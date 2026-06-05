"""
ZhiHealth 单元测试配置与Fixtures
提供Mock数据、测试客户端、数据库连接等共享资源
"""

import os
import sys
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 测试数据生成器 ====================

class TestDataGenerator:
    """测试数据生成工具类"""
    
    @staticmethod
    def generate_health_records(n: int = 100, seed: int = 42) -> pd.DataFrame:
        """生成模拟健康记录数据"""
        np.random.seed(seed)
        
        now = datetime.now()
        base_time = now - timedelta(days=30)
        
        data = {
            'id': range(1, n + 1),
            'record_id': [f'REC-{i:06d}' for i in range(1, n + 1)],
            'user_id': np.random.choice([1, 2, 3, 4, 5], n),
            'device_id': np.random.choice([101, 102, 103, None], n),
            'data_type': np.random.choice(
                ['heart_rate', 'blood_pressure', 'body_temp', 'steps', 'sleep'], 
                n
            ),
            'heart_rate': np.clip(np.random.normal(75, 15, n), 40, 200).round(1),
            'blood_pressure_systolic': np.clip(np.random.normal(120, 20, n), 80, 200).astype(int),
            'blood_pressure_diastolic': np.clip(np.random.normal(80, 12, n), 50, 130).astype(int),
            'body_temp': np.clip(np.random.normal(36.6, 0.5, n), 35.0, 42.0).round(1),
            'blood_oxygen': np.clip(np.random.normal(98, 2, n), 85, 100).round(1),
            'steps': np.random.randint(500, 25000, n),
            'calories': np.round(np.random.uniform(100, 3000, n), 2),
            'distance': np.round(np.random.uniform(0.5, 20, n), 2),
            'sleep_hours': np.clip(np.random.normal(7, 1.5, n), 2, 12).round(1),
            'sleep_quality': np.random.randint(1, 6, n),
            'weight': np.round(np.random.normal(65, 15, n), 1),
            'height': np.round(np.random.normal(170, 10, n), 1),
            'bmi': np.round(np.random.normal(23, 4, n), 1),
            'collect_time': [
                base_time + timedelta(hours=np.random.randint(0, 720))
                for _ in range(n)
            ],
            'timestamp': [
                int((base_time + timedelta(hours=np.random.randint(0, 720))).timestamp() * 1000)
                for _ in range(n)
            ],
            'data_source': np.random.choice(['manual', 'device', 'api', 'import'], n),
            'quality_score': np.random.randint(60, 101, n),
            'is_abnormal': np.random.choice([0, 0, 0, 1], n),
        }
        
        df = pd.DataFrame(data)
        
        # 根据data_type填充缺失值（模拟真实场景）
        for idx, row in df.iterrows():
            dtype = row['data_type']
            if dtype == 'heart_rate':
                df.loc[idx, ['blood_pressure_systolic', 'blood_pressure_diastolic', 
                             'steps', 'sleep_hours']] = [None, None, None, None]
            elif dtype == 'blood_pressure':
                df.loc[idx, ['heart_rate', 'steps', 'sleep_hours']] = [None, None, None]
            elif dtype == 'body_temp':
                df.loc[idx, ['heart_rate', 'blood_pressure_systolic', 'steps']] = [None, None, None]
            elif dtype == 'steps':
                df.loc[idx, ['heart_rate', 'blood_pressure_systolic', 'body_temp', 'sleep_hours']] = \
                    [None, None, None, None]
            elif dtype == 'sleep':
                df.loc[idx, ['heart_rate', 'blood_pressure_systolic', 'steps']] = [None, None, None]
        
        return df
    
    @staticmethod
    def generate_anomaly_data(n: int = 50) -> pd.DataFrame:
        """生成包含异常值的数据集（用于测试异常检测）"""
        normal_data = TestDataGenerator.generate_health_records(n - 10)
        
        # 添加明显异常的数据点
        anomalies = {
            'id': range(n - 9, n + 1),
            'record_id': [f'ANOMALY-{i}' for i in range(10)],
            'user_id': [99] * 10,
            'device_id': [999] * 10,
            'data_type': ['heart_rate'] * 5 + ['blood_pressure'] * 5,
            'heart_rate': [180, 195, 210, 35, 25] + [None] * 5,
            'blood_pressure_systolic': [None] * 5 + [220, 240, 200, 190, 230],
            'blood_pressure_diastolic': [None] * 5 + [140, 150, 120, 110, 145],
            'body_temp': [40.5, 41.2, 34.0] + [None] * 7,
            'blood_oxygen': [75, 70, 65] + [None] * 7,
            'steps': [None] * 10,
            'calories': [None] * 10,
            'distance': [None] * 10,
            'sleep_hours': [None] * 10,
            'sleep_quality': [None] * 10,
            'weight': [None] * 10,
            'height': [None] * 10,
            'bmi': [None] * 10,
            'collect_time': [datetime.now()] * 10,
            'data_source': ['test'] * 10,
            'quality_score': [100] * 10,
            'is_abnormal': [1] * 10,
        }
        
        anomaly_df = pd.DataFrame(anomalies)
        
        return pd.concat([normal_data, anomaly_df], ignore_index=True)
    
    @staticmethod
    def generate_alert_rules() -> list:
        """生成告警规则测试数据"""
        return [
            {
                'rule_name': '心率过高',
                'rule_code': 'hr_high',
                'metric': 'heart_rate',
                'condition_operator': '>',
                'condition_value': 120.0,
                'severity': 2,
                'cooldown_seconds': 300,
                'enabled': True,
                'notify_channels': 'email,in_app'
            },
            {
                'rule_name': '血压危象',
                'rule_code': 'bp_crisis',
                'metric': 'blood_pressure_systolic',
                'condition_operator': '>',
                'condition_value': 180.0,
                'severity': 3,
                'cooldown_seconds': 600,
                'enabled': True,
                'notify_channels': 'email,sms,in_app'
            },
            {
                'rule_name': '体温异常',
                'rule_code': 'temp_high',
                'metric': 'body_temp',
                'condition_operator': '>',
                'condition_value': 39.5,
                'severity': 3,
                'cooldown_seconds': 3600,
                'enabled': True,
                'notify_channels': 'in_app,email'
            }
        ]
    
    @staticmethod
    def generate_api_test_user() -> dict:
        """生成API测试用户"""
        return {
            'user_id': 999,
            'username': 'test_user',
            'password': 'TestPassword123!',
            'role': 'admin',
            'permissions': ['read', 'write', 'delete']
        }


