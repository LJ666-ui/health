"""
ZhiHealth AI/ML 核心引擎
提供智能健康分析、预测模型、异常检测、风险评估等机器学习能力
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                            f1_score, roc_auc_score, mean_squared_error, 
                            mean_absolute_error, classification_report)
from sklearn.cluster import KMeans, DBSCAN
from scipy import stats
from loguru import logger
import warnings
warnings.filterwarnings('ignore')


class HealthRiskPredictor:
    """健康风险预测器 - 预测未来健康指标和疾病风险"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.is_trained = False
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征工程：从原始数据提取有意义的特征"""
        feature_df = pd.DataFrame()
        
        if 'timestamp' in df.columns:
            feature_df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            feature_df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            feature_df['is_weekend'] = feature_df['day_of_week'].isin([5, 6]).astype(int)
        
        if 'heart_rate' in df.columns:
            feature_df['heart_rate'] = df['heart_rate'].fillna(df['heart_rate'].median())
            feature_df['hr_deviation'] = feature_df['heart_rate'] - feature_df['heart_rate'].mean()
            feature_df['hr_rolling_mean_7'] = feature_df['heart_rate'].rolling(7, min_periods=1).mean()
            
        if 'body_temp' in df.columns:
            feature_df['body_temp'] = df['body_temp'].fillna(36.5)
            feature_df['temp_abnormal'] = ((feature_df['body_temp'] < 36.0) | 
                                           (feature_df['body_temp'] > 37.3)).astype(int)
        
        if all(col in df.columns for col in ['blood_pressure_systolic', 'blood_pressure_diastolic']):
            feature_df['bp_sys'] = df['blood_pressure_systolic'].fillna(120)
            feature_df['bp_dia'] = df['blood_pressure_diastolic'].fillna(80)
            feature_df['pulse_pressure'] = feature_df['bp_sys'] - feature_df['bp_dia']
            feature_df['bp_ratio'] = feature_df['bp_dia'] / feature_df['bp_sys']
            feature_df['hypertension_risk'] = (
                (feature_df['bp_sys'] > 140) | 
                (feature_df['bp_dia'] > 90)
            ).astype(int)
            
        if 'steps' in df.columns:
            feature_df['steps'] = df['steps'].fillna(0)
            feature_df['activity_level'] = pd.cut(
                feature_df['steps'], 
                bins=[-1, 3000, 6000, 10000, float('inf')],
                labels=[0, 1, 2, 3]
            ).astype(float).fillna(0)
            
        if 'sleep_hours' in df.columns:
            feature_df['sleep_hours'] = df['sleep_hours'].fillna(7)
            feature_df['sleep_deficit'] = np.maximum(0, 8 - feature_df['sleep_hours'])
            feature_df['poor_sleep'] = (feature_df['sleep_hours'] < 6).astype(int)
        
        if 'user_id' in df.columns:
            le = LabelEncoder()
            feature_df['user_id_encoded'] = le.fit_transform(df['user_id'].astype(str))
            
        return feature_df.fillna(0)
    
    def train_risk_model(self, df: pd.DataFrame, target: str = 'health_risk') -> Dict:
        """训练疾病风险分类模型"""
        logger.info(f"开始训练 {target} 风险预测模型...")
        
        features = self.prepare_features(df)
        
        if target not in df.columns:
            df[target] = self._generate_synthetic_labels(features)
            
        X = features.values
        y = df[target].values
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',
            random_state=42
        )
        
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1': f1_score(y_test, y_pred, average='weighted'),
            'auc': roc_auc_score(y_test, y_prob, multi_class='ovr', average='weighted'),
            'support': len(X_test)
        }
        
        self.models[target] = model
        self.scalers[target] = scaler
        self.feature_importance[target] = dict(zip(
            features.columns.tolist(), 
            model.feature_importances_.tolist()
        ))
        self.is_trained = True
        
        logger.info(f"模型训练完成 - 准确率: {metrics['accuracy']:.2%}, F1: {metrics['f1']:.2%}")
        
        return {
            'model_name': f'RandomForest_{target}',
            'target_variable': target,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'metrics': metrics,
            'top_features': sorted(
                self.feature_importance[target].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }
    
    def _generate_synthetic_labels(self, features: pd.DataFrame) -> np.ndarray:
        """基于规则生成合成标签用于演示"""
        risk_scores = []
        
        for idx, row in features.iterrows():
            score = 0
            
            if 'heart_rate' in row and not pd.isna(row['heart_rate']):
                hr = row['heart_rate']
                if hr > 120 or hr < 50:
                    score += 2
                elif hr > 100 or hr < 60:
                    score += 1
                    
            if 'bp_sys' in row and not pd.isna(row.get('bp_sys', 0)):
                if row['bp_sys'] > 160 or row.get('bp_dia', 80) > 100:
                    score += 2
                elif row['bp_sys'] > 140 or row.get('bp_dia', 80) > 90:
                    score += 1
                    
            if 'temp_abnormal' in row and row.get('temp_abnormal', 0) == 1:
                score += 1
                
            if 'sleep_hours' in row and row.get('sleep_hours', 7) < 5:
                score += 1
                
            if 'steps' in row and row.get('steps', 5000) < 2000:
                score += 1
                
            risk_scores.append(min(score, 4))
            
        return np.array(risk_scores)
    
    def predict_health_risk(self, new_data: pd.DataFrame) -> List[Dict]:
        """对新数据进行健康风险预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练，请先调用 train_risk_model()")
            
        results = []
        features = self.prepare_features(new_data)
        
        for target, model in self.models.items():
            scaler = self.scalers[target]
            X_scaled = scaler.transform(features.values)
            
            predictions = model.predict(X_scaled)
            probabilities = model.predict_proba(X_scaled)
            
            risk_levels = ['低风险', '中低风险', '中等风险', '高风险', '极高风险']
            
            for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
                max_prob = prob.max()
                confidence = round(max_prob * 100, 1)
                
                result = {
                    'record_index': i,
                    'user_id': new_data.iloc[i]['user_id'] if 'user_id' in new_data.columns else i,
                    'predicted_risk_level': risk_levels[min(pred, len(risk_levels)-1)],
                    'risk_score': int(pred),
                    'confidence': confidence,
                    'model': target,
                    'recommendation': self._generate_recommendation(pred, target)
                }
                
                results.append(result)
                
        return results
    
    def _generate_recommendation(self, risk_score: int, model_type: str) -> str:
        """根据风险等级生成健康建议"""
        recommendations = {
            0: "继续保持良好的生活习惯，定期监测健康指标。",
            1: "建议适度增加运动量，注意饮食均衡。",
            2: "建议进行全面体检，关注血压、心率等关键指标。",
            3: "建议尽快就医检查，遵医嘱进行治疗或调整生活方式。",
            4: "警告：存在较高健康风险！请立即联系医疗专业人员。"
        }
        
        specific_advice = {
            'health_risk': "",
            'cardiovascular_risk': "特别关注心血管健康，减少盐分摄入，控制体重。",
            'metabolic_risk': "注意血糖控制，减少糖分摄入，增加有氧运动。"
        }
        
        base = recommendations.get(risk_score, recommendations[4])
        specific = specific_advice.get(model_type, "")
        
        return f"{base} {specific}".strip()


