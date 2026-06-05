"""
ZhiHealth AI 模型训练与评估工具
提供模型训练、超参数调优、性能评估、模型导出等功能
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from loguru import logger

try:
    from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.neural_network import MLPClassifier
    from sklearn.metrics import (classification_report, confusion_matrix,
                                roc_curve, auc, precision_recall_curve)
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn未安装，部分功能不可用")


class ModelTrainer:
    """模型训练器 - 支持多种算法的超参数搜索与训练"""
    
    def __init__(self, output_dir: str = "ai/models"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.best_models = {}
        self.training_history = {}
        
    def get_model_configs(self) -> Dict[str, Dict]:
        """获取预定义的模型配置"""
        configs = {
            'random_forest': {
                'model_class': RandomForestClassifier if SKLEARN_AVAILABLE else None,
                'param_grid': {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 10, 15, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'class_weight': ['balanced', None]
                },
                'default_params': {
                    'n_estimators': 100,
                    'max_depth': 10,
                    'random_state': 42
                }
            },
            'gradient_boosting': {
                'model_class': GradientBoostingClassifier if SKLEARN_AVAILABLE else None,
                'param_grid': {
                    'n_estimators': [50, 100, 200],
                    'learning_rate': [0.01, 0.1, 0.2],
                    'max_depth': [3, 5, 7],
                    'subsample': [0.8, 1.0]
                },
                'default_params': {
                    'n_estimators': 100,
                    'learning_rate': 0.1,
                    'max_depth': 5,
                    'random_state': 42
                }
            },
            'logistic_regression': {
                'model_class': LogisticRegression if SKLEARN_AVAILABLE else None,
                'param_grid': {
                    'C': [0.1, 1, 10, 100],
                    'penalty': ['l2'],
                    'solver': ['lbfgs', 'liblinear'],
                    'class_weight': ['balanced', None]
                },
                'default_params': {
                    'C': 1.0,
                    'max_iter': 1000,
                    'random_state': 42
                }
            },
            'svm': {
                'model_class': SVC if SKLEARN_AVAILABLE else None,
                'param_grid': {
                    'C': [0.1, 1, 10],
                    'kernel': ['rbf', 'linear'],
                    'gamma': ['scale', 'auto']
                },
                'default_params': {
                    'C': 1.0,
                    'kernel': 'rbf',
                    'probability': True,
                    'random_state': 42
                }
            }
        }
        return configs
    
    def train_and_evaluate(self, X_train: np.ndarray, y_train: np.ndarray,
                          X_test: np.ndarray, y_test: np.ndarray,
                          model_name: str = 'random_forest',
                          use_grid_search: bool = False) -> Dict:
        """训练并评估单个模型"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn未安装")
            
        configs = self.get_model_configs()
        
        if model_name not in configs:
            raise ValueError(f"未知模型: {model_name}。可用: {list(configs.keys())}")
            
        config = configs[model_name]
        ModelClass = config['model_class']
        
        if ModelClass is None:
            raise ValueError(f"模型 {model_name} 不可用")
            
        logger.info(f"开始训练模型: {model_name}")
        
        if use_grid_search:
            logger.info("使用网格搜索进行超参数优化...")
            model = GridSearchCV(
                ModelClass(**{k: v for k, v in config['default_params'].items() 
                             if k != 'random_state'}),
                param_grid=config['param_grid'],
                cv=5,
                scoring='f1_weighted',
                n_jobs=-1,
                verbose=1
            )
            model.fit(X_train, y_train)
            
            best_model = model.best_estimator_
            best_params = model.best_params_
            cv_score = model.best_score_
            
            logger.info(f"最佳参数: {best_params}")
            logger.info(f"交叉验证F1: {cv_score:.4f}")
            
        else:
            best_model = ModelClass(**config['default_params'])
            best_model.fit(X_train, y_train)
            best_params = config['default_params']
            cv_score = None
            
        # 预测与评估
        y_pred = best_model.predict(X_test)
        y_prob = best_model.predict_proba(X_test) if hasattr(best_model, 'predict_proba') else None
        
        metrics = self._calculate_metrics(y_test, y_pred, y_prob)
        
        result = {
            'model_name': model_name,
            'best_params': best_params,
            'cv_score': round(cv_score, 4) if cv_score else None,
            'test_metrics': metrics,
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        self.best_models[model_name] = best_model
        
        logger.info(f"{model_name} 训练完成 - 准确率: {metrics['accuracy']:.4f}, F1: {metrics['f1']:.4f}")
        
        return result
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, 
                          y_prob: Optional[np.ndarray] = None) -> Dict:
        """计算分类指标"""
        metrics = {
            'accuracy': float((y_true == y_pred).mean()),
            'precision_macro': 0,
            'recall_macro': 0,
            'f1_macro': 0,
            'auc': None
        }
        
        try:
            from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
            
            metrics.update({
                'precision_macro': float(precision_score(y_true, y_pred, average='macro')),
                'recall_macro': float(recall_score(y_true, y_pred, average='macro')),
                'f1_macro': float(f1_score(y_true, y_pred, average='macro'))
            })
            
            if y_prob is not None and len(np.unique(y_true)) == 2:
                metrics['auc'] = float(roc_auc_score(y_true, y_prob[:, 1]))
            elif y_prob is not None and len(np.unique(y_true)) > 2:
                metrics['auc'] = float(roc_auc_score(y_true, y_prob, multi_class='ovr', average='weighted'))
                
        except Exception as e:
            logger.warning(f"指标计算警告: {e}")
            
        return {k: round(v, 4) if v is not None else v for k, v in metrics.items()}
    
    def compare_models(self, X_train: np.ndarray, y_train: np.ndarray,
                      X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """对比多个模型的性能"""
        results = {}
        model_names = list(self.get_model_configs().keys())
        
        for model_name in model_names:
            try:
                result = self.train_and_evaluate(
                    X_train, y_train, X_test, y_test,
                    model_name=model_name,
                    use_grid_search=False
                )
                results[model_name] = result
                
            except Exception as e:
                logger.error(f"模型 {model_name} 训练失败: {e}")
                results[model_name] = {'error': str(e)}
                
        # 排序找出最佳模型
        valid_results = {k: v for k, v in results.items() if 'error' not in v}
        if valid_results:
            best_model = max(valid_results.items(), 
                            key=lambda x: x[1]['test_metrics']['f1_macro'])
            
            comparison_summary = {
                'models_compared': len(results),
                'successful_models': len(valid_results),
                'best_model': best_model[0],
                'best_f1_score': best_model[1]['test_metrics']['f1_macro'],
                'detailed_results': results,
                'recommendation': f"推荐使用 **{best_model[0]}** 模型，"
                                f"F1分数为 {best_model[1]['test_metrics']['f1_macro']:.4f}"
            }
        else:
            comparison_summary = {
                'models_compared': len(results),
                'successful_models': 0,
                'error': '所有模型训练失败',
                'detailed_results': results
            }
            
        return comparison_summary
    
    def save_model(self, model_name: str, custom_path: str = None) -> str:
        """保存训练好的模型"""
        if model_name not in self.best_models:
            raise ValueError(f"模型 {model_name} 尚未训练或不存在")
            
        save_path = custom_path or os.path.join(self.output_dir, f'{model_name}_best.joblib')
        joblib.dump(self.best_models[model_name], save_path)
        
        logger.info(f"模型已保存至: {save_path}")
        return save_path
    
    def load_model(self, model_name: str, path: str = None):
        """加载已保存的模型"""
        load_path = path or os.path.join(self.output_dir, f'{model_name}_best.joblib')
        
        if not os.path.exists(load_path):
            raise FileNotFoundError(f"模型文件不存在: {load_path}")
            
        self.best_models[model_name] = joblib.load(load_path)
        logger.info(f"模型已加载: {load_path}")
        
        return self.best_models[model_name]


class FeatureEngineeringPipeline:
    """特征工程管道 - 自动化特征提取、选择、转换"""
    
    def __init__(self):
        self.feature_transformers = {}
        self.selected_features = []
        self.feature_importance = {}
        
    def extract_temporal_features(self, df: pd.DataFrame, timestamp_col: str = 'timestamp') -> pd.DataFrame:
        """提取时间相关特征"""
        feature_df = df.copy()
        
        if timestamp_col not in df.columns:
            return feature_df
            
        dt_col = pd.to_datetime(df[timestamp_col])
        
        feature_df['hour'] = dt_col.dt.hour
        feature_df['day_of_week'] = dt_col.dt.dayofweek
        feature_df['day_of_month'] = dt_col.dt.day
        feature_df['month'] = dt_col.dt.month
        feature_df['is_weekend'] = dt_col.dt.dayofweek.isin([5, 6]).astype(int)
        feature_df['is_night'] = ((dt_col.dt.hour >= 22) | (dt_col.dt.hour <= 6)).astype(int)
        
        # 周期性编码（sin/cos变换）
        feature_df['hour_sin'] = np.sin(2 * np.pi * feature_df['hour'] / 24)
        feature_df['hour_cos'] = np.cos(2 * np.pi * feature_df['hour'] / 24)
        feature_df['dow_sin'] = np.sin(2 * np.pi * feature_df['day_of_week'] / 7)
        feature_df['dow_cos'] = np.cos(2 * np.pi * feature_df['day_of_week'] / 7)
        
        logger.info(f"已提取时间特征，新增 {12} 个特征列")
        return feature_df
    
    def extract_statistical_features(self, df: pd.DataFrame, group_by: str = 'user_id',
                                    windows: List[int] = [3, 7, 14]) -> pd.DataFrame:
        """提取统计聚合特征（滑动窗口）"""
        feature_df = df.copy()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = [group_by, 'timestamp', 'record_id', 'device_id']
        numeric_cols = [c for c in numeric_cols if c not in exclude_cols]
        
        if not numeric_cols or group_by not in df.columns:
            return feature_df
            
        for col in numeric_cols[:5]:  # 限制处理前5个数值列以避免过拟合
            for window in windows:
                roll_mean = df.groupby(group_by)[col].transform(
                    lambda x: x.rolling(window=window, min_periods=1).mean()
                )
                roll_std = df.groupby(group_by)[col].transform(
                    lambda x: x.rolling(window=window, min_periods=1).std().fillna(0)
                )
                
                feature_df[f'{col}_ma_{window}'] = roll_mean
                feature_df[f'{col}_std_{window}'] = roll_std
                
        logger.info(f"已提取统计特征，窗口大小: {windows}")
        return feature_df
    
    def extract_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取交互特征（特征组合）"""
        feature_df = df.copy()
        
        # 血压相关交互
        if all(c in df.columns for c in ['blood_pressure_systolic', 'blood_pressure_diastolic']):
            feature_df['pulse_pressure'] = (
                df['blood_pressure_systolic'] - df['blood_pressure_diastolic']
            )
            feature_df['mean_arterial_pressure'] = (
                df['blood_pressure_systolic'] + 2 * df['blood_pressure_diastolic']
            ) / 3
            feature_df['bp_ratio'] = (
                df['blood_pressure_diastolic'] / df['blood_pressure_systolic'].replace(0, 1)
            )
            
        # 心率与血压交互
        if 'heart_rate' in df.columns and 'blood_pressure_systolic' in df.columns:
            feature_df['hr_bp_product'] = df['heart_rate'] * df['blood_pressure_systolic'] / 10000
            feature_dbf['double_product'] = df['heart_rate'] * df['blood_pressure_systolic'] / 100
            
        # 活动与睡眠交互
        if 'steps' in df.columns and 'sleep_hours' in df.columns:
            feature_df['activity_sleep_balance'] = df['steps'] / (df['sleep_hours'].replace(0, 1) * 1000)
            
        # 综合健康评分（简化版）
        score_components = []
        if 'heart_rate' in df.columns:
            hr_normalized = (df['heart_rate'] - 72) / 20  # 标准化到72附近
            score_components.append(hr_normalized)
        if 'steps' in df.columns:
            steps_normalized = np.log1p(df['steps']) / 10
            score_components.append(steps_normalized)
        if 'sleep_hours' in df.columns:
            sleep_normalized = (df['sleep_hours'] - 7) / 2
            score_components.append(sleep_normalized)
            
        if score_components:
            feature_df['health_score_raw'] = sum(score_components) / len(score_components)
            
        logger.info("已提取交互特征")
        return feature_df
    
    def select_features_by_correlation(self, df: pd.DataFrame, target_col: str,
                                      threshold: float = 0.1) -> List[str]:
        """基于相关性选择特征"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if target_col not in numeric_df.columns:
            logger.warning(f"目标列 {target_col} 不在数据中")
            return []
            
        correlations = numeric_df.corr()[target_col].drop(target_col)
        selected = correlations[abs(correlations) >= threshold].index.tolist()
        
        self.feature_importance = correlations.abs().sort_values(ascending=False).to_dict()
        self.selected_features = selected
        
        logger.info(f"基于相关性选择了 {len(selected)} 个特征 (阈值: {threshold})")
        
        return selected


class AIPipelineManager:
    """AI管道管理器 - 端到端机器学习流程管理"""
    
    def __init__(self):
        self.trainer = ModelTrainer()
        self.feature_pipeline = FeatureEngineeringPipeline()
        self.training_results = {}
        
    def run_full_pipeline(self, raw_data: pd.DataFrame, target_column: str = 'health_risk',
                         auto_feature_engineering: bool = True,
                         compare_models: bool = True) -> Dict:
        """运行完整的ML流水线"""
        start_time = datetime.now()
        pipeline_report = {
            'pipeline_start_time': start_time.isoformat(),
            'raw_data_shape': raw_data.shape,
            'stages': {}
        }
        
        try:
            # Stage 1: 特征工程
            logger.info("="*60)
            logger.info("Stage 1: 特征工程")
            logger.info("="*60)
            
            processed_data = raw_data.copy()
            
            if auto_feature_engineering:
                processed_data = self.feature_pipeline.extract_temporal_features(processed_data)
                processed_data = self.feature_pipeline.extract_statistical_features(processed_data)
                processed_data = self.feature_pipeline.extract_interaction_features(processed_data)
                
            selected_features = self.feature_pipeline.select_features_by_correlation(
                processed_data, target_column, threshold=0.05
            )
            
            if not selected_features:
                selected_features = [c for c in processed_data.select_dtypes(include=[np.number]).columns 
                                    if c != target_column][:20]
                
            pipeline_report['stages']['feature_engineering'] = {
                'input_features': len(raw_data.columns),
                'output_features': len(processed_data.columns),
                'selected_for_training': len(selected_features),
                'new_features_created': len(processed_data.columns) - len(raw_data.columns)
            }
            
            # Stage 2: 数据分割
            logger.info("="*60)
            logger.info("Stage 2: 数据准备与分割")
            logger.info("="*60)
            
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            
            X = processed_data[selected_features].fillna(0).values
            y = processed_data[target_column].values if target_column in processed_data.columns \
                else self._generate_labels(processed_data)
                
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
            )
            
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            pipeline_report['stages']['data_preparation'] = {
                'total_samples': len(X),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'classes': list(set(y)),
                'class_distribution': dict(pd.Series(y).value_counts().to_dict())
            }
            
            # Stage 3: 模型训练与比较
            logger.info("="*60)
            logger.info("Stage 3: 模型训练与评估")
            logger.info("="*60)
            
            if compare_models:
                comparison_result = self.trainer.compare_models(
                    X_train_scaled, y_train, X_test_scaled, y_test
                )
                pipeline_report['stages']['model_comparison'] = comparison_result
                
                # 使用最佳模型重新训练并保存
                best_model_name = comparison_result.get('best_model', 'random_forest')
                final_result = self.trainer.train_and_evaluate(
                    X_train_scaled, y_train, X_test_scaled, y_test,
                    model_name=best_model_name,
                    use_grid_search=True
                )
                pipeline_report['stages']['final_model'] = final_result
                
                # 保存最佳模型
                saved_path = self.trainer.save_model(best_model_name)
                pipeline_report['stages']['final_model']['saved_to'] = saved_path
                
            else:
                # 仅训练默认模型
                default_result = self.trainer.train_and_evaluate(
                    X_train_scaled, y_train, X_test_scaled, y_test,
                    model_name='random_forest'
                )
                pipeline_report['stages']['single_model'] = default_result
                self.trainer.save_model('random_forest')
                
            end_time = datetime.now()
            pipeline_report['pipeline_end_time'] = end_time.isoformat()
            pipeline_report['total_duration_seconds'] = (end_time - start_time).total_seconds()
            pipeline_report['status'] = 'success'
            pipeline_report['message'] = "AI流水线执行成功！"
            
            logger.info(f"\n{'='*60}")
            logger.info(f"  AI Pipeline 完成!")
            logger.info(f"  耗时: {pipeline_report['total_duration_seconds']:.2f}s")
            logger.info(f"{'='*60}\n")
            
        except Exception as e:
            logger.error(f"AI流水线执行失败: {e}", exc_info=True)
            pipeline_report['status'] = 'failed'
            pipeline_report['error'] = str(e)
            
        self.training_results = pipeline_report
        return pipeline_report
    
    def _generate_labels(self, df: pd.DataFrame) -> np.ndarray:
        """生成合成标签用于无监督学习演示"""
        n_samples = len(df)
        labels = []
        
        for i in range(n_samples):
            score = 0
            row = df.iloc[i]
            
            if 'heart_rate' in row.index and not pd.isna(row.get('heart_rate')):
                hr = row['heart_rate']
                if hr > 120 or hr < 50: score += 2
                elif hr > 100 or hr < 60: score += 1
                    
            if 'bp_sys' in row.index or 'blood_pressure_systolic' in row.index:
                bp_val = row.get('bp_sys', row.get('blood_pressure_systolic', 120))
                if not pd.isna(bp_val) and bp_val > 150: score += 2
                    
            labels.append(min(score, 4))
            
        return np.array(labels)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ZhiHealth AI模型训练工具')
    subparsers = parser.add_subparsers(dest='command')
    
    # 训练命令
    train_parser = subparsers.add_parser('train', help='运行完整AI训练流程')
    train_parser.add_argument('--input', required=True, help='输入CSV文件路径')
    train_parser.add_argument('--target', default='health_risk', help='目标变量名')
    train_parser.add_argument('--compare', action='store_true', help='对比多个模型')
    train_parser.add_argument('--output-dir', default='ai/models', help='模型输出目录')
    
    # 评估命令
    eval_parser = subparsers.add_parser('evaluate', help='评估已训练的模型')
    eval_parser.add_argument('--model-name', required=True, help='模型名称')
    eval_parser.add_argument('--test-data', required=True, help='测试数据路径')
    
    args = parser.parse_args()
    
    if args.command == 'train':
        import pandas as pd
        
        print("\n" + "="*70)
        print("  ZhiHealth AI 模型训练系统")
        print("="*70 + "\n")
        
        df = pd.read_csv(args.input)
        print(f"加载数据: {df.shape[0]} 行 × {df.shape[1]} 列\n")
        
        manager = AIPipelineManager()
        manager.trainer.output_dir = args.output_dir
        
        results = manager.run_full_pipeline(
            raw_data=df,
            target_column=args.target,
            compare_models=args.compare
        )
        
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        
    elif args.command == 'evaluate':
        print(f"评估模式 - 模型: {args.model_name}")
        # 实现评估逻辑...
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()