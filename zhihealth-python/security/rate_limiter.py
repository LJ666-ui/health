"""
API访问频率限制 (Rate Limiting)
防止滥用、保护后端服务、实现公平使用策略
"""

import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from functools import wraps
from flask import request, jsonify, g
from loguru import logger


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_minute: int = 100      # 每分钟请求数
    requests_per_hour: int = 1000       # 每小时请求数
    requests_per_day: int = 10000       # 每天请求数
    
    # 特殊端点配置（可覆盖默认值）
    endpoint_limits: Dict[str, Dict] = field(default_factory=lambda: {
        '/api/v1/ai/predict': {'rpm': 20},     # AI预测：每分钟20次
        '/api/v1/data/export': {'rph': 50},    # 数据导出：每小时50次
        '/api/v1/auth/login': {'rpm': 5},      # 登录接口：每分钟5次
        '/api/v1/auth/register': {'rph': 10},  # 注册接口：每小时10次
    })
    
    # 白名单IP（不限流）
    whitelist_ips: set = field(default_factory=set)
    
    # 超限响应
    retry_after_seconds: int = 60


@dataclass 
class ClientRequestRecord:
    """客户端请求记录"""
    client_id: str
    timestamps: list = field(default_factory=list)
    first_request_time: Optional[datetime] = None
    
    def add_request(self):
        """记录一次请求"""
        now = datetime.now()
        self.timestamps.append(now)
        
        if self.first_request_time is None:
            self.first_request_time = now
        
        # 清理过期记录（保留最近1小时的）
        cutoff = now - timedelta(hours=1)
        self.timestamps = [ts for ts in self.timestamps if ts > cutoff]
    
    def count_in_window(self, window_seconds: int) -> int:
        """统计指定时间窗口内的请求次数"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        return sum(1 for ts in self.timestamps if ts > cutoff)


class InMemoryRateLimiter:
    """基于内存的限流器（单实例部署适用）"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._clients: Dict[str, ClientRequestRecord] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 每5分钟清理一次
        self._last_cleanup = datetime.now()
    
    def _get_client_id(self) -> str:
        """
        获取客户端标识符
        优先级：API Key > User ID > IP地址
        """
        # 尝试从请求上下文获取用户ID
        current_user = getattr(request, 'current_user', None)
        if current_user and 'user_id' in current_user:
            return f"user:{current_user['user_id']}"
        
        # 使用IP地址
        forwarded_for = request.headers.get('X-Forwarded-For')
        real_ip = request.headers.get('X-Real-IP')
        
        client_ip = (forwarded_for or real_ip or 
                    request.remote_addr or "unknown")
        
        # 处理多代理情况
        if ',' in str(client_ip):
            client_ip = str(client_ip).split(',')[0].strip()
            
        return f"ip:{client_ip}"
    
    def _get_endpoint_limit(self, endpoint: str) -> Tuple[int, int, int]:
        """
        获取特定端点的限制配置
        Returns: (per_minute, per_hour, per_day)
        """
        default_rpm = self.config.requests_per_minute
        default_rph = self.config.requests_per_hour
        default_rpd = self.config.requests_per_day
        
        if endpoint in self.config.endpoint_limits:
            limits = self.config.endpoint_limits[endpoint]
            rpm = limits.get('rpm', default_rpm)
            rph = limits.get('rph', default_rph)
            rpd = limits.get('rpd', default_rpd)
            return (min(rpm, default_rpm), min(rph, default_rph), min(rpd, default_rpd))
            
        return (default_rpm, default_rph, default_rpd)
    
    def is_allowed(self, endpoint: str = "") -> Tuple[bool, Optional[int]]:
        """
        检查是否允许请求
        
        Returns:
            (allowed, retry_after_seconds)
        """
        client_id = self._get_client_id()
        
        # 白名单检查
        ip_part = client_id.split(':', 1)[-1] if ':' in client_id else client_id
        if ip_part in self.config.whitelist_ips:
            return True, None
        
        with self._lock:
            # 获取或创建客户端记录
            if client_id not in self._clients:
                self._clients[client_id] = ClientRequestRecord(client_id=client_id)
                
            record = self._clients[client_id]
            
            # 记录本次请求
            record.add_request()
            
            # 获取该端点的限制
            rpm, rph, rpd = self._get_endpoint_limit(endpoint)
            
            # 检查各时间窗口
            minute_count = record.count_in_window(60)
            hour_count = record.count_in_window(3600)
            day_count = record.count_in_window(86400)
            
            violations = []
            if minute_count >= rpm:
                violations.append(('minute', rpm))
            if hour_count >= rph:
                violations.append(('hour', rph))
            if day_count >= rpd:
                violations.append(('day', rpd))
            
            if violations:
                # 返回最严格的等待时间
                worst_window = max(violations, key=lambda x: x[1])
                retry_after = self.config.retry_after_seconds
                
                logger.warning(
                    f"Rate limit exceeded | Client: {client_id} | "
                    f"Endpoint: {endpoint} | "
                    f"Minute: {minute_count}/{rpm} | "
                    f"Hour: {hour_count}/{rph}"
                )
                
                return False, retry_after
            
            # 定期清理过期数据
            if (datetime.now() - self._last_cleanup).seconds > self._cleanup_interval:
                self._cleanup_expired_records()
                self._last_cleanup = datetime.now()
            
            return True, None
    
    def _cleanup_expired_records(self):
        """清理过期的客户端记录"""
        cutoff = datetime.now() - timedelta(hours=24)
        expired_clients = [
            cid for cid, rec in self._clients.items() 
            if rec.first_request_time and rec.first_request_time < cutoff
        ]
        
        for cid in expired_clients:
            del self._clients[cid]
            
        if expired_clients:
            logger.debug(f"已清理 {len(expired_clients)} 个过期客户端记录")
    
    def get_stats(self) -> Dict:
        """获取限流统计信息"""
        active_clients = len(self._clients)
        total_requests_today = sum(
            rec.count_in_window(86400) 
            for rec in self._clients.values()
        )
        
        return {
            'active_clients_tracked': active_clients,
            'total_requests_24h': total_requests_today,
            'config': {
                'requests_per_minute': self.config.requests_per_minute,
                'requests_per_hour': self.config.requests_per_hour,
                'whitelist_size': len(self.config.whitelist_ips),
                'custom_endpoint_rules': len(self.config.endpoint_limits)
            }
        }
    
    def reset_client(self, client_id: str = None):
        """重置某客户端的限流计数"""
        target_id = client_id or self._get_client_id()
        
        with self._lock:
            if target_id in self._clients:
                del self._clients[target_id]
                logger.info(f"已重置客户端 {target_id} 的限流计数")


