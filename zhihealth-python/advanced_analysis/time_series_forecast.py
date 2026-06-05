"""
增强型时间序列预测引擎
整合多种算法：Prophet、LSTM、ARIMA、XGBoost
支持多步预测、置信区间、异常点检测
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger


class TimeSeriesModelType(Enum):
    """时间序列模型类型"""
    PROPHET = "prophet"
    LSTM = "lstm"
    ARIMA = "arima"
    XGBOOST = "xgboost"
    ENSEMBLE = "ensemble"           # 集成模型
    AUTO_SELECT = "auto"            # 自动选择最优模型


class SeasonalityType(Enum):
    """季节性类型"""
    DAILY = "daily"                 # 日周期 (24小时)
    WEEKLY = "weekly"               # 周周期 (7天)
    MONTHLY = "monthly"             # 月周期 (30天)
    YEARLY = "yearly"               # 年周期 (365天)


@dataclass
class ForecastResult:
    """预测结果数据结构"""
    model_type: str
    target_metric: str
    
    # 历史拟合值
    historical_dates: List[str] = field(default_factory=list)
    historical_actual: List[float] = field(default_factory=list)
    historical_fitted: List[float] = field(default_factory=list)
    
    # 未来预测值
    forecast_dates: List[str] = field(default_factory=list)
    forecast_values: List[float] = field(default_factory=list)
    
    # 置信区间
    lower_bound: List[float] = field(default_factory=list)
    upper_bound: List[float] = field(default_factory=list)
    
    # 模型评估指标
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # 异常检测
    anomaly_indices: List[int] = field(default_factory=list)
    anomaly_scores: List[float] = field(default_factory=list)
    
    # 元信息
    training_period: Optional[str] = None
    forecast_horizon: int = 7
    confidence_level: float = 0.95
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """转换为字典格式（用于API响应）"""
        return {
            'modelType': self.model_type,
            'targetMetric': self.target_metric,
            'historical': {
                'dates': self.historical_dates,
                'actual': self.historical_actual,
                'fitted': self.historical_fitted
            },
            'forecast': {
                'dates': self.forecast_dates,
                'values': self.forecast_values,
                'lowerBound': self.lower_bound,
                'upperBound': self.upper_bound
            },
            'metrics': self.metrics,
            'anomalies': {
                'indices': self.anomaly_indices,
                'scores': self.anomaly_scores
            },
            'meta': {
                'trainingPeriod': self.training_period,
                'forecastHorizon': self.forecast_horizon,
                'confidenceLevel': self.confidence_level,
                'generatedAt': self.generated_at
            }
        }


class BaseTimeSeriesModel(ABC):
    """时间序列预测模型基类"""
    
    def __init__(self, 
                 name: str, 
                 seasonality: List[SeasonalityType] = None):
        self.name = name
        self.seasonality = seasonality or [SeasonalityType.DAILY]
        self.is_fitted = False
        self.model_params: Dict = {}
        
    @abstractmethod
    def fit(self, df: pd.DataFrame, date_col: str = 'date', value_col: str = 'value') -> 'BaseTimeSeriesModel':
        """
        训练模型
        
        Args:
            df: 时间序列DataFrame，必须包含日期列和值列
            date_col: 日期列名
            value_col: 值列名
            
        Returns:
            self (支持链式调用)
        """
        pass
    
    @abstractmethod
    def predict(self, horizon: int = 7) -> ForecastResult:
        """
        进行未来预测
        
        Args:
            horizon: 预测步长（天数/小时数等）
            
        Returns:
            ForecastResult对象
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        pass