class AnomalyDetector:
    """异常检测器 - 使用多种算法识别健康数据异常"""
    
    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.detectors = {}
        self.thresholds = {}
        
    def detect_statistical_anomalies(self, data: pd.DataFrame, column: str) -> Dict:
        """基于统计方法的异常检测（Z-Score + IQR）"""
        values = data[column].dropna()
        
        z_scores = np.abs(stats.zscore(values))
        iqr_method = self._detect_iqr_outliers(values)
        
        anomalies_zscore = values[z_scores > 3]
        anomalies_iqr = values[iqr_method]
        
        combined_anomalies = set(anomalies_zscore.index) & set(anomalies_iqr.index)
        
        return {
            'method': 'statistical',
            'column': column,
            'total_records': len(values),
            'anomaly_count_zscore': len(anomalies_zscore),
            'anomaly_count_iqr': len(anomalies_iqr),
            'anomaly_count_combined': len(combined_anomalies),
            'anomaly_percentage': round(len(combined_anomalies) / len(values) * 100, 2),
            'anomaly_indices': list(combined_anomalies)[:20],
            'statistics': {
                'mean': round(values.mean(), 2),
                'std': round(values.std(), 2),
                'min': round(values.min(), 2),
                'max': round(values.max(), 2),
                'q1': round(values.quantile(0.25), 2),
                'q3': round(values.quantile(0.75), 2),
                'iqr': round(values.quantile(0.75) - values.quantile(0.25), 2)
            },
            'thresholds': {
                'zscore_upper': round(values.mean() + 3 * values.std(), 2),
                'zscore_lower': round(values.mean() - 3 * values.std(), 2),
                'iqr_upper': round(values.quantile(0.75) + 1.5 * (values.quantile(0.75) - values.quantile(0.25)), 2),
                'iqr_lower': round(values.quantile(0.25) - 1.5 * (values.quantile(0.75) - values.quantile(0.25)), 2)
            }
        }
    
    def _detect_iqr_outliers(self, series: pd.Series) -> pd.Series:
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return (series < lower_bound) | (series > upper_bound)
    
    def train_isolation_forest(self, df: pd.DataFrame, columns: List[str] = None) -> Dict:
        """训练Isolation Forest异常检测模型"""
        columns = columns or ['heart_rate', 'body_temp', 'blood_pressure_systolic']
        available_cols = [c for c in columns if c in df.columns]
        
        if not available_cols:
            raise ValueError("没有可用的特征列")
            
        X = df[available_cols].dropna().values
        
        detector = IsolationForest(
            contamination=self.contamination,
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )
        
        predictions = detector.fit_predict(X)
        anomaly_scores = detector.decision_function(X)
        
        anomaly_indices = np.where(predictions == -1)[0]
        
        self.detectors['isolation_forest'] = detector
        self.thresholds['isolation_forest'] = {
            'columns': available_cols,
            'contamination': self.contamination,
            'threshold': np.percentile(anomaly_scores, self.contamination * 100)
        }
        
        return {
            'model': 'Isolation Forest',
            'features_used': available_cols,
            'total_samples': len(X),
            'anomalies_detected': len(anomaly_indices),
            'anomaly_rate': round(len(anomaly_indices) / len(X) * 100, 2),
            'anomaly_indices': anomaly_indices[:50].tolist(),
            'anomaly_scores_stats': {
                'min': round(anomaly_scores.min(), 4),
                'max': round(anomaly_scores.max(), 4),
                'mean': round(anomaly_scores.mean(), 4),
                'std': round(anomaly_scores.std(), 4)
            }
        }
    
    def detect_multivariate_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """多变量联合异常检测"""
        if 'isolation_forest' not in self.detectors:
            raise ValueError("Isolation Forest模型尚未训练")
            
        detector = self.detectors['isolation_forest']
        cols = self.thresholds['isolation_forest']['columns']
        X = df[cols].dropna().values
        
        predictions = detector.predict(X)
        scores = detector.decision_function(X)
        
        anomalies = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:
                anomaly_info = {
                    'index': i,
                    'user_id': df.iloc[i]['user_id'] if 'user_id' in df.columns else None,
                    'anomaly_score': round(score, 4),
                    'severity': 'high' if score < -0.3 else ('medium' if score < -0.15 else 'low'),
                    'values': {col: df.iloc[i][col] for col in cols}
                }
                anomalies.append(anomaly_info)
                
        anomalies.sort(key=lambda x: x['anomaly_score'])
        
        return anomalies


