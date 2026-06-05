"""
ZhiHealth RESTful API 服务
提供统一的HTTP接口访问所有数据处理、分析、AI功能
基于Flask框架实现
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import json
import traceback
import pandas as pd
from functools import wraps
from loguru import logger

app = Flask(__name__, static_folder='visualization')
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"], "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})

app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def create_app():
    """创建Flask应用实例（供main.py调用）"""
    # 注册AI路由
    register_ai_routes(app)
    return app


class APIResponse:
    """统一API响应格式"""
    
    @staticmethod
    def success(data=None, message="操作成功", code=200):
        return jsonify({
            "code": code,
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }), code
    
    @staticmethod
    def error(message="操作失败", code=500, details=None):
        response = {
            "code": code,
            "success": False,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            response["details"] = details
        return jsonify(response), code
    
    @staticmethod
    def paginated(data, page, page_size, total):
        return {
            "items": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }


def require_api_key(f):
    """API密钥验证装饰器（可选）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if api_key and app.config.get('API_KEY'):
            if api_key != app.config['API_KEY']:
                return APIResponse.error("无效的API密钥", 401)
                
        return f(*args, **kwargs)
    return decorated_function


# ============== 健康数据接口 ==============

@app.route('/api/v1/health/data', methods=['GET'])
@require_api_key
def get_health_data():
    """获取健康数据列表（支持分页和筛选）"""
    try:
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        
        # 查询参数
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 20)), 100)
        user_id = request.args.get('user_id')
        data_type = request.args.get('data_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not pipeline._connect_mysql():
            return APIResponse.error("数据库连接失败", 503)
            
        df = pipeline.extract_from_mysql(batch_size=page_size * page)
        pipeline.close_connections()
        
        if df.empty:
            return APIResponse.success(APIResponse.paginated([], page, page_size, 0))
            
        # 应用筛选条件
        if user_id:
            df = df[df['user_id'].astype(str) == str(user_id)]
        if data_type:
            df = df[df['data_type'] == data_type]
            
        total = len(df)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_data = df.iloc[start_idx:end_idx].to_dict(orient='records')
        
        return APIResponse.success(
            APIResponse.paginated(paginated_data, page, page_size, total),
            f"获取到 {len(paginated_data)} 条记录"
        )
        
    except Exception as e:
        return APIResponse.error(f"获取数据失败: {str(e)}", 500)


@app.route('/api/v1/health/data/<int:user_id>', methods=['GET'])
@require_api_key
def get_user_health_data(user_id):
    """获取特定用户的健康数据"""
    try:
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        
        if not pipeline._connect_mysql():
            return APIResponse.error("数据库连接失败", 503)
            
        df = pipeline.extract_from_mysql(batch_size=5000)
        pipeline.close_connections()
        
        user_df = df[df['user_id'] == user_id]
        
        if user_df.empty:
            return APIResponse.error("未找到该用户的数据", 404)
            
        data_summary = {
            'user_id': user_id,
            'total_records': len(user_df),
            'date_range': {
                'first_record': str(user_df['timestamp'].min())[:19] if 'timestamp' in user_df.columns else 'N/A',
                'last_record': str(user_df['timestamp'].max())[:19] if 'timestamp' in user_df.columns else 'N/A'
            },
            'data_types': user_df['data_type'].value_counts().to_dict() if 'data_type' in user_df.columns else {},
            'latest_metrics': {}
        }
        
        for metric in ['heart_rate', 'body_temp', 'blood_pressure_systolic', 
                      'blood_pressure_diastolic', 'steps', 'sleep_hours']:
            if metric in user_df.columns:
                latest_val = user_df[metric].dropna().iloc[-1] if not user_df[metric].dropna().empty else None
                avg_val = user_df[metric].mean() if not user_df[metric].empty else None
                data_summary['latest_metrics'][metric] = {
                    'latest': float(latest_val) if latest_val is not None else None,
                    'average': round(float(avg_val), 2) if avg_val is not None else None
                }
                
        recent_data = user_df.tail(10).to_dict(orient='records')
        
        return APIResponse.success({
            'summary': data_summary,
            'recent_records': recent_data
        })
        
    except Exception as e:
        return APIResponse.error(f"查询用户数据失败: {str(e)}", 500)


# ============== 数据分析接口 ==============

@app.route('/api/v1/analysis/comprehensive', methods=['POST'])
@require_api_key
def run_comprehensive_analysis():
    """运行综合健康数据分析"""
    try:
        from analysis.analyzer import HealthDataAnalyzer
        
        data = request.json or {}
        input_file = data.get('input_file')
        user_ids = data.get('user_ids')
        
        analyzer = HealthDataAnalyzer()
        
        if input_file and os.path.exists(input_file):
            df = pd.read_csv(input_file)
        else:
            from etl.etl_pipeline import ETPipeline
            pipeline = ETPipeline()
            if not pipeline._connect_mysql():
                return APIResponse.error("数据库连接失败", 503)
            df = pipeline.extract_from_mysql(batch_size=10000)
            pipeline.close_connections()
            
        if user_ids:
            df = df[df['user_id'].isin(user_ids)]
            
        if df.empty:
            return APIResponse.error("无可用数据进行分析", 400)
            
        report = analyzer.generate_comprehensive_report(df)
        
        return APIResponse.success(report, "综合分析完成")
        
    except Exception as e:
        return APIResponse.error(f"分析失败: {str(e)}", 500)


@app.route('/api/v1/analysis/<analysis_type>', methods=['POST'])
@require_api_key
def run_specific_analysis(analysis_type):
    """运行专项分析"""
    try:
        from analysis.analyzer import HealthDataAnalyzer
        
        analyzer = HealthDataAnalyzer()
        data = request.json or {}
        
        if data.get('input_file') and os.path.exists(data['input_file']):
            df = pd.read_csv(data['input_file'])
        else:
            return APIResponse.error("请提供有效的输入文件路径", 400)
            
        analysis_methods = {
            'heart_rate': analyzer.analyze_heart_rate,
            'blood_pressure': analyzer.analyze_blood_pressure,
            'sleep': analyzer.analyze_sleep_quality,
            'activity': analyzer.analyze_activity_level
        }
        
        if analysis_type not in analysis_methods:
            return APIResponse.error(
                f"不支持的分析类型: {analysis_type}。可选: {list(analysis_methods.keys())}",
                400
            )
            
        result = analysis_methods[analysis_type](df)
        
        return APIResponse.success(result, f"{analysis_type} 分析完成")
        
    except Exception as e:
        return APIResponse.error(f"{analysis_type} 分析失败: {str(e)}", 500)


# ============== AI/ML 接口 ==============

@app.route('/api/v1/ai/predict', methods=['POST'])
@require_api_key
def ai_predict_risk():
    """AI健康风险预测"""
    try:
        from ai.ml_engine import AIEngine
        
        engine = AIEngine()
        data = request.json or {}
        
        if data.get('input_file') and os.path.exists(data['input_file']):
            df = pd.read_csv(data['input_file'])
        elif data.get('records'):
            df = pd.DataFrame(data['records'])
        else:
            return APIResponse.error("请提供输入数据 (input_file 或 records)", 400)
            
        limit = min(int(data.get('limit', 10)), 50)
        
        engine.risk_predictor.train_risk_model(df)
        predictions = engine.risk_predictor.predict_health_risk(df.head(limit))
        
        summary = {
            'total_predicted': len(predictions),
            'risk_distribution': {},
            'high_risk_count': sum(1 for p in predictions if p['risk_score'] >= 3)
        }
        
        for pred in predictions:
            level = pred['predicted_risk_level']
            summary['risk_distribution'][level] = summary['risk_distribution'].get(level, 0) + 1
            
        return APIResponse.success({
            'summary': summary,
            'predictions': predictions
        }, f"已完成 {len(predictions)} 条记录的风险预测")
        
    except Exception as e:
        return APIResponse.error(f"AI预测失败: {str(e)}", 500)


@app.route('/api/v1/ai/trend', methods=['POST'])
@require_api_key
def ai_trend_prediction():
    """AI趋势预测"""
    try:
        from ai.ml_engine import AIEngine
        
        engine = AIEngine()
        data = request.json or {}
        
        if data.get('input_file') and os.path.exists(data['input_file']):
            df = pd.read_csv(data['input_file'])
        else:
            return APIResponse.error("请提供输入文件", 400)
            
        user_id = data.get('user_id')
        
        if user_id:
            user_df = df[df['user_id'] == int(user_id)]
            if user_df.empty:
                return APIResponse.error(f"未找到用户 {user_id} 的数据", 404)
            result = engine.trend_predictor.predict_future_health(user_df)
        else:
            result = engine.trend_predictor.predict_future_health(df.head(200))
            
        return APIResponse.success(result, "趋势预测完成")
        
    except Exception as e:
        return APIResponse.error(f"趋势预测失败: {str(e)}", 500)


@app.route('/api/v1/ai/segment', methods=['POST'])
@require_api_key
def ai_user_segmentation():
    """AI用户分群"""
    try:
        from ai.ml_engine import AIEngine
        
        engine = AIEngine()
        data = request.json or {}
        
        if data.get('input_file') and os.path.exists(data['input_file']):
            df = pd.read_csv(data['input_file'])
        else:
            return APIResponse.error("请提供输入文件", 400)
            
        n_clusters = min(int(data.get('n_clusters', 5)), 10)
        engine.segmentation_engine.n_clusters = n_clusters
        
        result = engine.segmentation_engine.segment_users(df)
        
        return APIResponse.success(result, f"完成 {n_clusters} 群体分群")
        
    except Exception as e:
        return APIResponse.error(f"用户分群失败: {str(e)}", 500)


@app.route('/api/v1/ai/comprehensive', methods=['POST'])
@require_api_key
def ai_comprehensive_analysis():
    """AI综合分析（整合所有AI功能）"""
    try:
        from ai.ml_engine import AIEngine
        
        engine = AIEngine()
        data = request.json or {}
        
        if data.get('input_file') and os.path.exists(data['input_file']):
            df = pd.read_csv(data['input_file'])
        else:
            return APIResponse.error("请提供输入文件", 400)
            
        result = engine.run_comprehensive_analysis(df.head(min(int(data.get('limit', 5000)), 10000)))
        
        return APIResponse.success(result, "AI综合分析完成")
        
    except Exception as e:
        return APIError(f"AI综合分析失败: {str(e)}", 500)


# ============== 可视化数据接口 ==============

@app.route('/api/v1/dashboard/kpi', methods=['GET'])
def get_dashboard_kpi():
    """获取仪表板KPI指标"""
    try:
        from visualization.data_generator import VisualizationDataGenerator
        
        generator = VisualizationDataGenerator()
        kpi_data = generator.generate_kpi_metrics()
        
        return APIResponse.success(kpi_data)
        
    except Exception as e:
        return APIResponse.error(f"获取KPI数据失败: {str(e)}", 500)


@app.route('/api/v1/dashboard/alerts', methods=['GET'])
def get_dashboard_alerts():
    """获取实时警报数据"""
    try:
        from visualization.data_generator import VisualizationDataGenerator
        
        generator = VisualizationDataGenerator()
        count = min(int(request.args.get('count', 10)), 50)
        alerts = generator.generate_alerts(count)
        
        return APIResponse.success(alerts)
        
    except Exception as e:
        return APIResponse.error(f"获取警报数据失败: {str(e)}", 500)


@app.route('/api/v1/dashboard/chart-data/<chart_type>', methods=['GET'])
def get_chart_data(chart_type):
    """获取图表数据"""
    try:
        from visualization.data_generator import VisualizationDataGenerator
        
        generator = VisualizationDataGenerator()
        
        chart_generators = {
            'heart_rate': lambda: generator.generate_heart_rate_timeseries(),
            'blood_pressure': lambda: generator.generate_blood_pressure_data(),
            'health_distribution': lambda: generator.generate_health_distribution(),
            'activity_heatmap': lambda: generator.generate_activity_heatmap(),
            'sleep_radar': lambda: generator.generate_sleep_quality_radar(),
            'full_dashboard': lambda: generator.generate_full_dashboard_data()
        }
        
        if chart_type not in chart_generators:
            return APIResponse.error(
                f"未知图表类型: {chart_type}。可选: {list(chart_generators.keys())}",
                400
            )
            
        data = chart_generators[chart_type]()
        
        return APIResponse.success(data)
        
    except Exception as e:
        return APIResponse.error(f"获取图表数据失败: {str(e)}", 500)


# ============== ETL 接口 ==============

@app.route('/api/v1/etl/run', methods=['POST'])
@require_api_key
def run_etl_pipeline():
    """触发ETL流程执行"""
    try:
        from etl.etl_pipeline import ETPipeline
        
        data = request.json or {}
        mode = data.get('mode', 'full')
        source_table = data.get('source_table', 'health_record')
        
        pipeline = ETPipeline()
        
        if mode == 'full':
            stats = pipeline.run_full_pipeline(source_table=source_table)
        else:
            return APIResponse.error(f"不支持的ETL模式: {mode}", 400)
            
        pipeline.close_connections()
        
        return APIResponse.success(stats, f"ETL流程 ({mode}) 执行成功")
        
    except Exception as e:
        return APIResponse.error(f"ETL执行失败: {str(e)}", 500)


# ============== 系统状态接口 ==============

@app.route('/api/v1/system/status', methods=['GET'])
def system_status():
    """系统状态检查"""
    status = {
        'service': 'ZhiHealth API',
        'version': '2.0.0',
        'status': 'healthy',
        'uptime_seconds': 0,
        'modules': {
            'etl': {'status': 'available'},
            'analysis': {'status': 'available'},
            'ai_ml': {'status': 'available'},
            'visualization': {'status': 'available'}
        },
        'database_connections': {},
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        from etl.etl_pipeline import ETPipeline
        pipeline = ETPipeline()
        mysql_ok = pipeline._connect_mysql()
        status['database_connections']['mysql'] = 'connected' if mysql_ok else 'failed'
        pipeline.close_connections()
    except:
        status['database_connections']['mysql'] = 'error'
        
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
        r.ping()
        status['database_connections']['redis'] = 'connected'
    except:
        status['database_connections']['redis'] = 'disconnected'
        
    all_healthy = all(
        conn in ['connected', 'disconnected']
        for conn in status['database_connections'].values()
    ) and status['database_connections'].get('mysql') == 'connected'
    
    status['status'] = 'healthy' if all_healthy else 'degraded'
    
    return APIResponse.success(status)


@app.route('/api/v1/system/info', methods=['GET'])
def system_info():
    """系统信息"""
    info = {
        'service_name': 'ZhiHealth 智慧健康大数据平台',
        'version': '2.0.0',
        'description': '基于Spring Cloud + Python大数据处理的智慧健康解决方案',
        'api_endpoints': {
            'health_data': '/api/v1/health/data',
            'user_data': '/api/v1/health/data/{user_id}',
            'analysis': '/api/v1/analysis/{type}',
            'ai_predict': '/api/v1/ai/predict',
            'ai_trend': '/api/v1/ai/trend',
            'ai_segment': '/api/v1/ai/segment',
            'dashboard_kpi': '/api/v1/dashboard/kpi',
            'etl_run': '/api/v1/etl/run'
        },
        'supported_formats': ['json'],
        'documentation': '/docs'
    }
    
    return APIResponse.success(info)


# ============== 静态文件服务 ==============

@app.route('/')
def serve_dashboard():
    """提供可视化大屏页面"""
    return send_from_directory('visualization', 'index.html')


@app.route('/dashboard.js')
def serve_dashboard_js():
    """提供大屏JS文件"""
    return send_from_directory('visualization', 'dashboard.js')


# ============== 错误处理 ==============

@app.errorhandler(404)
def not_found(error):
    return APIResponse.error("资源不存在", 404)

@app.errorhandler(405)
def method_not_allowed(error):
    return APIResponse.error("请求方法不允许", 405)

@app.errorhandler(413)
def entity_too_large(error):
    return APIResponse.error("请求数据过大", 413)

@app.errorhandler(500)
def internal_error(error):
    return APIResponse.error("服务器内部错误", 500)


# ============== NLP + Ollama AI 智能服务路由注册 ==============

def register_ai_routes(flask_app):
    """注册NLP和Ollama AI服务路由"""
    try:
        from nlp.nlp_processor import create_nlp_api
        flask_app = create_nlp_api(flask_app)
        logger.info("[API] NLP自然语言处理路由已注册")
    except Exception as e:
        logger.warning(f"[API] NLP路由注册失败（可能缺少jieba依赖）: {e}")

    try:
        from ai.ollama_service import create_ollama_api
        flask_app = create_ollama_api(flask_app)
        logger.info("[API] Ollama大模型服务路由已注册")
    except Exception as e:
        logger.warning(f"[API] Ollama路由注册失败: {e}")

    return flask_app


# 启动时自动注册AI路由
app = register_ai_routes(app)


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  ZhiHealth RESTful API 服务")
    print("="*70)
    print(f"\n  服务地址: http://localhost:5000")
    print(f"  API文档: http://localhost:5000/api/v1/system/info")
    print(f"  可视化大屏: http://localhost:5000/")
    print(f"  系统状态: http://localhost:5000/api/v1/system/status\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)