# 全局限流器实例
_rate_limiter: Optional[InMemoryRateLimiter] = None

def get_rate_limiter() -> InMemoryRateLimiter:
    """获取全局限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        config = RateLimitConfig()
        _rate_limiter = InMemoryRateLimiter(config=config)
    return _rate_limiter


# Flask装饰器：应用限流
def rate_limit(f):
    """Flask路由装饰器：自动应用频率限制"""
    @wraps(f)
    def decorated(*args, **kwargs):
        limiter = get_rate_limiter()
        endpoint = request.endpoint or request.path
        
        allowed, retry_after = limiter.is_allowed(endpoint=endpoint)
        
        if not allowed:
            response = jsonify({
                'code': 429,
                'message': '请求过于频繁，请稍后再试',
                'error': 'Rate limit exceeded',
                'retry_after': retry_after
            })
            
            response.status_code = 429
            response.headers['Retry-After'] = str(retry_after)
            response.headers['X-RateLimit-Limit'] = str(limiter.config.requests_per_minute)
            
            return response
        
        # 在响应头中添加剩余配额信息
        response = f(*args, **kwargs)
        
        if hasattr(response, 'headers'):
            client_id = limiter._get_client_id()
            record = limiter._clients.get(client_id)
            
            if record:
                remaining_min = max(0, limiter.config.requests_per_minute - 
                                 record.count_in_window(60))
                response.headers['X-RateLimit-Remaining'] = str(remaining_min)
        
        return response
    return decorated


# Flask蓝图级别的限流中间件
class RateLimitMiddleware:
    """WSGI中间件形式的限流器（适用于所有请求）"""
    
    def __init__(self, app, limiter=None):
        self.app = app
        self.limiter = limiter or get_rate_limiter()
    
    def __call__(self, environ, start_response):
        from werkzeug.wrappers import Request
        
        req = Request(environ)
        
        # 对API路径进行限流
        if req.path.startswith('/api/'):
            allowed, retry_after = self.limiter.is_allowed(endpoint=req.path)
            
            if not allowed:
                status = '429 Too Many Requests'
                headers = [
                    ('Content-Type', 'application/json'),
                    ('Retry-After', str(retry_after)),
                ]
                body = json.dumps({
                    'code': 429,
                    'message': '请求过于频繁',
                    'error': 'rate_limited'
                }).encode()
                start_response(status, headers, [])
                return [body]
        
        return self.app(environ, start_response)