class HealthTrendPredictor:
    """健康趋势预测器 - 使用时间序列分析预测未来健康走向"""
    
    def __init__(self, prediction_horizon: int = 30):
        self.prediction_horizon = prediction_horizon
        self.models = {}
        self.trend_models = {}
        
    def analyze_trends(self, time_series_data: pd.DataFrame, value_column: str) -> Dict:
        """分析时间序列趋势"""
        if 'timestamp' not in time_series_data.columns:
            raise ValueError("数据必须包含 timestamp 列")
            
        ts_data = time_series_data.copy()
        ts_data['datetime'] = pd.to_datetime(ts_data['timestamp'])
        ts_data = ts_data.sort_values('datetime')
        
        values = ts_data[value_column].dropna().values
        dates = ts_data['datetime'].values
        
        # 计算移动平均
        ma_7 = pd.Series(values).rolling(window=7, min_periods=1).mean().values
        ma_30 = pd.Series(values).rolling(window=min(30, len(values)), min_periods=1).mean().values
        
        # 线性回归趋势
        x = np.arange(len(values)).reshape(-1, 1)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x.flatten(), values)
        
        # 季节性分解（简化版）
        trend_component = ma_30
        residual = values - trend_component
        
        # 趋势判断
        if slope > 0.01:
            trend_direction = '上升'
        elif slope < -0.01:
            trend_direction = '下降'
        else:
            trend_direction = '稳定'
            
        volatility = np.std(residual)
        
        return {
            'metric': value_column,
            'data_points': len(values),
            'time_range': {
                'start': str(dates[0])[:19],
                'end': str(dates[-1])[:19]
            },
            'trend_analysis': {
                'direction': trend_direction,
                'slope_per_day': round(slope, 4),
                'r_squared': round(r_value**2, 4),
                'p_value': round(p_value, 6),
                'significance': '显著' if p_value < 0.05 else '不显著'
            },
            'statistics': {
                'current_value': round(values[-1], 2),
                'mean': round(np.mean(values), 2),
                'std': round(np.std(values), 2),
                'min': round(np.min(values), 2),
                'max': round(np.max(values), 2),
                'ma_7_current': round(ma_7[-1], 2),
                'ma_30_current': round(ma_30[-1], 2)
            },
            'volatility': {
                'value': round(volatility, 4),
                'level': '高' if volatility > np.mean(values) * 0.1 else ('中' if volatility > np.mean(values) * 0.05 else '低')
            },
            'forecast': self._simple_forecast(values, slope, intercept)
        }
    
    def _simple_forecast(self, historical_values: np.ndarray, slope: float, intercept: float) -> List[Dict]:
        """简单线性预测"""
        forecasts = []
        last_idx = len(historical_values)
        
        for day in range(1, self.prediction_horizon + 1):
            predicted_value = slope * (last_idx + day) + intercept
            
            forecast = {
                'day_ahead': day,
                'date': (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d'),
                'predicted_value': round(predicted_value, 2),
                'confidence_interval_lower': round(predicted_value - np.std(historical_values) * 1.96, 2),
                'confidence_interval_upper': round(predicted_value + np.std(historical_values) * 1.96, 2)
            }
            forecasts.append(forecast)
            
        return forecasts
    
    def predict_future_health(self, user_data: pd.DataFrame) -> Dict:
        """综合预测用户未来健康状况"""
        predictions = {}
        
        metrics_to_predict = ['heart_rate', 'body_temp', 'blood_pressure_systolic', 
                             'blood_pressure_diastolic', 'steps', 'sleep_hours']
        
        for metric in metrics_to_predict:
            if metric in user_data.columns:
                try:
                    analysis = self.analyze_trends(user_data, metric)
                    predictions[metric] = analysis
                except Exception as e:
                    logger.warning(f"无法预测 {metric}: {e}")
                    
        overall_assessment = self._assess_overall_health(predictions)
        
        return {
            'user_id': user_data['user_id'].iloc[0] if 'user_id' in user_data.columns else 'unknown',
            'analysis_date': datetime.now().isoformat(),
            'prediction_horizon_days': self.prediction_horizon,
            'individual_metrics': predictions,
            'overall_assessment': overall_assessment
        }
    
    def _assess_overall_health(self, predictions: Dict) -> Dict:
        """综合评估整体健康状况"""
        risk_factors = 0
        positive_factors = 0
        concerns = []
        strengths = []
        
        for metric, analysis in predictions.items():
            trend = analysis.get('trend_analysis', {}).get('direction', '')
            significance = analysis.get('trend_analysis', {}).get('significance', '')
            
            if metric == 'heart_rate':
                current = analysis.get('statistics', {}).get('current_value', 72)
                if current > 100 or current < 55:
                    risk_factors += 2
                    concerns.append(f"心率异常 ({current} bpm)")
                elif trend == '上升' and significance == '显著':
                    risk_factors += 1
                    concerns.append("心率呈上升趋势")
                else:
                    positive_factors += 1
                    
            elif metric.startswith('blood_pressure'):
                sys_val = analysis.get('statistics', {}).get('current_value', 120)
                if metric.endswith('systolic') and sys_val > 140:
                    risk_factors += 2
                    concerns.append(f"收缩压偏高 ({sys_val})")
                    
            elif metric == 'steps':
                avg = analysis.get('statistics', {}).get('mean', 5000)
                if avg < 3000:
                    risk_factors += 1
                    concerns.append(f"活动量不足 (日均{avg:.0f}步)")
                elif avg > 8000:
                    positive_factors += 1
                    strengths.append("活动量充足")
                    
            elif metric == 'sleep_hours':
                avg = analysis.get('statistics', {}).get('mean', 7)
                if avg < 6:
                    risk_factors += 1
                    concerns.append(f"睡眠不足 (平均{avg:.1f}小时)")
                elif avg >= 7:
                    positive_factors += 1
                    strengths.append("睡眠质量良好")
                    
        total_score = positive_factors - risk_factors
        if total_score >= 2:
            health_status = "优秀"
        elif total_score >= 0:
            health_status = "良好"
        elif total_score >= -2:
            health_status = "需关注"
        else:
            health_status = "需改善"
            
        return {
            'health_status': health_status,
            'risk_factor_count': risk_factors,
            'positive_factor_count': positive_factors,
            'concerns': concerns,
            'strengths': strengths,
            'overall_recommendation': self._generate_overall_recommendation(health_status, concerns)
        }
    
    def _generate_overall_recommendation(self, status: str, concerns: List[str]) -> str:
        templates = {
            "优秀": "您的各项健康指标表现优异，请继续保持当前的健康生活方式。",
            "良好": "整体健康状况良好，但仍有提升空间。建议关注以下方面：" + "; ".join(concerns[:2]),
            "需关注": "检测到一些需要关注的健康信号。建议：" + "; ".join(concerns[:3]) + "。建议咨询专业医生。",
            "需改善": "多项健康指标显示异常，强烈建议尽快进行全面的身体检查并寻求医疗建议。"
        }
        return templates.get(status, templates["良好"])


class UserSegmentationEngine:
    """用户分群引擎 - 基于行为数据对用户进行聚类分群"""
    
    def __init__(self, n_clusters: int = 5):
        self.n_clusters = n_clusters
        self.kmeans = None
        self.cluster_labels = None
        self.cluster_profiles = {}
        
    def segment_users(self, df: pd.DataFrame) -> Dict:
        """对用户进行分群"""
        user_features = self._extract_user_features(df)
        
        if user_features.empty:
            raise ValueError("无法提取用户特征")
            
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(user_features.values)
        
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        self.cluster_labels = self.kmeans.fit_predict(scaled_features)
        
        user_features['cluster'] = self.cluster_labels
        
        profiles = self._analyze_cluster_profiles(user_features)
        
        return {
            'total_users': len(user_features),
            'n_clusters': self.n_clusters,
            'cluster_distribution': dict(pd.Series(self.cluster_labels).value_counts().sort_index()),
            'cluster_profiles': profiles,
            'feature_importance': self._calculate_feature_importance(scaled_features),
            'silhouette_score': self._calculate_silhouette(scaled_features)
        }
    
    def _extract_user_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取每个用户的聚合特征"""
        features = []
        
        if 'user_id' in df.columns:
            for user_id, group in df.groupby('user_id'):
                user_feat = {'user_id': user_id}
                
                if 'heart_rate' in group.columns:
                    hr = group['heart_rate'].dropna()
                    if len(hr) > 0:
                        user_feat.update({
                            'avg_hr': hr.mean(),
                            'hr_std': hr.std(),
                            'hr_min': hr.min(),
                            'hr_max': hr.max(),
                            'hr_range': hr.max() - hr.min()
                        })
                        
                if all(c in group.columns for c in ['blood_pressure_systolic', 'blood_pressure_diastolic']):
                    bp_sys = group['blood_pressure_systolic'].dropna()
                    bp_dia = group['blood_pressure_diastolic'].dropna()
                    if len(bp_sys) > 0:
                        user_feat.update({
                            'avg_bp_sys': bp_sys.mean(),
                            'avg_bp_dia': bp_dia.mean(),
                            'bp_variability': bp_sys.std() if len(bp_sys) > 1 else 0
                        })
                        
                if 'steps' in group.columns:
                    steps = group['steps'].dropna()
                    if len(steps) > 0:
                        user_feat.update({
                            'avg_steps': steps.mean(),
                            'total_steps': steps.sum(),
                            'active_days': (steps > 8000).sum()
                        })
                        
                if 'sleep_hours' in group.columns:
                    sleep = group['sleep_hours'].dropna()
                    if len(sleep) > 0:
                        user_feat.update({
                            'avg_sleep': sleep.mean(),
                            'sleep_quality_score': min(100, (sleep.mean() / 8) * 100)
                        })
                        
                if 'body_temp' in group.columns:
                    temp = group['body_temp'].dropna()
                    if len(temp) > 0:
                        user_feat['avg_temp'] = temp.mean()
                        
                if 'data_type' in group.columns:
                    user_feat['data_types_count'] = group['data_type'].nunique()
                    user_feat['total_records'] = len(group)
                    
                features.append(user_feat)
                
        return pd.DataFrame(features).fillna(0)
    
    def _analyze_cluster_profiles(self, features_df: pd.DataFrame) -> Dict[int, Dict]:
        """分析各簇的用户画像"""
        profiles = {}
        
        numeric_cols = [c for c in features_df.columns 
                       if c not in ['user_id', 'cluster'] and pd.api.types.is_numeric_dtype(features_df[c])]
                       
        for cluster_id in range(self.n_clusters):
            cluster_data = features_df[features_df['cluster'] == cluster_id]
            
            profile = {
                'user_count': len(cluster_data),
                'percentage': round(len(cluster_data) / len(features_df) * 100, 1),
                'characteristics': {},
                'archetype': self._assign_archetype(cluster_id, cluster_data, numeric_cols)
            }
            
            for col in numeric_cols:
                cluster_mean = cluster_data[col].mean()
                global_mean = features_df[col].mean()
                
                if cluster_mean > global_mean * 1.2:
                    deviation = 'high'
                elif cluster_mean < global_mean * 0.8:
                    deviation = 'low'
                else:
                    deviation = 'normal'
                    
                profile['characteristics'][col] = {
                    'value': round(cluster_mean, 2),
                    'vs_average': deviation,
                    'percentile': round(
                        (cluster_data[col] < cluster_mean).sum() / len(cluster_data) * 100, 1
                    ) if len(cluster_data) > 0 else 50
                }
                
            profiles[cluster_id] = profile
            
        return profiles
    
    def _assign_archetype(self, cluster_id: int, cluster_data: pd.DataFrame, 
                         numeric_cols: List[str]) -> str:
        """为每个簇分配典型用户画像标签"""
        archetypes = [
            "健康活跃型",      # 高活动量、好睡眠、正常生理指标
            "亚健康预警型",    # 心率偏高、血压临界、睡眠不足
            "运动达人型",      # 极高活动量、心率适应性好
            "慢病管理型",      # 血压偏高、心率波动大、需监控
            "数据稀疏型"       # 数据记录少、参与度低
        ]
        
        try:
            avg_steps = cluster_data.get('avg_steps', pd.Series([0])).mean()
            avg_bp_sys = cluster_data.get('avg_bp_sys', pd.Series([120])).mean()
            avg_sleep = cluster_data.get('avg_sleep', pd.Series([7])).mean()
            records = cluster_data.get('total_records', pd.Series([0])).mean()
            
            if records < 10:
                return archetypes[4]
            elif avg_steps > 12000 and avg_bp_sys < 125:
                return archetypes[2]
            elif avg_bp_sys > 135 or avg_sleep < 6:
                return archetypes[1] if avg_bp_sys > 135 else archetypes[3]
            elif avg_steps > 7000 and 6.5 <= avg_sleep <= 8.5:
                return archetypes[0]
            else:
                return archetypes[cluster_id % len(archetypes)]
        except:
            return f"类型_{cluster_id}"
    
    def _calculate_feature_importance(self, scaled_features: np.ndarray) -> Dict[str, float]:
        """计算特征在聚类中的重要性"""
        if self.kmeans is None:
            return {}
            
        centroids = self.kmeans.cluster_centers_
        centroid_variance = np.var(centroids, axis=0)
        
        importance = {}
        feature_names = [f'feature_{i}' for i in range(centroid_variance.shape[0])]
        
        for name, var in zip(feature_names, centroid_variance):
            importance[name] = round(var, 4)
            
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def _calculate_silhouette(self, scaled_features: np.ndarray) -> float:
        """计算轮廓系数评估聚类质量"""
        from sklearn.metrics import silhouette_score
        
        if len(set(self.cluster_labels)) < 2:
            return 0.0
            
        try:
            score = silhouette_score(scaled_features, self.cluster_labels)
            return round(score, 4)
        except:
            return 0.0


class AIEngine:
    """AI主引擎 - 整合所有AI/ML功能"""
    
    def __init__(self):
        self.risk_predictor = HealthRiskPredictor()
        self.anomaly_detector = AnomalyDetector()
        self.trend_predictor = HealthTrendPredictor(prediction_horizon=30)
        self.segmentation_engine = UserSegmentationEngine(n_clusters=5)
        
    def run_comprehensive_analysis(self, df: pd.DataFrame) -> Dict:
        """运行综合AI分析"""
        start_time = datetime.now()
        results = {
            'analysis_timestamp': start_time.isoformat(),
            'data_summary': {
                'total_records': len(df),
                'users_count': df['user_id'].nunique() if 'user_id' in df.columns else 0,
                'date_range': self._get_date_range(df)
            },
            'modules': {}
        }
        
        try:
            logger.info("正在训练风险预测模型...")
            risk_result = self.risk_predictor.train_risk_model(df)
            results['modules']['risk_prediction'] = risk_result
            
            logger.info("正在进行异常检测...")
            anomaly_results = {}
            
            for col in ['heart_rate', 'body_temp', 'blood_pressure_systolic']:
                if col in df.columns:
                    stat_anomaly = self.anomaly_detector.detect_statistical_anomalies(df, col)
                    anomaly_results[f'statistical_{col}'] = stat_anomaly
                    
            iso_result = self.anomaly_detector.train_isolation_forest(df)
            anomaly_results['isolation_forest'] = iso_result
            
            multivariate_anomalies = self.anomaly_detector.detect_multivariate_anomalies(df)
            anomaly_results['multivariate'] = {
                'total_anomalies': len(multivariate_anomalies),
                'top_anomalies': multivariate_anomalies[:10]
            }
            
            results['modules']['anomaly_detection'] = anomaly_results
            
            logger.info("正在分析健康趋势...")
            trend_results = {}
            
            for col in ['heart_rate', 'blood_pressure_systolic', 'steps']:
                if col in df.columns:
                    try:
                        trend = self.trend_predictor.analyze_trends(df, col)
                        trend_results[col] = trend
                    except Exception as e:
                        logger.warning(f"趋势分析失败 {col}: {e}")
                        
            results['modules']['trend_prediction'] = trend_results
            
            logger.info("正在进行用户分群...")
            segmentation_result = self.segmentation_engine.segment_users(df)
            results['modules']['user_segmentation'] = segmentation_result
            
        except Exception as e:
            logger.error(f"AI分析过程出错: {e}", exc_info=True)
            results['error'] = str(e)
            
        end_time = datetime.now()
        results['processing_time_seconds'] = (end_time - start_time).total_seconds()
        results['status'] = 'completed' if 'error' not in results else 'partial'
        
        logger.info(f"AI综合分析完成，耗时: {results['processing_time_seconds']:.2f}s")
        
        return results
    
    def _get_date_range(self, df: pd.DataFrame) -> Dict:
        """获取数据日期范围"""
        if 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'])
            return {
                'start': timestamps.min().isoformat(),
                'end': timestamps.max().isoformat()
            }
        return {'start': 'unknown', 'end': 'unknown'}
    
    def generate_ai_report(self, df: pd.DataFrame, output_path: str = None) -> str:
        """生成完整的AI分析报告"""
        analysis = self.run_comprehensive_analysis(df)
        
        report_lines = [
            "="*70,
            "  ZhiHealth AI智能健康分析报告",
            "="*70,
            f"  分析时间: {analysis['analysis_timestamp']}",
            f"  数据规模: {analysis['data_summary']['total_records']} 条记录",
            f"  用户数量: {analysis['data_summary']['users_count']} 人",
            f"  处理耗时: {analysis['processing_time_seconds']:.2f} 秒",
            "-"*70,
            ""
        ]
        
        if 'risk_prediction' in analysis.get('modules', {}):
            rp = analysis['modules']['risk_prediction']
            report_lines.extend([
                "[模块1] 健康风险预测模型",
                f"  模型类型: {rp['model_name']}",
                f"  准确率: {rp['metrics']['accuracy']:.2%}",
                f"  F1分数: {rp['metrics']['f1']:.2%}",
                f"  AUC值: {rp['metrics']['auc']:.2%}",
                "  重要特征 TOP5:",
            ])
            for feat, imp in rp.get('top_features', []):
                report_lines.append(f"    - {feat}: {imp:.4f}")
            report_lines.append("")
            
        if 'anomaly_detection' in analysis.get('modules', {}):
            ad = analysis['modules']['anomaly_detection']
            report_lines.extend([
                "[模块2] 异常检测结果",
                f"  统计方法异常数: {ad.get('isolation_forest', {}).get('anomalies_detected', 0)}",
                f"  异常率: {ad.get('isolation_forest', {}).get('anomaly_rate', 0):.2f}%",
                ""
            ])
            
        if 'trend_prediction' in analysis.get('modules', {}):
            tp = analysis['modules']['trend_prediction']
            report_lines.append("[模块3] 健康趋势分析")
            for metric, analysis_data in tp.items():
                trend = analysis_data.get('trend_analysis', {})
                report_lines.append(f"  {metric}: {trend.get('direction', 'N/A')} (R²={trend.get('r_squared', 0):.3f})")
            report_lines.append("")
            
        if 'user_segmentation' in analysis.get('modules', {}):
            us = analysis['modules']['user_segmentation']
            report_lines.extend([
                "[模块4] 用户分群结果",
                f"  分群数量: {us['n_clusters']}",
                f"  轮廓系数: {us.get('silhouette_score', 0):.3f}",
                "  各群体分布:",
            ])
            for cluster_id, count in us.get('cluster_distribution', {}).items():
                profile = us.get('cluster_profiles', {}).get(cluster_id, {})
                archetype = profile.get('archetype', f'Cluster_{cluster_id}')
                pct = profile.get('percentage', 0)
                report_lines.append(f"    群体{cluster_id} ({archetype}): {count}人 ({pct}%)")
            report_lines.append("")
        
        report_lines.extend([
            "="*70,
            "  报告结束",
            "="*70
        ])
        
        report_text = "\n".join(report_lines)
        
        if output_path:
            import os
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"报告已保存至: {output_path}")
            
        return report_text