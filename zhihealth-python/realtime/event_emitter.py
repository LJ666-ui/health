"""
实时数据事件发射器
将各业务模块的事件转化为WebSocket实时推送
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from .ws_server import get_realtime_server, ChannelType


class EventPriority(Enum):
    """事件优先级"""
    LOW = 1          # 低优先级（统计日志等）
    NORMAL = 2       # 普通优先级（常规数据更新）
    HIGH = 3         # 高优先级（重要告警）
    CRITICAL = 4     # 紧急优先级（系统故障）


@dataclass
class RealtimeEvent:
    """实时事件定义"""
    event_id: str
    channel: ChannelType
    event_type: str
    payload: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    source: str = "system"
    timestamp: datetime = None
    target_users: Optional[List[int]] = None  # None=广播，[1,2]=指定用户
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class HealthDataEmitter:
    """
    健康数据实时流发射器
    将新采集的健康数据实时推送给订阅者
    """
    
    def __init__(self):
        self.server = get_realtime_server()
        self._buffer: List[Dict] = []
        self._batch_size: int = 10           # 批量发送阈值
        self._flush_interval: float = 2.0    # 批量刷新间隔(秒)
        self._last_flush: float = time.time()
        self._lock = threading.Lock()
        
        # 启动批量刷新线程
        self._start_flush_thread()
    
    def emit_single_record(self, record: Dict):
        """
        发射单条健康记录
        
        Args:
            record: 健康数据字典，包含 user_id, heart_rate, blood_pressure 等
        """
        event = RealtimeEvent(
            event_id=f"HD-{int(time.time()*1000)}",
            channel=ChannelType.HEALTH_DATA,
            event_type="new_record",
            payload={
                'record': record,
                'data_type': record.get('data_type', 'unknown'),
                'collect_time': record.get('collect_time', datetime.now().isoformat()),
                'user_id': record.get('user_id')
            }
        )
        
        # 加入缓冲区等待批量发送
        with self._lock:
            self._buffer.append(event.payload)
            
            if len(self._buffer) >= self._batch_size:
                self._flush_buffer()
    
    def emit_batch_records(self, records: List[Dict]):
        """批量发射健康记录"""
        for record in records:
            self.emit_single_record(record)
    
    def _flush_buffer(self):
        """刷新缓冲区，批量发送"""
        with self._lock:
            if not self._buffer:
                return
            
            batch_data = self._buffer.copy()
            self._buffer.clear()
        
        try:
            self.server.broadcast_to_channel(
                channel=ChannelType.HEALTH_DATA.value,
                event='health_data_batch',
                data={
                    'records': batch_data,
                    'count': len(batch_data),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.debug(f"批量推送健康数据: {len(batch_data)} 条")
            
        except Exception as e:
            logger.error(f"健康数据推送失败: {e}")
    
    def _start_flush_thread(self):
        """启动定时刷新线程"""
        def flush_loop():
            while True:
                time.sleep(self._flush_interval)
                
                current_time = time.time()
                if (current_time - self._last_flush) >= self._flush_interval:
                    self._flush_buffer()
                    self._last_flush = current_time
        
        thread = threading.Thread(target=flush_loop, daemon=True)
        thread.start()


class AlertEventEmitter:
    """
    告警事件发射器
    将告警系统产生的告警实时推送给相关用户和管理员
    """
    
    def __init__(self):
        self.server = get_realtime_server()
    
    def emit_alert(self, alert_info: Dict):
        """
        发射告警事件
        
        Args:
            alert_info: 告警信息字典，包含：
                - alert_id: 告警ID
                - level: 告警级别 (warning/critical/info)
                - title: 告警标题
                - message: 告警内容
                - user_id: 关联用户ID
                - rule_name: 触发规则名
        """
        priority_map = {
            'critical': EventPriority.CRITICAL,
            'warning': EventPriority.HIGH,
            'info': EventPriority.LOW,
            'success': EventPriority.NORMAL
        }
        
        event = RealtimeEvent(
            event_id=f"ALT-{alert_info.get('alert_id', 'N/A')}",
            channel=ChannelType.ALERT_NOTIFICATION,
            event_type="alert_triggered",
            payload={
                **alert_info,
                'triggered_at': datetime.now().isoformat(),
                'acknowledged': False
            },
            priority=priority_map.get(alert_info.get('level', 'info'), EventPriority.NORMAL),
            target_users=[alert_info.get('user_id')] if alert_info.get('user_id') else None
        )
        
        # 推送到全局告警频道（管理员/运维人员）
        self.server.broadcast_to_channel(
            channel=ChannelType.ALERT_NOTIFICATION.value,
            event='new_alert',
            data=event.payload
        )
        
        # 如果有关联用户，同时推送到用户个人频道
        if event.target_users and event.target_users[0]:
            self.server.send_to_user(
                user_id=event.target_users[0],
                event='personal_alert',
                data=event.payload
            )
        
        logger.warning(
            f"[Alert Emitter] {event.payload.get('level').upper()} | "
            f"{event.payload.get('title')} | User: {event.target_users}"
        )
    
    def emit_alert_resolved(self, alert_id: str, resolved_by: str = "system"):
        """发射告警已解决通知"""
        self.server.broadcast_to_channel(
            channel=ChannelType.ALERT_NOTIFICATION.value,
            event='alert_resolved',
            data={
                'alert_id': alert_id,
                'resolved_at': datetime.now().isoformat(),
                'resolved_by': resolved_by,
                'status': 'resolved'
            }
        )


class DashboardDataPusher:
    """
    仪表板实时数据推送器
    定期向大屏/仪表板客户端推送最新统计数据
    """
    
    def __init__(self, push_interval: int = 5):
        """
        Args:
            push_interval: 推送间隔(秒)，默认5秒
        """
        self.server = get_realtime_server()
        self.push_interval = push_interval
        self._running = False
        self._push_thread: Optional[threading.Thread] = None
        
        # 数据获取回调函数（外部注入）
        self._data_fetcher: Optional[Callable] = None
    
    def set_data_fetcher(self, fetcher_func: Callable):
        """
        设置数据获取回调函数
        
        Args:
            fetcher_func: 无参数函数，返回Dict类型的仪表板数据
        """
        self._data_fetcher = fetcher_func
    
    def start_pushing(self):
        """开始定时推送"""
        if self._running:
            return
        
        self._running = True
        self._push_thread = threading.Thread(target=self._push_loop, daemon=True)
        self._push_thread.start()
        
        logger.info(f"[Dashboard Pusher] 已启动 | 间隔: {self.push_interval}s")
    
    def stop_pushing(self):
        """停止推送"""
        self._running = False
        logger.info("[Dashboard Pusher] 已停止")
    
    def _push_loop(self):
        """推送循环"""
        while self._running:
            try:
                dashboard_data = self._fetch_dashboard_data()
                
                if dashboard_data:
                    self.server.broadcast_to_channel(
                        channel=ChannelType.DASHBOARD_UPDATE.value,
                        event='dashboard_refresh',
                        data={
                            'data': dashboard_data,
                            'push_timestamp': datetime.now().isoformat(),
                            'interval': self.push_interval
                        }
                    )
                    
            except Exception as e:
                logger.error(f"仪表板数据推送异常: {e}", exc_info=True)
            
            time.sleep(self.push_interval)
    
    def _fetch_dashboard_data(self) -> Optional[Dict]:
        """获取仪表板数据"""
        if self._data_fetcher:
            return self._data_fetcher()
        
        # 默认返回模拟数据
        import random
        return {
            'kpi_cards': {
                'total_records': random.randint(10000, 15000),
                'active_users': random.randint(300, 400),
                'alerts_today': random.randint(0, 15),
                'etl_success_rate': round(random.uniform(97.0, 99.9), 2),
                'avg_response_ms': random.randint(80, 200),
                'ai_predictions_today': random.randint(50, 200)
            },
            'trend_chart': {
                'labels': [f'{i}:00' for i in range(24)],
                'heart_rate_avg': [random.randint(70, 80) for _ in range(24)],
                'steps_total': [random.randint(5000, 12000) for _ in range(24)]
            },
            'recent_alerts': [
                {
                    'id': f'ALT-{i}',
                    'level': random.choice(['warning', 'info', 'critical']),
                    'title': f'告警示例-{i}',
                    'time_ago': f'{random.randint(1, 60)}分钟前'
                }
                for i in range(5)
            ]
        }


class AIResultBroadcaster:
    """
    AI分析结果广播器
    当AI模型完成分析后，将结果实时广播给订阅者
    """
    
    def __init__(self):
        self.server = get_realtime_server()
    
    def broadcast_prediction_result(self, 
                                   prediction_id: str,
                                   results: Dict,
                                   model_type: str = "risk_assessment"):
        """
        广播AI预测结果
        
        Args:
            prediction_id: 预测任务ID
            results: 预测结果字典
            model_type: 模型类型标识
        """
        self.server.broadcast_to_channel(
            channel=ChannelType.AI_RESULT.value,
            event='prediction_complete',
            data={
                'prediction_id': prediction_id,
                'model_type': model_type,
                'results': results,
                'completed_at': datetime.now().isoformat(),
                'summary': self._generate_summary(results)
            }
        )
        
        logger.info(f"[AI Broadcaster] 预测完成 | ID: {prediction_id} | Type: {model_type}")
    
    def broadcast_anomaly_detected(self, anomaly_record: Dict):
        """广播检测到的新异常"""
        self.server.broadcast_to_channel(
            channel=ChannelType.AI_RESULT.value,
            event='anomaly_found',
            data={
                'anomaly': anomaly_record,
                'detected_at': datetime.now().isoformat(),
                'severity': anomaly_record.get('anomaly_score', 0) * 100
            }
        )
    
    def broadcast_training_progress(self, task_id: str, progress: float, status: str):
        """广播模型训练进度"""
        self.server.broadcast_to_channel(
            channel=ChannelType.AI_RESULT.value,
            event='training_progress',
            data={
                'task_id': task_id,
                'progress_percent': round(progress * 100, 2),
                'status': status,
                'eta_seconds': max(int((1 - progress) * 60), 0)
            }
        )
    
    def _generate_summary(self, results: Dict) -> str:
        """生成结果摘要文本"""
        risk_level = results.get('risk_level', 'unknown')
        confidence = results.get('confidence', 0)
        
        summary_map = {
            'low': f'✅ 健康状况良好 (置信度: {confidence:.1%})',
            'medium': f'⚠️ 存在潜在风险建议关注 (置信度: {confidence:.1%})',
            'high': f'🔴 高风险需立即检查 (置信度: {confidence:.1%})',
            'critical': f'🚨 紧急风险请立即就医 (置信度: {confidence:.1%})'
        }
        
        return summary_map.get(risk_level, f'分析完成 (置信度: {confidence:.1%})')


# 全局实例
_health_emitter: Optional[HealthDataEmitter] = None
_alert_emitter: Optional[AlertEventEmitter] = None
_dashboard_pusher: Optional[DashboardDataPusher] = None
_ai_broadcaster: Optional[AIResultBroadcaster] = None


def get_health_emitter() -> HealthDataEmitter:
    global _health_emitter
    if _health_emitter is None:
        _health_emitter = HealthDataEmitter()
    return _health_emitter


def get_alert_emitter() -> AlertEventEmitter:
    global _alert_emitter
    if _alert_emitter is None:
        _alert_emitter = AlertEventEmitter()
    return _alert_emitter


def get_dashboard_pusher() -> DashboardDataPusher:
    global _dashboard_pusher
    if _dashboard_pusher is None:
        _dashboard_pusher = DashboardDataPusher()
    return _dashboard_pusher


def get_ai_broadcaster() -> AIResultBroadcaster:
    global _ai_broadcaster
    if _ai_broadcaster is None:
        _ai_broadcaster = AIResultBroadcaster()
    return _ai_broadcaster