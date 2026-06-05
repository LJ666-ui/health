"""
数据导出 API 接口
提供RESTful端点支持Excel/PDF/CSV多格式导出
"""

import os
from datetime import datetime
from typing import Optional
from flask import Blueprint, request, jsonify, send_file, Response
from functools import wraps
from loguru import logger

from .excel_exporter import ExcelExporter, ExportConfig
from .pdf_generator import PDFReportGenerator, get_pdf_generator


def require_export_permission(f):
    """导出权限检查装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import g
        
        ctx = getattr(g, 'user_context', None)
        
        if not ctx:
            return jsonify({
                'code': 401,
                'message': '需要登录才能导出数据',
                'error': 'Authentication required'
            }), 401
        
        # 检查是否有数据导出权限
        has_permission = hasattr(ctx, 'has_permission') and \
                        ctx.has_permission('data:export')
        
        if not has_permission and getattr(ctx, 'role', None) != 'admin':
            return jsonify({
                'code': 403,
                'message': '您没有数据导出权限',
                'error': 'Permission denied: data:export required'
            }), 403
            
        return f(*args, **kwargs)
    return decorated


def create_export_blueprint():
    """创建数据导出蓝图"""
    bp = Blueprint('export', __name__, url_prefix='/api/v1/export')
    
    excel_exporter = ExcelExporter()
    
    @bp.route('/formats', methods=['GET'])
    def list_formats():
        """
        列出支持的导出格式
        
        Returns:
            200: 格式列表
        """
        formats = [
            {
                'format': 'xlsx',
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'description': 'Excel 2007+ 工作簿（推荐）',
                'features': ['多工作表', '图表', '样式美化', '自动筛选'],
                'max_rows': 1048576,
                'file_extension': '.xlsx'
            },
            {
                'format': 'csv',
                'mime_type': 'text/csv',
                'description': '逗号分隔值（通用格式）',
                'features': ['轻量级', '兼容性好', '适合大数据量'],
                'max_rows': -1,  # 无限制
                'file_extension': '.csv'
            },
            {
                'format': 'pdf',
                'mime_type': 'application/pdf',
                'description': 'PDF文档报告',
                'features': ['打印友好', '固定布局', '专业排版'],
                'max_rows': 10000,
                'file_extension': '.pdf'
            },
            {
                'format': 'json',
                'mime_type': 'application/json',
                'description': 'JSON结构化数据',
                'features': ['程序可读', '嵌套结构', '元数据丰富'],
                'max_rows': -1,
                'file_extension': '.json'
            }
        ]
        
        return jsonify({
            'code': 200,
            'message': '支持的导出格式列表',
            'data': {
                'total_formats': len(formats),
                'formats': formats
            }
        })
    
    @bp.route('/health-data', methods=['POST'])
    @require_export_permission
    def export_health_data():
        """
        导出健康数据
        
        Request Body:
            format: xlsx | csv | pdf | json (默认: xlsx)
            user_id: int (可选，不传则导出所有用户)
            data_type: str (可选，如 heart_rate, blood_pressure 等)
            start_date: str (YYYY-MM-DD)
            end_date: str (YYYY-MM-DD)
            include_abnormal_only: bool (默认: false)
            
        Returns:
            200: 文件下载流
            400: 参数错误
            500: 导出失败
        """
        try:
            params = request.json or {}
            
            export_format = params.get('format', 'xlsx').lower()
            
            # 验证格式
            valid_formats = {'xlsx', 'csv', 'pdf', 'json'}
            if export_format not in valid_formats:
                return jsonify({
                    'code': 400,
                    'message': f'不支持的导出格式: {export_format}',
                    'supported_formats': list(valid_formats),
                    'error': 'Invalid format parameter'
                }), 400
            
            # 获取数据（实际应用中从数据库查询）
            import pandas as pd
            df = self._query_health_data(params)
            
            if df.empty:
                return jsonify({
                    'code': 204,
                    'message': '没有符合条件的数据',
                    'data': None
                }), 204
            
            # 根据格式生成文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"zhihealth_data_{timestamp}"
            
            if export_format == 'xlsx':
                config = ExportConfig(
                    highlight_abnormal=params.get('highlight_abnormal', True)
                )
                output = excel_exporter.export_health_data(df, config=config)
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename += '.xlsx'
                
            elif export_format == 'csv':
                output = BytesIO()
                df.to_csv(output, index=False, encoding='utf-8-sig')
                output.seek(0)
                mimetype = 'text/csv'
                filename += '.csv'
                
            elif export_format == 'pdf':
                pdf_gen = get_pdf_generator()
                
                user_info = {'user_id': params.get('user_id', 0), 'real_name': 'User'}
                output = pdf_gen.generate_health_profile_report(
                    user_info=user_info,
                    health_data=df
                )
                mimetype = 'application/pdf'
                filename += '.pdf'
                
            else:  # json
                import json as json_module
                output = BytesIO()
                json_str = df.to_json(orient='records', force_ascii=False, indent=2)
                output.write(json_str.encode('utf-8'))
                output.seek(0)
                mimetype = 'application/json'
                filename += '.json'
            
            # 记录导出指标
            from monitoring.metrics_collector import get_metrics
            metrics = get_metrics()
            metrics.data_exports_total.labels(format=export_format, status='success').inc()
            
            return send_file(
                output,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            logger.error(f"数据导出失败: {e}", exc_info=True)
            
            from monitoring.metrics_collector import get_metrics
            metrics = get_metrics()
            metrics.data_exports_total.labels(format=export_format, status='error').inc()
            
            return jsonify({
                'code': 500,
                'message': f'导出失败: {str(e)}',
                'error': 'Export failed'
            }), 500
    
    @bp.route('/ai-report', methods=['POST'])
    @require_export_permission
    def export_ai_report():
        """
        导出AI分析报告（Excel/PDF）
        
        Request Body:
            report_id: str (AI分析结果ID)
            format: xlsx | pdf (默认: xlsx)
            include_raw_data: bool (是否包含原始数据)
        """
        params = request.json or {}
        report_id = params.get('report_id')
        export_format = params.get('format', 'xlsx')
        
        if not report_id:
            return jsonify({
                'code': 400,
                'message': '缺少report_id参数',
                'error': 'Missing required parameter: report_id'
            }), 400
        
        # 实际应从数据库或缓存获取AI分析结果
        analysis_results = self._get_ai_analysis_results(report_id)
        
        if not analysis_results:
            return jsonify({
                'code': 404,
                'message': f'未找到ID为 {report_id} 的AI分析报告',
                'error': 'Report not found'
            }), 404
        
        # 获取原始数据（可选）
        raw_df = None
        if params.get('include_raw_data'):
            raw_df = self._query_health_data({'limit': 1000})
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"zhihealth_ai_report_{timestamp}"
        
        try:
            if export_format == 'xlsx':
                output = excel_exporter.export_ai_report(
                    analysis_results=analysis_results,
                    df=raw_df
                )
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename += '.xlsx'
            else:
                pdf_gen = get_pdf_generator()
                user_info = {'user_id': 999, 'real_name': 'User'}
                output = pdf_gen.generate_health_profile_report(
                    user_info=user_info,
                    health_data=raw_df or pd.DataFrame(),
                    ai_analysis=analysis_results
                )
                mimetype = 'application/pdf'
                filename += '.pdf'
            
            return send_file(
                output,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            logger.error(f"AI报告导出失败: {e}")
            return jsonify({
                'code': 500,
                'message': f'报告导出失败: {str(e)}',
                'error': 'Export failed'
            }), 500
    
    @bp.route('/statistics', methods=['GET'])
    @require_export_permission
    def export_statistics_dashboard():
        """
        导出统计仪表板数据
        
        Query Parameters:
            period: daily | weekly | monthly (默认: monthly)
            format: xlsx (默认)
        """
        period = request.args.get('period', 'monthly')
        
        stats_dict = self._generate_statistics(period)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"zhihealth_stats_{period}_{timestamp}.xlsx"
        
        output = excel_exporter.export_statistics_dashboard(stats_dict)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    def _query_health_data(self, params: dict) -> pd.DataFrame:
        """
        查询健康数据（示例实现）
        实际应用中应从MySQL/MongoDB等数据源查询
        """
        import pandas as pd
        import numpy as np
        
        # 返回模拟数据用于演示
        n_records = min(params.get('limit', 100), 10000)
        
        return pd.DataFrame({
            'id': range(1, n_records + 1),
            'record_id': [f'REC-{i:06d}' for i in range(1, n_records + 1)],
            'user_id': np.random.choice([1, 2, 3, 4, 5], n_records),
            'data_type': np.random.choice(['heart_rate', 'blood_pressure', 'steps'], n_records),
            'heart_rate': np.random.normal(75, 12, n_records).round(1),
            'blood_pressure_systolic': np.random.normal(120, 15, n_records).astype(int),
            'body_temp': np.random.normal(36.6, 0.4, n_records).round(1),
            'steps': np.random.randint(1000, 15000, n_records),
            'sleep_hours': np.clip(np.random.normal(7, 1.5, n_records), 3, 10).round(1),
            'collect_time': pd.date_range(start='2026-05-01', periods=n_records, freq='H'),
            'is_abnormal': np.random.choice([0, 0, 0, 1], n_records)  # 约25%异常率
        })
    
    def _get_ai_analysis_results(self, report_id: str) -> Optional[dict]:
        """获取AI分析结果（示例）"""
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_summary': {
                'total_records': 1205,
                'users_count': 45,
                'date_range': '2026-05-01 ~ 2026-06-01'
            },
            'modules': {
                'risk_prediction': {
                    'metrics': {
                        'accuracy': 0.87,
                        'f1_score': 0.85,
                        'risk_distribution': {'low': 30, 'medium': 12, 'high': 3}
                    },
                    'predictions': []
                },
                'anomaly_detection': {
                    'metrics': {
                        'anomaly_count': 28,
                        'anomaly_rate': 0.023
                    }
                },
                'user_segmentation': {
                    'cluster_profiles': {
                        '0': {'archetype': '健康活跃型', 'user_count': 18},
                        '1': {'archetype': '亚健康关注型', 'user_count': 15},
                        '2': {'archetype': '慢病管理型', 'user_count': 7},
                        '3': {'archetype': '运动达人型', 'user_count': 5}
                    }
                }
            }
        }
    
    def _generate_statistics(self, period: str) -> dict:
        """生成统计数据"""
        return {
            'kpis': [
                {'name': '总记录数', 'value': 12580, 'target': 12000},
                {'name': '活跃用户数', 'value': 342, 'target': 300},
                {'name': '异常检出率', 'value': 2.3, 'target': 3.0},
                {'name': 'ETL成功率', 'value': 99.2, 'target': 98.0},
                {'name': 'API平均响应时间(ms)', 'value': 145, 'target': 200},
                {'name': '告警响应时间(s)', 'value': 28, 'target': 60},
            ],
            'trends': {
                'heart_rate': {'direction': 'stable', 'change_rate': 0.5},
                'active_users': {'direction': 'increasing', 'change_rate': 12.3},
                'anomaly_rate': {'direction': 'decreasing', 'change_rate': -15.2}
            },
            'suggestions': [
                '继续保持当前运动习惯，建议每周增加1次有氧运动',
                '关注睡眠质量，尝试保持规律的作息时间',
                '定期监测血压变化，特别是早晨起床后'
            ]
        }


# 全局蓝图实例
_export_blueprint = None

def get_export_blueprint() -> Blueprint:
    """获取导出蓝图实例"""
    global _export_blueprint
    if _export_blueprint is None:
        _export_blueprint = create_export_blueprint()
    return _export_blueprint