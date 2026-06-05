"""
移动端API响应格式标准化
提供统一的移动端友好响应结构，支持分页、离线同步等特性
"""

from typing import Any, Optional, Dict, List, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum


class ResponseCode(Enum):
    """移动端专用响应码"""
    
    # 2xx 成功
    SUCCESS = (200, "操作成功")
    CREATED = (201, "创建成功")
    ACCEPTED = (202, "请求已接受")
    NO_CONTENT = (204, "无内容")
    
    # 4xx 客户端错误
    BAD_REQUEST = (400, "请求参数错误")
    UNAUTHORIZED = (401, "未授权或Token过期")
    FORBIDDEN = (403, "权限不足")
    NOT_FOUND = (404, "资源不存在")
    METHOD_NOT_ALLOWED = (405, "请求方法不允许")
    CONFLICT = (409, "资源冲突")
    TOO_MANY_REQUESTS = (429, "请求过于频繁")
    VALIDATION_ERROR = (422, "数据验证失败")
    OFFLINE_DATA_CONFLICT = (430, "离线数据冲突需解决")
    
    # 5xx 服务端错误
    INTERNAL_ERROR = (500, "服务器内部错误")
    SERVICE_UNAVAILABLE = (503, "服务暂时不可用")
    GATEWAY_TIMEOUT = (504, "网关超时")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


@dataclass
class PaginationMeta:
    """分页元信息（移动端优化）"""
    current_page: int = 1
    page_size: int = 20
    total_items: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False
    
    @classmethod
    def create(cls, page: int, size: int, total: int) -> 'PaginationMeta':
        """根据总数计算分页元数据"""
        from math import ceil
        
        return cls(
            current_page=page,
            page_size=size,
            total_items=total,
            total_pages=ceil(total / size) if total > 0 else 0,
            has_next=(page * size) < total,
            has_prev=page > 1
        )


@dataclass 
class OfflineSyncInfo:
    """离线同步状态信息"""
    last_sync_time: Optional[str] = None
    pending_count: int = 0
    conflict_count: int = 0
    sync_token: Optional[str] = None
    
    @staticmethod
    def generate_sync_token(user_id: int) -> str:
        """生成同步令牌"""
        import hashlib
        raw = f"{user_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]


@dataclass
class MobileResponse:
    """
    移动端统一响应体
    
    设计原则：
      - 结构扁平化，减少嵌套层级
      - 支持离线优先模式
      - 内置版本控制和缓存提示
      - 错误码国际化支持
    """
    code: int
    message: str
    success: bool = True
    data: Optional[Any] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    request_id: Optional[str] = None
    version: str = "2.0"
    
    # 可选扩展字段
    pagination: Optional[PaginationMeta] = None
    offline_info: Optional[OfflineSyncInfo] = None
    cache_hint: Optional[Dict] = None  # 缓存建议
    extra: Optional[Dict] = None       # 扩展数据
    
    @classmethod
    def success_response(cls, 
                        data: Any = None,
                        message: str = "success",
                        **kwargs) -> 'MobileResponse':
        """构建成功响应"""
        return cls(
            code=ResponseCode.SUCCESS.code,
            message=message,
            success=True,
            data=data,
            **kwargs
        )
    
    @classmethod
    def paginated_response(cls,
                          items: List[Any],
                          page: int,
                          size: int,
                          total: int,
                          **kwargs) -> 'MobileResponse':
        """构建分页响应（移动端常用）"""
        return cls(
            code=ResponseCode.SUCCESS.code,
            message="查询成功",
            success=True,
            data=items,
            pagination=PaginationMeta.create(page, size, total),
            **kwargs
        )
    
    @classmethod
    def error_response(cls,
                      error_code: ResponseCode,
                      details: Optional[List[Dict]] = None,
                      **kwargs) -> 'MobileResponse':
        """构建错误响应"""
        response = cls(
            code=error_code.code,
            message=error_code.message,
            success=False,
            **kwargs
        )
        
        if details:
            response.extra = {'validation_errors': details}
        
        return response
    
    @classmethod
    def offline_ready_response(cls,
                              data: Any,
                              sync_info: OfflineSyncInfo,
                              **kwargs) -> 'MobileResponse':
        """构建离线优先响应"""
        return cls(
            code=ResponseCode.SUCCESS.code,
            message="数据已就绪（含离线更新）",
            success=True,
            data=data,
            offline_info=sync_info,
            **kwargs
        )
    
    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        result = {
            'code': self.code,
            'message': self.message,
            'success': self.success,
            'timestamp': self.timestamp,
            'version': self.version
        }
        
        if self.data is not None:
            result['data'] = self.data
        
        if self.request_id:
            result['request_id'] = self.request_id
            
        if self.pagination:
            result['pagination'] = asdict(self.pagination)
            
        if self.offline_info:
            result['offline'] = asdict(self.offline_info)
            
        if self.cache_hint:
            result['cache'] = self.cache_hint
            
        if self.extra:
            result.update(self.extra)
            
        return result


# ==================== 移动端专用工具函数 ====================

def compress_for_mobile(data: Dict, max_depth: int = 3) -> Dict:
    """
    移动端数据压缩
    - 移除空值字段
    - 截断过长字符串
    - 简化嵌套结构
    """
    compressed = {}
    
    for key, value in data.items():
        if value is None or value == "" or value == []:
            continue
            
        if isinstance(value, dict) and max_depth > 0:
            compressed[key] = compress_for_mobile(value, max_depth - 1)
        elif isinstance(value, str) and len(value) > 500:
            compressed[key] = value[:500] + "...(truncated)"
        else:
            compressed[key] = value
            
    return compressed


def generate_mobile_friendly_error(error: Exception, 
                                   user_language: str = "zh") -> Dict:
    """
    生成移动端友好的错误响应
    包含用户可读的错误信息和开发者调试信息
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    user_messages = {
        'zh': {
            'ConnectionError': '网络连接失败，请检查网络设置',
            'TimeoutError': '请求超时，请稍后重试',
            'ValueError': '参数无效',
            'KeyError': '数据缺失',
            'AuthenticationError': '登录已过期，请重新登录',
            'PermissionError': '权限不足',
            'default': f'操作失败：{error_msg[:100]}'
        },
        'en': {
            'ConnectionError': 'Network connection failed, please check settings',
            'TimeoutError': 'Request timeout, please try again later',
            'ValueError': 'Invalid parameter',
            'KeyError': 'Data missing',
            'AuthenticationError': 'Session expired, please login again',
            'PermissionError': 'Permission denied',
            'default': f'Operation failed: {error_msg[:100]}'
        }
    }
    
    lang_map = user_messages.get(user_language, user_messages['en'])
    user_msg = lang_map.get(error_type, lang_map['default'])
    
    return {
        'code': 500,
        'message': user_msg,
        'success': False,
        'debug_info': {
            'error_type': error_type,
            'original_message': error_msg[:200],
            'timestamp': datetime.now().isoformat()
        } if _is_debug_mode() else None
    }


def _is_debug_mode() -> bool:
    """检查是否为调试模式"""
    import os
    return os.environ.get('APP_ENV', 'production') == 'development'