class ProphetModel(BaseTimeSeriesModel):
    """
    Facebook Prophet 时间序列模型
    适合：具有明显季节性和趋势的数据
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="Prophet", **kwargs)
        self._model = None
        self._forecast_df = None
        
    def fit(self, df: pd.DataFrame, date_col: str = 'ds', value_col: str = 'y') -> 'ProphetModel':
        try:
            from prophet import Prophet
        except ImportError:
            logger.warning("Prophet未安装，使用简化实现")
            return self._fit_simplified(df, date_col, value_col)
        
        prophet_df = df[[date_col, value_col]].copy()
        prophet_df.columns = ['ds', 'y']
        
        # 配置季节性
        seasonality_modes = {'daily': 'daily', 'weekly': 'weekly', 'yearly': 'yearly'}
        
        self._model = Prophet(
            yearly_seasonality=SeasonalityType.YEARLY in self.seasonality,
            weekly_seasonality=SeasonalityType.WEEKLY in self.seasonality,
            daily_seasonality=SeasonalityType.DAILY in self.seasonality,
            interval_width=0.95,       # 95%置信区间
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10
        )
        
        # 添加自定义季节性
        if SeasonalityType.MONTHLY in self.seasonality:
            self._model.add_seasonality(
                name='monthly',
                period=30.5,
                fourier_order=5
            )
        
        self._model.fit(prophet_df)
        self.is_fitted = True
        
        logger.info(f"[Prophet] 模型训练完成 | 数据量: {len(df)} | 季节性: {[s.value for s in self.seasonality]}")
        return self
    
    def predict(self, horizon: int = 7) -> ForecastResult:
        if not self.is_fitted or not self._model:
            raise RuntimeError("模型尚未训练，请先调用fit()")
        
        future = self._model.make_future_dataframe(periods=horizon)
        self._forecast_df = self._model.predict(future)
        
        forecast_part = self._forecast_df.tail(horizon)
        historical_part = self._forecast_df.iloc[:-horizon]
        
        result = ForecastResult(
            model_type=TimeSeriesModelType.PROPHET.value,
            target_metric=self._model.history['y'].name if hasattr(self._model.history['y'], 'name') else 'value',
            
            historical_dates=historical_part['ds'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
            historical_actual=self._model.history['y'].tolist(),
            historical_fitted=historical_part['yhat'].tolist(),
            
            forecast_dates=forecast_part['ds'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
            forecast_values=forecast_part['yhat'].tolist(),
            lower_bound=forecast_part['yhat_lower'].tolist(),
            upper_bound=forecast_part['yhat_upper'].tolist(),
            
            forecast_horizon=horizon,
            confidence_level=0.95
        )
        
        # 异常检测（基于残差）
        residuals = np.array(historical_part['y']) - np.array(historical_part['yhat'])
        std_residuals = (residuals - np.mean(residuals)) / np.std(residuals)
        anomaly_idx = np.where(np.abs(std_residuals) > 2.5)[0].tolist()
        
        result.anomaly_indices = anomaly_idx
        result.anomaly_scores = [abs(std_residuals[i]) for i in anomaly_idx]
        
        # 模型指标
        y_true = self._model.history['y'].values
        y_pred = historical_part['yhat'].values[:len(y_true)]
        
        result.metrics = {
            'mae': float(np.mean(np.abs(y_true - y_pred))),
            'rmse': float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
            'mape': float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100),
            'r_squared': float(1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - np.mean(y_true))**2))
        }
        
        return result
    
    def get_model_info(self) -> Dict:
        return {
            'modelName': 'Facebook Prophet',
            'version': '1.1.x',
            'isFitted': self.is_fitted,
            'seasonality': [s.value for s in self.seasonality],
            'params': {
                'changepointPriorScale': 0.05,
                'seasonalityPriorScale': 10,
                'intervalWidth': 0.95
            }
        }
    
    def _fit_simplified(self, df, date_col, value_col):
        """简化的类Prophet实现（无依赖时使用）"""
        logger.info("使用简化版时间序列模型")
        
        df_sorted = df.sort_values(date_col)
        self._simple_data = df_sorted[value_col].values
        self._simple_dates = df_sorted[date_col].values
        
        self.is_fitted = True
        return self


class LSTMForecastModel(BaseTimeSeriesModel):
    """
    LSTM神经网络时间序列预测
    适合：非线性、复杂模式的时间序列
    """
    
    def __init__(self, sequence_length: int = 30, hidden_units: int = 50, **kwargs):
        super().__init__(name="LSTM", **kwargs)
        self.sequence_length = sequence_length
        self.hidden_units = hidden_units
        self._model = None
        self.scaler = None
        
    def fit(self, df: pd.DataFrame, date_col: str = 'date', value_col: str = 'value') -> 'LSTMForecastModel':
        try:
            from sklearn.preprocessing import MinMaxScaler
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
        except ImportError:
            logger.warning("TensorFlow/Keras未安装，LSTM模型不可用")
            self.is_fitted = False
            return self
        
        data = df.sort_values(date_col)[value_col].values.reshape(-1, 1)
        
        # 数据归一化
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = self.scaler.fit_transform(data)
        
        # 创建序列数据集
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i, 0])
            y.append(scaled_data[i, 0])
        
        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        # 构建LSTM模型
        self._model = Sequential([
            LSTM(units=self.hidden_units, return_sequences=True, input_shape=(X.shape[1], 1)),
            Dropout(0.2),
            LSTM(units=self.hidden_units // 2, return_sequences=False),
            Dropout(0.2),
            Dense(units=25),
            Dense(units=1)
        ])
        
        self._model.compile(optimizer='adam', loss='mean_squared_error')
        
        # 训练
        history = self._model.fit(
            X, y,
            epochs=50,
            batch_size=32,
            validation_split=0.1,
            verbose=0,
            shuffle=False
        )
        
        self.is_fitted = True
        self._train_data = (data, scaled_data, X, y)
        self._dates = df.sort_values(date_col)[date_col].values
        
        final_loss = history.history['loss'][-1]
        val_loss = history.history.get('val_loss', [final_loss])[-1]
        
        logger.info(f"[LSTM] 模型训练完成 | Loss: {final_loss:.6f} | ValLoss: {val_loss:.6f}")
        return self
    
    def predict(self, horizon: int = 7) -> ForecastResult:
        if not self.is_fitted or not self._model:
            raise RuntimeError("LSTM模型尚未训练")
        
        data, scaled_data, _, _ = self._train_data
        dates = self._dates
        
        # 历史拟合
        predictions = []
        current_batch = scaled_data[-self.sequence_length:].reshape(1, self.sequence_length, 1)
        
        for i in range(len(scaled_data) - self.sequence_length + horizon):
            pred = self._model.predict(current_batch.reshape(1, self.sequence_length, 1), verbose=0)[0][0]
            predictions.append(pred)
            current_batch = np.roll(current_batch, -1)
            current_batch[0][-1] = pred
        
        # 反归一化
        all_predictions = self.scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten()
        
        split_point = len(scaled_data) - self.sequence_length
        hist_pred = all_predictions[:split_point]
        fore_pred = all_predictions[split_point:]
        
        # 计算置信区间（基于历史误差）
        hist_errors = np.abs(data[self.sequence_length:] - hist_pred[:len(data)-self.sequence_length])
        std_error = np.std(hist_errors) * 1.96  # 95% CI
        
        result = ForecastResult(
            model_type=TimeSeriesModelType.LSTM.value,
            target_metric='value',
            
            historical_dates=[str(d)[:16] for d in dates[self.sequence_length:]],
            historical_actual=data[self.sequence_length:].flatten().tolist(),
            historical_fitted=hist_pred[:len(data)-self.sequence_length].tolist(),
            
            forecast_dates=[(datetime.strptime(str(dates[-1])[:19], '%Y-%m-%d %H:%M:%S') + timedelta(days=i+1)).strftime('%Y-%m-%d')
                           for i in range(horizon)],
            forecast_values=fore_pred.tolist(),
            lower_bound=(fore_pred - std_error).tolist(),
            upper_bound=(fore_pred + std_error).tolist(),
            
            forecast_horizon=horizon,
            confidence_level=0.95
        )
        
        # 指标计算
        actual = data[self.sequence_length:].flatten()
        fitted = hist_pred[:len(actual)]
        result.metrics = {
            'mae': float(np.mean(np.abs(actual - fitted))),
            'rmse': float(np.sqrt(np.mean((actual - fitted) ** 2)))
        }
        
        return result
    
    def get_model_info(self) -> Dict:
        return {
            'modelName': 'LSTM Neural Network',
            'architecture': f'LSTM({self.hidden_units}) -> LSTM({self.hidden_units//2}) -> Dense',
            'sequenceLength': self.sequence_length,
            'isFitted': self.is_fitted,
            'framework': 'TensorFlow/Keras'
        }


class ARIMAModel(BaseTimeSeriesModel):
    """
    ARIMA传统统计模型
    适合：平稳或可差分平稳的时间序列
    """
    
    def __init__(self, order: Tuple[int, int, int] = (5, 1, 0), **kwargs):
        super().__init__(name="ARIMA", **kwargs)
        self.order = order
        self._arima_model = None
        
    def fit(self, df: pd.DataFrame, date_col: str = 'date', value_col: str = 'value') -> 'ARIMAModel':
        try:
            from statsmodels.tsa.arima.model import ARIMA as ARIMA_Model
        except ImportError:
            logger.warning("statsmodels未安装，ARIMA不可用")
            return self
        
        series = df.sort_values(date_col)[value_col]
        
        # 自动确定最优参数（简化版）
        try:
            from pmdarima import auto_arima
            auto_model = auto_arima(
                series,
                seasonal=True,
                m=7 if SeasonalityType.WEEKLY in self.seasonality else 1,
                suppress_warnings=True,
                stepwise=True,
                trace=0
            )
            best_order = auto_model.order
            best_seasonal_order = auto_model.seasonal_order
            logger.info(f"[ARIMA] 自动选参: ARIMA{best_order} x {best_seasonal_order}")
        except:
            best_order = self.order
            best_seasonal_order = (0, 0, 0, 0)
        
        self._arima_model = ARIMA_Model(series, order=best_order, seasonal_order=best_seasonal_order)
        self._arima_result = self._arima_model.fit(disp=0)
        
        self.is_fitted = True
        self._series = series
        self._dates = df.sort_values(date_col)[date_col]
        
        logger.info(f"[ARIMA] 模型训练完成 | AIC: {self._arima_result.aic:.2f}")
        return self
    
    def predict(self, horizon: int = 7) -> ForecastResult:
        if not self.is_fitted or not self._arima_result:
            raise RuntimeError("ARIMA模型尚未训练")
        
        # 获取拟合值
        fitted_values = self._arima_result.fittedvalues
        
        # 预测未来
        forecast_obj = self._arima_result.get_forecast(steps=horizon)
        forecast_mean = forecast_obj.predicted_mean
        conf_int = forecast_obj.conf_int(alpha=0.05)
        
        result = ForecastResult(
            model_type=TimeSeriesModelType.ARIMA.value,
            target_metric=str(self._series.name),
            
            historical_dates=[str(d)[:16] for d in self._dates[len(self._series) - len(fitted_values):]],
            historical_actual=self._series.values.tolist(),
            historical_fitted=fitted_values.tolist() + [None] * (len(self._series) - len(fitted_values)),
            
            forecast_dates=[d.strftime('%Y-%m-%d') for d in forecast_mean.index],
            forecast_values=forecast_mean.values.tolist(),
            lower_bound=conf_int.iloc[:, 0].tolist(),
            upper_bound=conf_int.iloc[:, 1].tolist(),
            
            forecast_horizon=horizon,
            confidence_level=0.95
        )
        
        # 指标
        valid_mask = ~np.isnan(fitted_values)
        if valid_mask.any():
            actual = self._series.values[valid_mask]
            pred = fitted_values.values[valid_mask]
            result.metrics = {
                'aic': float(self._arima_result.aic),
                'bic': float(self._arima_result.bic),
                'rmse': float(np.sqrt(np.mean((actual - pred) ** 2)))
            }
        
        return result
    
    def get_model_info(self) -> Dict:
        return {
            'modelName': 'ARIMA',
            'order': self.order,
            'isFitted': self.is_fitted,
            'framework': 'statsmodels'
        }