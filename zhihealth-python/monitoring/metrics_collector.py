"""
Prometheus 指标采集器
定义、收集和暴露自定义业务指标
"""

import time
import threading
from functools import wraps
from typing import Dict, Optional, Callable
from datetime import datetime
from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
from flask import Response, request
from loguru import logger


class ZhiHealthMetrics:
    """ZhiHealth 自定义Prometheus指标集合"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        
        # ============== 计数器 (Counter) - 只增不减 ==============
        
        # ETL处理记录数
        self.etl_records_processed_total = Counter(
            'zhihealth_etl_records_processed_total',
            'ETL处理的健康数据记录总数',
            ['status', 'source_table'],  # 标签维度
            registry=self.registry
        )
        
        # API请求总数
        self.api_requests_total = Counter(
            'zhihealth_api_requests_total',
            'API请求总数',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        # AI预测调用次数
        self.ai_predictions_total = Counter(
            'zhihealth_ai_predictions_total',
            'AI模型预测调用次数',
            ['model_type', 'prediction_type'],
            registry=self.registry
        )
        
        # 告警触发次数
        self.alerts_triggered_total = Counter(
            'zhihealth_alerts_triggered_total',
            '告警触发总次数',
            ['severity', 'rule_id'],
            registry=self.registry
        )
        
        # 数据导出次数
        self.data_exports_total = Counter(
            'zhihealth_data_exports_total',
            '数据导出操作次数',
            ['format', 'status'],
            registry=self.registry
        )
        
        # 用户登录次数（成功/失败）
        self.auth_login_attempts = Counter(
            'zhihealth_auth_login_attempts',
            '用户登录尝试次数',
            ['result'],  # success / failure
            registry=self.registry
        )
        
        # ============== 直方图 (Histogram) - 分布统计 ==============
        
        # API响应时间分布
        self.api_request_duration_seconds = Histogram(
            'zhihealth_api_request_duration_seconds',
            'API请求处理时间(秒)',
            ['method', 'endpoint'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # ETL批处理耗时
        self.etl_batch_duration_seconds = Histogram(
            'zhihealth_etl_batch_duration_seconds',
            'ETL批处理耗时(秒)',
            ['operation'],  # extract / transform / load
            buckets=[1, 5, 15, 30, 60, 120, 300, 600],
            registry=self.registry
        )
        
        # AI模型推理延迟
        self.ai_inference_latency_seconds = Histogram(
            'zhihealth_ai_inference_latency_seconds',
            'AI模型推理延迟(秒)',
            ['model_name'],
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # 数据库查询时间
        self.db_query_duration_seconds = Histogram(
            'zhihealth_db_query_duration_seconds',
            '数据库查询执行时间(秒)',
            ['database', 'operation'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
            registry=self.registry
        )
        
        # ============== 仪表盘 (Gauge) - 可增可减 ==============
        
        # 当前活跃连接数
        self.active_connections = Gauge(
            'zhihealth_active_connections',
            '当前活跃的客户端连接数',
            ['type'],  # api / websocket / scheduler
            registry=self.registry
        )
        
        # 待处理任务队列长度
        self.task_queue_length = Gauge(
            'zhihealth_task_queue_length',
            '待处理的任务队列长度',
            ['queue_name'],
            registry=self.registry
        )
        
        # 系统资源使用情况
        self.system_cpu_usage = Gauge(
            'zhihealth_system_cpu_usage_percent',
            '系统CPU使用率(%)',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'zhihealth_system_memory_usage_bytes',
            '系统内存使用量(字节)',
            registry=self.registry
        )
        
        # 数据库连接池状态
        self.db_pool_active_connections = Gauge(
            'zhihealth_db_pool_active_connections',
            '数据库连接池活跃连接数',
            ['database'],
            registry=self.registry
        )
        
        self.db_pool_idle_connections = Gauge(
            'zhihealth_db_pool_idle_connections',
            '数据库连接池空闲连接数',
            ['database'],
            registry=self.registry
        )
        
        # 缓存命中率
        self.cache_hit_rate = Gauge(
            'zhihealth_cache_hit_rate',
            '缓存命中率(%)',
            ['cache_type'],  # redis / memory
            registry=self.registry
        )
        
        # ============== 信息 (Info) - 静态元数据 ==============
        
        self.app_info = Info(
            'zhihealth_app_info',
            'ZhiHealth应用信息',
            registry=self.registry
        )
        self.app_info.info({
            'version': '2.0.0',
            'name': 'ZhiHealth Big Data Platform',
            'environment': 'production',
            'python_version': '3.10'
        })
    
    # ==================== 辅助方法 ====================
    
    def track_api_request(self, method: str, endpoint: str, 
                         status_code: int, duration: float):
        """记录API请求指标"""
        self.api_requests_total.labels(
            method=method, 
            endpoint=endpoint, 
            status_code=str(status_code)
        ).inc()
        
        self.api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def track_etl_operation(self, operation: str, status: str, 
                           record_count: int, duration: float):
        """记录ETL操作指标"""
        self.etl_records_processed_total.labels(
            status=status,
            source_table='health_record'
        ).inc(record_count)
        
        self.etl_batch_duration_seconds.labels(operation=operation).observe(duration)
    
    def track_ai_prediction(self, model_type: str, pred_type: str, 
                           latency: float):
        """记录AI预测指标"""
        self.ai_predictions_total.labels(
            model_type=model_type,
            prediction_type=pred_type
        ).inc()
        
        self.ai_inference_latency_seconds.labels(model_name=model_type).observe(latency)
    
    def track_alert(self, severity: str, rule_id: str):
        """记录告警指标"""
        self.alerts_triggered_total.labels(
            severity=str(severity),
            rule_id=rule_id
        ).inc()
    
    def update_system_metrics(self):
        """更新系统资源指标"""
        try:
            import psutil
            
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().used
            
            self.system_cpu_usage.set(cpu)
            self.system_memory_usage.set(mem)
            
        except ImportError:
            pass
    
    def get_metrics_response(self) -> Response:
        """生成Prometheus格式的metrics响应"""
        output = generate_latest(self.registry)
        return Response(output, mimetype=CONTENT_TYPE_LATEST)


# 全局实例
_metrics_instance: Optional[ZhiHealthMetrics] = None

def get_metrics() -> ZhiHealthMetrics:
    """获取全局指标实例"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = ZhiHealthMetrics()
    return _metrics_instance


