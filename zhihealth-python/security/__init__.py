# ZhiHealth 安全模块
# 提供：JWT认证、RBAC权限、API限流、数据加密

from .jwt_utils import (
    JWTManager,
    get_jwt_manager,
    generate_token,
    decode_token,
    require_auth,
    require_role
)

from .rbac import (
    RBACManager,
    Role,
    Permission,
    UserContext,
    get_rbac_manager,
    require_permission
)

from .rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    get_rate_limiter,
    rate_limit
)

from .encryption import (
    EncryptionManager,
    PasswordSecurity,
    DataMasking,
    get_encryption_manager
)

__all__ = [
    # JWT认证
    'JWTManager',
    'get_jwt_manager',
    'generate_token', 
    'decode_token',
    'require_auth',
    'require_role',
    
    # 权限控制
    'RBACManager',
    'Role',
    'Permission',
    'UserContext',
    'get_rbac_manager',
    'require_permission',
    
    # 频率限制
    'InMemoryRateLimiter',
    'RateLimitConfig',
    'get_rate_limiter',
    'rate_limit',
    
    # 数据安全
    'EncryptionManager',
    'PasswordSecurity',
    'DataMasking',
    'get_encryption_manager'
]