# ZhiHealth 移动端适配模块
# 提供：移动端专用API、离线同步、响应式数据格式

from .response_format import (
    MobileResponse,
    ResponseCode,
    PaginationMeta,
    OfflineSyncInfo,
    compress_for_mobile
)

from .mobile_endpoints import (
    create_mobile_blueprint,
    get_mobile_blueprint,
    mobile_auth_required,
    rate_limit_for_mobile
)

__all__ = [
    'MobileResponse',
    'ResponseCode',
    'PaginationMeta',
    'OfflineSyncInfo',
    'compress_for_mobile',
    'create_mobile_blueprint',
    'get_mobile_blueprint',
    'mobile_auth_required',
    'rate_limit_for_mobile'
]