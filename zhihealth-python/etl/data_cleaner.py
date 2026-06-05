import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from datetime import datetime
import re
from config.config import VALID_DATA_RANGES, DATA_TYPES

class DataCleaner:
    def __init__(self):
        self.cleaning_stats = {
            "total_records": 0,
            "cleaned_records": 0,
            "removed_records": 0,
            "errors_fixed": 0
        }

    def clean_health_data(self, df: pd.DataFrame) -> pd.DataFrame:
        self.cleaning_stats["total_records"] = len(df)
        logger.info(f"开始清洗数据，共 {len(df)} 条记录")

        df = self._remove_duplicates(df)
        df = self._handle_missing_values(df)
        df = self._validate_data_ranges(df)
        df = self._fix_data_types(df)
        df = self._remove_outliers(df)
        df = self._standardize_timestamps(df)

        self.cleaning_stats["cleaned_records"] = len(df)
        self.cleaning_stats["removed_records"] = self.cleaning_stats["total_records"] - len(df)

        logger.info(f"数据清洗完成: {self.cleaning_stats}")
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        before_count = len(df)
        df = df.drop_duplicates(subset=['device_id', 'user_id', 'timestamp', 'data_type'], keep='last')
        after_count = len(df)
        
        if before_count > after_count:
            removed = before_count - after_count
            logger.info(f"移除重复数据: {removed} 条")
            
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            if df[col].isnull().sum() > 0:
                missing_count = df[col].isnull().sum()
                if col in ['heart_rate', 'body_temp', 'blood_pressure_systolic', 
                           'blood_pressure_diastolic', 'steps', 'sleep_hours']:
                    df[col] = df[col].fillna(df[col].median())
                    self.cleaning_stats["errors_fixed"] += missing_count
                    logger.info(f"列 {col}: 使用中位数填充 {missing_count} 个缺失值")
                elif col in ['device_id', 'user_id']:
                    df = df[df[col].notna()]
                    logger.info(f"列 {col}: 移除 {missing_count} 条缺失关键字的记录")
                    
        return df

    def _validate_data_ranges(self, df: pd.DataFrame) -> pd.DataFrame:
        mask = pd.Series([True] * len(df), index=df.index)
        
        for data_type in DATA_TYPES:
            if data_type in VALID_DATA_RANGES:
                min_val, max_val = VALID_DATA_RANGES[data_type]
                
                if data_type == "heart_rate" and 'heart_rate' in df.columns:
                    mask &= (df['heart_rate'] >= min_val) & (df['heart_rate'] <= max_val)
                elif data_type == "body_temp" and 'body_temp' in df.columns:
                    mask &= (df['body_temp'] >= min_val) & (df['body_temp'] <= max_val)
                elif data_type == "blood_pressure":
                    if 'blood_pressure_systolic' in df.columns:
                        mask &= (df['blood_pressure_systolic'] >= VALID_DATA_RANGES["blood_pressure_systolic"][0]) & \
                               (df['blood_pressure_systolic'] <= VALID_DATA_RANGES["blood_pressure_systolic"][1])
                    if 'blood_pressure_diastolic' in df.columns:
                        mask &= (df['blood_pressure_diastolic'] >= VALID_DATA_RANGES["blood_pressure_diastolic"][0]) & \
                               (df['blood_pressure_diastolic'] <= VALID_DATA_RANGES["blood_pressure_diastolic"][1])
                elif data_type == "steps" and 'steps' in df.columns:
                    mask &= (df['steps'] >= min_val) & (df['steps'] <= max_val)
                elif data_type == "sleep" and 'sleep_hours' in df.columns:
                    mask &= (df['sleep_hours'] >= min_val) & (df['sleep_hours'] <= max_val)

        invalid_count = (~mask).sum()
        if invalid_count > 0:
            logger.warning(f"移除 {invalid_count} 条超出合理范围的数据")
            self.cleaning_stats["errors_fixed"] += invalid_count
            
        return df[mask]

    def _fix_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        type_mappings = {
            'device_id': 'int64',
            'user_id': 'int64',
            'heart_rate': 'float64',
            'body_temp': 'float64',
            'blood_pressure_systolic': 'int32',
            'blood_pressure_diastolic': 'int32',
            'steps': 'int32',
            'sleep_hours': 'float64',
            'timestamp': 'int64'
        }
        
        for col, dtype in type_mappings.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except Exception as e:
                    logger.warning(f"列 {col} 类型转换失败: {e}")
                    
        return df

    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        numeric_cols = ['heart_rate', 'body_temp', 'blood_pressure_systolic', 
                       'blood_pressure_diastolic', 'steps', 'sleep_hours']
        
        for col in numeric_cols:
            if col in df.columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 3 * IQR
                upper_bound = Q3 + 3 * IQR
                
                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                outlier_count = outlier_mask.sum()
                
                if outlier_count > 0:
                    df.loc[outlier_mask, col] = np.nan
                    df[col] = df[col].fillna(df[col].median())
                    self.cleaning_stats["errors_fixed"] += outlier_count
                    logger.info(f"列 {col}: 修正 {outlier_count} 个异常值")
                    
        return df

    def _standardize_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'timestamp' in df.columns:
            current_time = int(datetime.now().timestamp() * 1000)
            
            future_mask = df['timestamp'] > current_time
            if future_mask.sum() > 0:
                logger.warning(f"发现 {future_mask.sum()} 条未来时间戳数据，已移除")
                df = df[~future_mask]
                
            old_time_threshold = current_time - (365 * 24 * 60 * 60 * 1000)
            old_mask = df['timestamp'] < old_time_threshold
            if old_mask.sum() > 0:
                logger.warning(f"发现 {old_mask.sum()} 条过期时间戳数据（超过1年），已移除")
                df = df[~old_mask]
                
        return df

    def get_cleaning_report(self) -> Dict:
        return {
            **self.cleaning_stats,
            "cleaning_rate": f"{(self.cleaning_stats['cleaned_records'] / max(self.cleaning_stats['total_records'], 1)) * 100:.2f}%"
        }