# ==================== Flask装饰器 ====================

def track_performance(f):
    """
    性能追踪装饰器
    自动记录API请求时间和状态码
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        metrics = get_metrics()
        start_time = time.time()
        
        try:
            response = f(*args, **kwargs)
            
            duration = time.time() - start_time
            
            if hasattr(response, 'status_code'):
                status = response.status_code
            else:
                status = 200
                
            metrics.track_api_request(
                method=request.method,
                endpoint=request.endpoint or request.path,
                status_code=status,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            metrics.track_api_request(
                method=request.method,
                endpoint=request.endpoint or request.path,
                status_code=500,
                duration=duration
            )
            raise
            
    return decorated


# 定时更新系统指标的线程
class MetricsUpdater(threading.Thread):
    """后台线程：定期更新系统级指标"""
    
    def __init__(self, interval: int = 10):
        super().__init__(daemon=True)
        self.interval = interval
        self._stop_event = threading.Event()
        
    def run(self):
        metrics = get_metrics()
        
        while not self._stop_event.is_set():
            try:
                metrics.update_system_metrics()
                
                # 更新连接池指标（示例）
                # 实际应用中应从连接池对象获取真实值
                metrics.db_pool_active_connections.labels(database='mysql').set(5)
                metrics.db_pool_idle_connections.labels(database='mysql').set(10)
                
                # 更新缓存命中率（示例）
                metrics.cache_hit_rate.labels(cache_type='redis').set(95.5)
                
            except Exception as e:
                logger.error(f"指标更新失败: {e}")
                
            self._stop_event.wait(timeout=self.interval)
    
    def stop(self):
        self._stop_event.set()


def start_metrics_updater(interval: int = 10):
    """启动后台指标更新器"""
    updater = MetricsUpdater(interval=interval)
    updater.start()
    logger.info(f"Prometheus指标更新器已启动 (间隔: {interval}秒)")
    return updater