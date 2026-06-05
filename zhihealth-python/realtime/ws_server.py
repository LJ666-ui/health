"""
ZhiHealth 实时通信服务器
基于Flask-SocketIO实现WebSocket长连接
支持实时数据流、即时告警推送、大屏数据刷新
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request, session
from loguru import logger


class ChannelType(Enum):
    """实时频道类型枚举"""
    HEALTH_DATA = "health_data"           # 健康数据实时流
    ALERT_NOTIFICATION = "alert"          # 告警通知
    DASHBOARD_UPDATE = "dashboard"        # 仪表板刷新
    AI_RESULT = "ai_result"              # AI分析结果
    SYSTEM_STATUS = "system_status"       # 系统状态
    USER_ACTIVITY = "user_activity"      # 用户活动追踪


@dataclass 
class WSClient:
    """WebSocket客户端连接信息"""
    sid: str                              # Session ID (SocketIO)
    user_id: Optional[int] = None         # 关联用户ID
    username: str = "anonymous"
    connected_at: datetime = field(default_factory=datetime.now)
    subscribed_channels: Set[str] = field(default_factory=set)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    
    def is_alive(self) -> bool:
        """检查连接是否存活（心跳超时检测）"""
        timeout_seconds = 120  # 2分钟无心跳视为断开
        return (datetime.now() - self.last_heartbeat).seconds < timeout_seconds
    
    def to_dict(self) -> dict:
        return {
            'sid': self.sid[:8],  # 只显示前8位保护隐私
            'user_id': self.user_id,
            'username': self.username,
            'connected_at': self.connected_at.isoformat(),
            'channels': list(self.subscribed_channels),
            'is_online': self.is_alive()
        }


class RealtimeEventBus:
    """
    实时事件总线（发布-订阅模式）
    用于解耦数据生产者和消费者
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: List[Dict] = []
        self._max_history_size: int = 1000
        self._lock = threading.Lock()
        
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件类型"""
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"订阅事件: {event_type} | 当前订阅者数: {len(self._subscribers[event_type])}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
    
    def publish(self, event_type: str, data: Any, source: str = "unknown"):
        """
        发布事件
        
        Args:
            event_type: 事件类型标识符
            data: 事件负载数据
            source: 事件来源（用于调试和审计）
        """
        event = {
            'type': event_type,
            'data': data,
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'event_id': f"EVT-{int(time.time() * 1000)}"
        }
        
        # 记录历史（用于重放或调试）
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)
            
            # 通知所有订阅者
            handlers = self._subscribers.get(event_type, []).copy()
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"事件处理器异常 [{event_type}]: {e}", exc_info=True)
        
        logger.debug(f"事件已发布: {event_type} | 订阅者数: {len(handlers)}")
    
    def get_recent_events(self, event_type: str = None, limit: int = 50) -> List[Dict]:
        """获取最近的事件记录"""
        with self._lock:
            events = self._event_history
            
            if event_type:
                events = [e for e in events if e['type'] == event_type]
                
            return events[-limit:]
    
    def get_subscriber_count(self, event_type: str) -> int:
        """获取某事件的订阅者数量"""
        return len(self._subscribers.get(event_type, []))


class ZhiHealthRealtimeServer:
    """
    ZhiHealth 实时通信服务器核心
    管理所有WebSocket连接、频道、消息路由
    """
    
    def __init__(self, app=None, socketio: SocketIO = None, cors_allowed_origins="*"):
        self.app = app
        self.socketio = socketio or SocketIO(
            app, 
            cors_allowed_origins=cors_allowed_origins,
            async_mode='threading',
            ping_timeout=60,
            ping_interval=25
        )
        
        # 连接管理
        self.clients: Dict[str, WSClient] = {}  # sid -> client
        
        # 事件总线
        self.event_bus = RealtimeEventBus()
        
        # 频道统计
        self.channel_stats: Dict[str, int] = defaultdict(int)
        
        # 消息计数器
        self.messages_sent_total: int = 0
        self.messages_received_total: int = 0
        
        # 注册内置事件处理
        self._register_event_handlers()
        
        logger.info("ZhiHealth Realtime Server 初始化完成")
    
    def _register_event_handlers(self):
        """注册SocketIO事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """新客户端连接"""
            client_sid = request.sid
            
            new_client = WSClient(sid=client_sid)
            self.clients[client_sid] = new_client
            
            logger.info(f"[WS] 新连接 | SID: {client_sid[:8]}... | "
                       f"当前在线: {len(self.clients)}")
            
            emit('connected', {
                'sid': client_sid[:12],
                'server_time': datetime.now().isoformat(),
                'welcome_message': '欢迎连接到 ZhiHealth 实时服务！',
                'available_channels': [ct.value for ct in ChannelType]
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开连接"""
            client_sid = request.sid
            
            if client_sid in self.clients:
                client = self.clients[client_sid]
                
                # 清理频道统计
                for channel in client.subscribed_channels:
                    self.channel_stats[channel] -= 1
                
                del self.clients[client_sid]
                
                logger.info(f"[WS] 断开连接 | User: {client.username} | "
                           f"SID: {client_sid[:8]}... | "
                           f"剩余在线: {len(self.clients)}")
        
        @self.socketio.on('authenticate')
        def handle_auth(data):
            """客户端身份认证"""
            client_sid = request.sid
            
            if not isinstance(data, dict):
                emit('auth_error', {'message': '无效的认证数据格式'})
                return
                
            token = data.get('token')
            user_id = data.get('user_id')
            username = data.get('username', f'user_{user_id}')
            
            # TODO: 实际应调用JWT验证
            if client_sid in self.clients:
                self.clients[client_sid].user_id = user_id
                self.clients[client_sid].username = username
                
                emit('auth_success', {
                    'user_id': user_id,
                    'username': username,
                    'authenticated_at': datetime.now().isoformat()
                })
                
                logger.info(f"[WS] 认证成功 | User: {username}({user_id})")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """订阅频道"""
            client_sid = request.sid
            channel_name = data.get('channel') if isinstance(data, dict) else data
            
            if not channel_name or client_sid not in self.clients:
                emit('error', {'message': '无效的请求'})
                return
            
            client = self.clients[client_sid]
            
            # 验证频道是否存在
            valid_channels = {ct.value for ct in ChannelType}
            if channel_name not in valid_channels and not channel_name.startswith('user_'):
                emit('subscribe_error', {
                    'channel': channel_name,
                    'message': f'未知频道: {channel_name}'
                })
                return
            
            # 加入SocketIO房间（用于定向广播）
            join_room(channel_name)
            
            client.subscribed_channels.add(channel_name)
            self.channel_stats[channel_name] += 1
            
            emit('subscribed', {
                'channel': channel_name,
                'subscribers_count': self.channel_stats[channel_name],
                'message': f'成功订阅频道: {channel_name}'
            })
            
            logger.info(f"[WS] 订阅频道 | User: {client.username} -> {channel_name}")
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """取消订阅频道"""
            client_sid = request.sid
            channel_name = data.get('channel') if isinstance(data, dict) else data
            
            if client_sid in self.clients and channel_name:
                client = self.clients[client_sid]
                
                leave_room(channel_name)
                
                if channel_name in client.subscribed_channels:
                    client.subscribed_channels.discard(channel_name)
                    self.channel_stats[channel_name] -= 1
                
                emit('unsubscribed', {'channel': channel_name})
        
        @self.socketio.on('ping')
        def handle_ping():
            """心跳检测"""
            client_sid = request.sid
            
            if client_sid in self.clients:
                self.clients[client_sid].last_heartbeat = datetime.now()
                
            emit('pong', {
                'timestamp': datetime.now().isoformat(),
                'server_load': len(self.clients)
            })
        
        @self.socketio.on('message')
        def handle_message(data):
            """通用消息处理"""
            self.messages_received_total += 1
            
            # 转发到事件总线
            if isinstance(data, dict):
                event_type = data.get('type', 'generic')
                payload = data.get('payload', data)
                
                self.event_bus.publish(
                    event_type=event_type,
                    data=payload,
                    source=f'ws:{request.sid[:8]}'
                )
    
    # ==================== 广播方法 ====================
    
    def broadcast_to_channel(self, channel: str, event: str, data: Any):
        """
        向指定频道的所有订阅者广播消息
        
        Args:
            channel: 目标频道名称
            event: 事件名称
            data: 事件数据
        """
        self.messages_sent_total += 1
        
        self.socketio.emit(
            event, 
            {
                'channel': channel,
                'data': data,
                'timestamp': datetime.now().isoformat()
            },
            room=channel,
            include_self=True
        )
        
        logger.debug(f"[Broadcast] {channel}/{event} | "
                    f"接收者: ~{self.channel_stats.get(channel, 0)}")
    
    def send_to_user(self, user_id: int, event: str, data: Any):
        """
        向特定用户发送私信
        
        Args:
            user_id: 目标用户ID
            event: 事件名称
            data: 事件数据
        """
        personal_channel = f"user_{user_id}"
        self.broadcast_to_channel(personal_channel, event, data)
    
    def send_system_notification(self, title: str, message: str, level: str = "info"):
        """
        发送系统级通知（所有在线用户）
        
        Args:
            title: 通知标题
            message: 通知内容
            level: info | warning | error | success
        """
        notification = {
            'type': 'system_notification',
            'title': title,
            'body': message,
            'level': level,
            'timestamp': datetime.now().isoformat()
        }
        
        self.broadcast_to_channel(
            ChannelType.SYSTEM_STATUS.value,
            'notification',
            notification
        )
    
    # ==================== 统计与监控 ====================
    
    def get_server_status(self) -> Dict:
        """获取服务器状态信息"""
        online_clients = sum(1 for c in self.clients.values() if c.is_alive())
        
        return {
            'status': 'running',
            'total_connections_today': len(self.clients),
            'online_clients': online_clients,
            'messages_sent': self.messages_sent_total,
            'messages_received': self.messages_received_total,
            'active_channels': {
                ch: count for ch, count in self.channel_stats.items() if count > 0
            },
            'uptime_info': 'N/A',  # 可扩展为记录启动时间
            'version': '2.0.0'
        }
    
    def get_connected_users(self) -> List[Dict]:
        """获取当前在线用户列表"""
        return [
            client.to_dict() 
            for client in self.clients.values() 
            if client.is_alive() and client.user_id is not None
        ]
    
    def cleanup_stale_connections(self):
        """清理断开的连接（定期执行）"""
        stale_sids = [
            sid for sid, client in self.clients.items() 
            if not client.is_alive()
        ]
        
        for sid in stale_sids:
            client = self.clients[sid]
            for ch in client.subscribed_channels:
                self.channel_stats[ch] -= 1
            del self.clients[sid]
            
        if stale_sids:
            logger.info(f"清理了 {len(stale_sids)} 个过期连接")


# 全局实例
_realtime_server: Optional[ZhiHealthRealtimeServer] = None

def get_realtime_server(app=None) -> ZhiHealthRealtimeServer:
    """获取全局实时服务器实例"""
    global _realtime_server
    if _realtime_server is None:
        _realtime_server = ZhiHealthRealtimeServer(app=app)
    elif app and not _realtime_server.app:
        _realtime_server.app = app
        _realtime_server.socketio.init_app(app)
    return _realtime_server