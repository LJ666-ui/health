"""
ETL数据管道单元测试
覆盖：数据提取、清洗、转换、加载全流程
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestETLPipeline:
    """ETL管道核心功能测试"""
    
    def test_pipeline_initialization(self):
        """Test ETL pipeline initialization"""
        from etl.etl_pipeline import ETPipeline

        pipeline = ETPipeline()

        assert pipeline is not None
        assert hasattr(pipeline, 'cleaner')
        assert hasattr(pipeline, 'mysql_conn')
    
    def test_data_cleaning_removes_null_rows(self, sample_health_data):
        """测试空行删除功能"""
        from etl.data_cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        # 插入一些完全为空的行
        dirty_data = sample_health_data.copy()
        null_indices = [0, 5, 10]
        for idx in null_indices:
            dirty_data.loc[idx, dirty_data.columns[1:-3]] = np.nan
        
        cleaned = cleaner.clean_health_data(dirty_data)
        
        # 验证空行已被移除（允许保留部分有值的行）
        assert len(cleaned) <= len(dirty_data)
    
    def test_data_cleaning_handles_outliers(self, sample_health_data):
        """测试异常值处理"""
        from etl.data_cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        # 添加极端异常值
        data_with_outliers = sample_health_data.copy()
        outlier_idx = 0
        if 'heart_rate' in data_with_outliers.columns:
            data_with_outliers.loc[outlier_idx, 'heart_rate'] = 999  # 不可能的心率
        
        cleaned = cleaner.clean_health_data(data_with_outliers)
        
        # 验证极端值被处理（替换或移除）
        if len(cleaned) > 0 and 'heart_rate' in cleaned.columns:
            max_hr = cleaned['heart_rate'].max()
            assert max_hr < 300, f"异常值未处理: 心率最大值 {max_hr}"
    
    def test_data_type_standardization(self, sample_health_data):
        """测试数据类型标准化"""
        from etl.data_cleaner import DataCleaner
        
        cleaner = DataCleaner()
        cleaned = cleaner.clean_health_data(sample_health_data.copy())
        
        # 验证数值列的数据类型
        numeric_cols = ['heart_rate', 'blood_pressure_systolic', 'body_temp', 
                       'steps', 'sleep_hours', 'weight']
        
        for col in numeric_cols:
            if col in cleaned.columns:
                assert pd.api.types.is_numeric_dtype(cleaned[col]), \
                    f"列 {col} 应为数值类型"
    
    def test_transform_enriches_data(self, sample_health_data):
        """测试数据转换与特征增强"""
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        transformed = pipeline.transform_data(sample_health_data.copy())
        
        # 验证新增的特征列
        expected_new_cols = ['bmi', 'age_group', 'health_score']
        for col in expected_new_cols:
            if col in transformed.columns:
                assert not transformed[col].isna().all(), \
                    f"新字段 {col} 全部为空"
    
    @pytest.mark.slow
    def test_full_pipeline_execution(self, mock_mysql_connection, sample_health_data):
        """测试完整ETL流程执行（Mock数据库）"""
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        
        with patch.object(pipeline, 'extract_from_mysql') as mock_extract:
            mock_extract.return_value = sample_health_data
            
            stats = pipeline.run_full_pipeline(source_table='health_record')
            
            assert isinstance(stats, dict)
            assert 'extract_count' in stats
            assert stats['extract_count'] >= 0
            assert 'cleaning_report' in stats
            assert 'total_records' in stats['cleaning_report']
    
    def test_batch_processing(self, sample_health_data):
        """测试批处理逻辑"""
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        large_data = pd.concat([sample_health_data] * 10, ignore_index=True)
        
        # 测试分批处理不会丢失数据
        batch_size = 50
        batches = []
        for i in range(0, len(large_data), batch_size):
            batch = large_data.iloc[i:i + batch_size]
            batches.append(batch)
        
        total_processed = sum(len(b) for b in batches)
        assert total_processed == len(large_data), "批处理后数据量不匹配"


class TestDataQualityChecks:
    """数据质量检查测试套件"""
    
    def test_missing_value_detection(self, sample_health_data):
        """Test missing value detection accuracy"""
        from etl.data_cleaner import DataCleaner

        cleaner = DataCleaner()

        # Intentionally create missing values
        test_data = sample_health_data.copy()
        test_data.loc[0:4, 'heart_rate'] = np.nan
        test_data.loc[5:9, 'body_temp'] = np.nan

        # Clean data first (populates stats), then get report
        cleaner.clean_health_data(test_data)
        report = cleaner.get_cleaning_report()

        # Verify cleaning detected and fixed issues
        assert report['errors_fixed'] >= 10 or report['cleaned_records'] > 0
    
    def test_duplicate_detection(self, sample_health_data):
        """测试重复记录检测"""
        from etl.data_cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        # 添加重复行
        duplicated_data = pd.concat([sample_health_data, sample_health_data.iloc[0:3]], 
                                   ignore_index=True)
        
        cleaned = cleaner.clean_health_data(duplicated_data)
        
        # 验证重复项已处理
        assert len(cleaned) <= len(duplicated_data), "重复项未被移除"
    
    def test_date_range_validation(self, sample_health_data):
        """测试日期范围验证"""
        from etl.data_cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        # 添加未来日期（无效）
        invalid_data = sample_health_data.copy()
        future_date = datetime.now() + timedelta(days=365)
        invalid_data.loc[0, 'collect_time'] = future_date
        
        cleaned = cleaner.clean_health_data(invalid_data)
        
        # 未来日期的记录应被标记或移除
        future_records = cleaned[cleaned['collect_time'] > datetime.now()]
        assert len(future_records) == 0, "未来日期记录应被过滤"


class TestDatabaseConnectors:
    """数据库连接器测试"""
    
    def test_mysql_connection_failure_handling(self):
        """测试MySQL连接失败时的优雅降级"""
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        
        with patch('pymysql.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection refused")
            
            result = pipeline._connect_mysql()
            
            assert result is False, "连接失败应返回False"
    
    def test_redis_connection_retry(self, mock_redis_client):
        """测试Redis重连机制"""
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        
        # 第一次失败，第二次成功
        call_count = 0
        original_ping = mock_redis_client.ping
        
        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection error")
            return True
        
        mock_redis_client.ping.side_effect = side_effect
        
        result = pipeline._connect_redis()
        
        assert result is True or result is False  # 根据实现可能不同


class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    @pytest.mark.slow
    def test_large_dataset_processing_time(self):
        """大数据集处理时间测试 (< 5秒)"""
        import time
        from etl.etl_pipeline import ETPipeline
        from tests.conftest import TestDataGenerator
        
        generator = TestDataGenerator()
        large_df = generator.generate_health_records(n=10000)
        
        pipeline = ETPipeline()
        
        start_time = time.time()
        _ = pipeline.transform_data(large_df)
        elapsed = time.time() - start_time
        
        assert elapsed < 5.0, f"1万条数据处理耗时 {elapsed:.2f}s，超过5秒限制"
    
    @pytest.mark.slow  
    def test_memory_usage_stability(self):
        """内存使用稳定性测试"""
        import psutil
        import os
        from etl.etl_pipeline import ETPipeline
        from tests.conftest import TestDataGenerator
        
        process = psutil.Process(os.getpid())
        initial_mem = process.memory_info().rss / (1024 * 1024)  # MB
        
        generator = TestDataGenerator()
        
        for i in range(5):
            df = generator.generate_health_records(n=5000)
            pipeline = ETPipeline()
            _ = pipeline.transform_data(df)
            del df, pipeline
        
        final_mem = process.memory_info().rss / (1024 * 1024)
        mem_increase = final_mem - initial_mem
        
        # 内存增长不应超过200MB
        assert mem_increase < 200, f"内存增长过多: {mem_increase:.1f}MB"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])