# ==================== Pytest Fixtures ====================

@pytest.fixture(scope='session')
def test_data_generator():
    """全局测试数据生成器"""
    return TestDataGenerator()


@pytest.fixture(scope='session')
def sample_health_data(test_data_generator):
    """标准健康数据样本 (100条)"""
    return test_data_generator.generate_health_records(n=100)


@pytest.fixture(scope='session')
def anomaly_health_data(test_data_generator):
    """包含异常值的健康数据 (50条)"""
    return test_data_generator.generate_anomaly_data(n=50)


@pytest.fixture(scope='session')
def alert_rules_data(test_data_generator):
    """告警规则测试数据"""
    return test_data_generator.generate_alert_rules()


@pytest.fixture(scope='session')
def test_user():
    """API测试用户"""
    return TestDataGenerator.generate_api_test_user()


@pytest.fixture
def mock_mysql_connection():
    """Mock MySQL连接"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = []
    mock_conn.cursor.return_value = mock_cursor
    
    with patch('pymysql.connect') as mock_connect:
        mock_connect.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_redis_client():
    """Mock Redis客户端"""
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_redis.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_mongodb_client():
    """Mock MongoDB客户端"""
    with patch('pymongo.MongoClient') as mock_mongo:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo.return_value = mock_db
        yield mock_db


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB客户端"""
    with patch('influxdb_client.InfluxDBClient') as mock_influx:
        mock_instance = MagicMock()
        mock_instance.write_api.return_value = MagicMock()
        mock_instance.query_api.return_value = MagicMock()
        mock_influx.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def api_client():
    """Flask测试客户端"""
    from api.rest_server import app
    
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret-key-12345'
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_headers(api_client, test_user):
    """带认证的请求头"""
    from api.auth_utils import generate_token
    
    token = generate_token(test_user['user_id'], test_user['role'])
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture
def temp_csv_file(sample_health_data, tmp_path):
    """临时CSV文件fixture"""
    file_path = tmp_path / "test_data.csv"
    sample_health_data.to_csv(file_path, index=False, encoding='utf-8-sig')
    return str(file_path)


