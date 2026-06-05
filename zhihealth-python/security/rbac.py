"""
基于角色的访问控制 (Role-Based Access Control, RBAC)
实现细粒度的权限管理
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from loguru import logger


class Permission(Enum):
    """系统权限枚举"""
    # 用户管理
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # 数据访问
    DATA_READ = "data:read"
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    DATA_DELETE = "data:delete"
    
    # 分析功能
    ANALYSIS_BASIC = "analysis:basic"
    ANALYSIS_ADVANCED = "analysis:advanced"
    AI_PREDICT = "ai:predict"
    AI_TRAIN = "ai:train"
    
    # 系统管理
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    ALERT_MANAGE = "alert:manage"
    SCHEDULE_MANAGE = "schedule:manage"


class Role(Enum):
    """角色枚举"""
    ADMIN = "admin"           # 超级管理员
    DOCTOR = "doctor"         # 医生/健康顾问
    RESEARCHER = "researcher" # 数据分析师/研究员
    USER = "user"             # 普通用户
    GUEST = "guest"           # 访客（只读）


# 角色权限映射表
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # 拥有所有权限
        Permission.USER_READ, Permission.USER_CREATE, 
        Permission.USER_UPDATE, Permission.USER_DELETE,
        Permission.DATA_READ, Permission.DATA_EXPORT,
        Permission.DATA_IMPORT, Permission.DATA_DELETE,
        Permission.ANALYSIS_BASIC, Permission.ANALYSIS_ADVANCED,
        Permission.AI_PREDICT, Permission.AI_TRAIN,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_MONITOR,
        Permission.ALERT_MANAGE, Permission.SCHEDULE_MANAGE
    },
    Role.DOCTOR: {
        Permission.USER_READ,
        Permission.DATA_READ, Permission.DATA_EXPORT,
        Permission.ANALYSIS_BASIC, Permission.ANALYSIS_ADVANCED,
        Permission.AI_PREDICT,
        Permission.SYSTEM_MONITOR, Permission.ALERT_MANAGE
    },
    Role.RESEARCHER: {
        Permission.USER_READ,
        Permission.DATA_READ, Permission.DATA_EXPORT,
        Permission.ANALYSIS_BASIC, Permission.ANALYSIS_ADVANCED,
        Permission.AI_PREDICT, Permission.AI_TRAIN,
        Permission.SYSTEM_MONITOR
    },
    Role.USER: {
        Permission.USER_READ,  # 只能查看自己的信息
        Permission.DATA_READ,
        Permission.ANALYSIS_BASIC,
        Permission.AI_PREDICT
    },
    Role.GUEST: {
        Permission.USER_READ,
        Permission.DATA_READ  # 受限的数据读取
    }
}


@dataclass
class UserContext:
    """用户上下文（存储在请求中）"""
    user_id: int
    username: str
    role: Role
    permissions: Set[Permission] = field(default_factory=set)
    organization_id: Optional[int] = None
    department: Optional[str] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """检查是否拥有指定权限"""
        return permission in self.permissions
    
    def has_any_permission(self, *permissions: Permission) -> bool:
        """检查是否拥有任一权限"""
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, *permissions: Permission) -> bool:
        """检查是否拥有所有权限"""
        return all(p in self.permissions for p in permissions)


class RBACManager:
    """RBAC权限管理器"""
    
    def __init__(self):
        self._role_cache: Dict[int, Role] = {}
        self._custom_permissions: Dict[int, Set[Permission]] = {}
        
    def get_user_role(self, user_id: int) -> Role:
        """
        获取用户角色（优先从缓存，其次从数据库）
        实际应用中应从数据库或LDAP查询
        """
        if user_id in self._role_cache:
            return self._role_cache[user_id]
        
        # 默认角色（实际应从数据库查询）
        default_role = Role.USER
        self._role_cache[user_id] = default_role
        return default_role
    
    def get_user_permissions(self, user_id: int) -> Set[Permission]:
        """获取用户完整权限列表（角色权限 + 自定义权限）"""
        role = self.get_user_role(user_id)
        base_perms = ROLE_PERMISSIONS.get(role, set())
        
        custom_perms = self._custom_permissions.get(user_id, set())
        
        return base_perms | custom_perms
    
    def create_user_context(self, 
                           user_id: int, 
                           username: str,
                           role_name: str = "user") -> UserContext:
        """创建用户上下文对象"""
        try:
            role = Role(role_name.lower())
        except ValueError:
            logger.warning(f"未知角色: {role_name}，使用默认角色")
            role = Role.USER
        
        permissions = self.get_user_permissions(user_id)
        
        return UserContext(
            user_id=user_id,
            username=username,
            role=role,
            permissions=permissions
        )
    
    def assign_role(self, user_id: int, role: Role):
        """为用户分配角色"""
        self._role_cache[user_id] = role
        logger.info(f"用户{user_id}角色已更新为: {role.value}")
    
    def grant_custom_permission(self, user_id: int, permission: Permission):
        """授予用户自定义额外权限"""
        if user_id not in self._custom_permissions:
            self._custom_permissions[user_id] = set()
        self._custom_permissions[user_id].add(permission)
        logger.info(f"已授予用户{user_id}权限: {permission.value}")
    
    def revoke_custom_permission(self, user_id: int, permission: Permission):
        """撤销用户自定义权限"""
        if user_id in self._custom_permissions:
            self._custom_permissions[user_id].discard(permission)
    
    def check_access(self, 
                    user_context: UserContext, 
                    required_permission: Permission) -> bool:
        """检查访问权限"""
        return user_context.has_permission(required_permission)
    
    def check_data_ownership(self, 
                            user_context: UserContext, 
                            resource_owner_id: int) -> bool:
        """
        检查数据所有权（普通用户只能访问自己的数据）
        管理员可以访问所有数据
        """
        if user_context.role == Role.ADMIN:
            return True
        
        return user_context.user_id == resource_owner_id


# 全局RBAC管理器实例
_rbac_manager: Optional[RBACManager] = None

def get_rbac_manager() -> RBACManager:
    """获取全局RBAC管理器实例"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


# Flask装饰器：权限检查
def require_permission(*required_permissions: Permission):
    """
    要求特定权限的装饰器
    用法：
        @require_permission(Permission.DATA_EXPORT, Permission.AI_PREDICT)
        def export_data():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import request, jsonify
            
            ctx = getattr(request, 'user_context', None)
            
            if not ctx:
                return jsonify({
                    'code': 403,
                    'message': '需要认证',
                    'error': 'User context not found'
                }), 403
            
            rbac = get_rbac_manager()
            
            for perm in required_permissions:
                if not rbac.check_access(ctx, perm):
                    return jsonify({
                        'code': 403,
                        'message': '权限不足',
                        'error': f'Missing permission: {perm.value}',
                        'required_permissions': [p.value for p in required_permissions],
                        'current_permissions': [p.value for p in ctx.permissions]
                    }), 403
            
            return f(*args, **kwargs)
        return decorator
    return decorator


# 辅助函数：快速创建权限检查中间件
def setup_flask_middleware(app):
    """为Flask应用设置RBAC中间件"""
    @app.before_request
    def inject_user_context():
        """在每个请求前注入用户上下文"""
        from flask import request, g
        
        current_user = getattr(request, 'current_user', None)
        
        if current_user:
            rbac = get_rbac_manager()
            ctx = rbac.create_user_context(
                user_id=current_user['user_id'],
                username=current_user.get('username', 'unknown'),
                role_name=current_user.get('role', 'user')
            )
            g.user_context = ctx
            request.user_context = ctx