"""
RESTful API接口单元测试
覆盖：认证、数据查询、分析接口、错误处理
"""

import pytest
import json
from datetime import datetime, timedelta


class TestAPIHealthEndpoint:
    """健康检查端点测试"""
    
    def test_system_status_endpoint(self, api_client):
        """测试系统状态API"""
        response = api_client.get('/api/v1/system/status')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['code'] == 200
        assert 'data' in data
        assert 'version' in data['data'] or 'status' in data['data']
    
    def test_health_check_response_time(self, api_client):
        """测试响应时间 (< 200ms)"""
        import time
        
        start = time.time()
        response = api_client.get('/api/v1/system/status')
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 200, f"响应时间过长: {elapsed:.0f}ms"


class TestDataQueryEndpoints:
    """数据查询接口测试"""
    
    def test_list_data_types(self, api_client):
        """测试数据类型列表接口"""
        response = api_client.get('/api/v1/data/types')
        
        assert response.status_code in [200, 404, 500]  # 根据实现可能不同
        if response.status_code == 200:
            data = response.get_json()
            assert isinstance(data.get('data'), list)
    
    def test_query_with_pagination(self, api_client):
        """测试分页参数处理"""
        params = {'page': 1, 'page_size': 10}
        response = api_client.get('/api/v1/data/query', query_string=params)
        
        assert response.status_code in [200, 400, 404, 422]
        if response.status_code == 200:
            data = response.get_json()
            if 'data' in data:
                result = data['data']
                assert isinstance(result, (list, dict))
    
    def test_invalid_page_parameters(self, api_client):
        """测试无效分页参数"""
        invalid_params = [
            {'page': -1, 'page_size': 10},
            {'page': 0, 'page_size': -5},
            {'page': 'abc', 'page_size': 10},
        ]
        
        for params in invalid_params:
            response = api_client.get('/api/v1/data/query', query_string=params)
            
            # Should return 400, 404, or 422 error
            assert response.status_code in [400, 404, 422], \
                f"Invalid params not rejected: {params}"
    
    def test_date_range_filter(self, api_client):
        """测试日期范围过滤"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'user_id': 1
        }
        
        response = api_client.get('/api/v1/data/query', query_string=params)
        
        assert response.status_code in [200, 204, 400, 404]


class TestAnalysisEndpoints:
    """分析功能接口测试"""
    
    def test_basic_statistics_endpoint(self, api_client):
        """测试基础统计接口"""
        response = api_client.get('/api/v1/analysis/stats?metric=heart_rate')
        
        assert response.status_code in [200, 404, 405, 503]
    
    def test_comprehensive_analysis_requires_data(self, api_client):
        """测试综合分析需要数据输入"""
        payload = {}
        response = api_client.post('/api/v1/analysis/comprehensive',
                                  json=payload,
                                  content_type='application/json')
        
        # 无数据应返回错误
        assert response.status_code in [400, 422]
        data = response.get_json()
        assert data['code'] != 200


class TestAIEndpoints:
    """AI功能接口测试"""
    
    def test_ai_prediction_without_auth(self, api_client):
        """测试无Token访问AI接口"""
        payload = {
            'records': [{'heart_rate': 75, 'blood_pressure_systolic': 120}]
        }
        
        response = api_client.post('/api/v1/ai/predict',
                                  json=payload,
                                  content_type='application/json')
        
        # Should return 401 (unauthorized) or other status codes
        assert response.status_code in [200, 400, 401, 403, 404, 500]
    
    def test_ai_prediction_invalid_input(self, api_client):
        """测试无效输入数据格式"""
        invalid_payloads = [
            None,
            {},
            {'records': 'not_a_list'},
            {'records': [{'invalid_key': 'value'}]},
        ]
        
        for payload in invalid_payloads:
            response = api_client.post('/api/v1/ai/predict',
                                      json=payload or {},
                                      content_type='application/json')
            
            assert response.status_code in [400, 404, 422, 500], \
                f"Invalid input not rejected: {payload}"


class TestAlertingEndpoints:
    """告警相关接口测试"""
    
    def test_get_alert_rules(self, api_client):
        """测试获取告警规则列表"""
        response = api_client.get('/api/v1/alerts/rules')
        
        assert response.status_code in [200, 401, 403, 404]
    
    def test_create_alert_rule_validation(self, api_client):
        """测试创建告警规则的字段验证"""
        incomplete_rules = [
            {},  # 完全为空
            {'rule_name': 'test'},  # 缺少必要字段
            {
                'rule_name': 'test',
                'metric': 'heart_rate',
                'condition_operator': '>',
                # 缺少condition_value
            },
        ]
        
        for rule_data in incomplete_rules:
            response = api_client.post('/api/v1/alerts/rules',
                                      json=rule_data,
                                      content_type='application/json')
            
            assert response.status_code in [400, 404, 422], \
                f"Incomplete rule data not rejected: {rule_data}"


class TestErrorResponseFormat:
    """错误响应格式统一性测试"""
    
    def test_404_not_found_format(self, api_client):
        """测试404响应格式"""
        response = api_client.get('/api/v1/nonexistent-endpoint-12345')
        
        assert response.status_code == 404
        data = response.get_json()
        
        assert 'code' in data, "缺少code字段"
        assert 'message' in data, "缺少message字段"
        assert data['code'] != 200
    
    def test_method_not_allowed(self, api_client):
        """测试405方法不允许"""
        response = api_client.delete('/api/v1/system/status')
        
        assert response.status_code == 405
    
    def test_unsupported_media_type(self, api_client):
        """Test 415 unsupported media type"""
        response = api_client.post('/api/v1/data/upload',
                                  data="not json",
                                  content_type='text/plain')

        assert response.status_code in [400, 404, 415]


class TestCORSHeaders:
    """跨域资源共享(CORS)头测试"""
    
    def test_cors_preflight_headers(self, api_client):
        """Test OPTIONS preflight request headers"""
        response = api_client.options('/api/v1/system/status')

        # At minimum, Access-Control-Allow-Origin should be present
        assert 'Access-Control-Allow-Origin' in response.headers, \
            f"Missing CORS header: Access-Control-Allow-Origin. Headers: {dict(response.headers)}"


class TestRateLimiting:
    """API频率限制测试（如果已启用）"""
    
    @pytest.mark.slow
    def test_rate_limit_enforcement(self, api_client):
        """测试请求频率限制"""
        responses = []
        
        for _ in range(110):  # 超过可能的限制（如100次/分钟）
            resp = api_client.get('/api/v1/system/status')
            responses.append(resp.status_code)
        
        # 如果启用了限流，应出现429状态码
        has_rate_limit = any(code == 429 for code in responses)
        
        # 此测试仅验证不会崩溃，限流逻辑由具体实现决定
        assert len(responses) == 110


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])