@pytest.fixture
def temp_json_file(tmp_path):
    """临时JSON文件fixture"""
    data = {'key': 'value', 'nested': {'count': 42}}
    file_path = tmp_path / "test_config.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return str(file_path)


# ==================== 自定义断言助手 ====================

class CustomAssertions:
    """自定义断言方法集合"""
    
    @staticmethod
    def assert_dataframe_shape(df, expected_rows=None, expected_cols=None):
        """验证DataFrame形状"""
        if expected_rows is not None:
            assert len(df) == expected_rows, \
                f"行数不匹配: 期望 {expected_rows}, 实际 {len(df)}"
        if expected_cols is not None:
            assert len(df.columns) == expected_cols, \
                f"列数不匹配: 期望 {expected_cols}, 实际 {len(df.columns)}"
    
    @staticmethod
    def assert_api_response(response, expected_status=200, check_keys=None):
        """验证API响应格式"""
        data = response.get_json()
        
        assert response.status_code == expected_status, \
            f"状态码错误: 期望 {expected_status}, 实际 {response.status_code}, 响应: {data}"
        
        assert 'code' in data, "响应缺少code字段"
        assert 'message' in data, "响应缺少message字段"
        assert 'data' in data or 'error' in data, "响应缺少data或error字段"
        
        if check_keys and 'data' in data:
            for key in check_keys:
                assert key in data['data'], f"响应数据缺少字段: {key}"
                
        return data
    
    @staticmethod
    def assert_cleaning_stats(stats, expected_total=None, expected_cleaned=None):
        """验证ETL清洗统计信息"""
        assert isinstance(stats, dict), "stats应为字典类型"
        assert 'total_records' in stats, "缺少total_records字段"
        assert 'cleaned_records' in stats, "缺少cleaned_records字段"
        
        if expected_total is not None:
            assert stats['total_records'] >= expected_total
            
        if expected_cleaned is not None:
            assert stats['cleaned_records'] >= expected_cleaned
    
    @staticmethod
    def assert_ai_prediction(predictions, min_count=1):
        """验证AI预测结果格式"""
        assert isinstance(predictions, list), "预测结果应为列表"
        assert len(predictions) >= min_count, f"预测结果数量不足: {len(predictions)} < {min_count}"
        
        required_fields = ['user_id', 'predicted_risk_level', 'confidence', 'recommendation']
        for pred in predictions[:3]:
            for field in required_fields:
                assert field in pred, f"预测结果缺少字段: {field}"


# 将自定义断言注入到pytest命名空间
@pytest.fixture
def assertions():
    """自定义断言助手"""
    return CustomAssertions()


# ==================== 性能基准测试标记 ====================

def pytest_configure(config):
    """注册自定义pytest标记"""
    config.addinivalue_line("markers", "slow: 标记运行时间较长的测试")
    config.addinivalue_line("markers", "integration: 集成测试（需要外部服务）")
    config.addinivalue_line("markers", "unit: 单元测试（纯逻辑）")


# ==================== 测试输出增强 ====================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Enhance failure output with context info"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        longrepr = getattr(report, 'longrepr', '')
        if hasattr(longrepr, 'addsection'):
            try:
                _loc = item.location[1] if hasattr(item, 'location') else 'N/A'
            except (TypeError, IndexError):
                _loc = 'N/A'
            longrepr.addsection("ZhiHealth Context",
                              f"Test: {item.name}\nFile: {item.fspath}:{_loc}")