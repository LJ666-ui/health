"""
JWT Token 工具类
提供Token生成、验证、刷新、黑名单管理功能
"""

import jwt
import time
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
from functools import wraps
from loguru import logger


class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self, 
                 secret_key: str = "zhihealth-jwt-secret-key-2026",
                 algorithm: str = "HS256",
                 access_token_expire: int = 3600,        # 1小时
                 refresh_token_expire: int = 604800,     # 7天
                 issuer: str = "zhihealth-api"):
        
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire
        self.refresh_token_expire = refresh_token_expire
        self.issuer = issuer
        
        # 内存中的Token黑名单（生产环境应使用Redis）
        self._token_blacklist: set = set()
        self._refresh_tokens: Dict[str, datetime] = {}
    
    def generate_token_pair(self, 
                           user_id: int, 
                           username: str,
                           role: str = "user",
                           permissions: list = None,
                           extra_claims: dict = None) -> Tuple[str, str, Dict]:
        """
        生成Access Token和Refresh Token对
        
        Returns:
            (access_token, refresh_token, token_info)
        """
        now = datetime.utcnow()
        
        # Access Token载荷
        access_payload = {
            'jti': str(uuid.uuid4()),          # JWT ID (唯一标识)
            'iat': now,                         # 签发时间
            'exp': now + timedelta(seconds=self.access_token_expire),
            'iss': self.issuer,                  # 签发者
            'sub': str(user_id),                # 主题(用户ID)
            'type': 'access',                   # Token类型
            'username': username,
            'role': role,
            'permissions': permissions or [],
            **(extra_claims or {})
        }
        
        # Refresh Token载荷（仅包含基本信息）
        refresh_payload = {
            'jti': str(uuid.uuid4()),
            'iat': now,
            'exp': now + timedelta(seconds=self.refresh_token_expire),
            'iss': self.issuer,
            'sub': str(user_id),
            'type': 'refresh'
        }
        
        # 签发Token
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
        
        # 存储Refresh Token用于后续刷新
        self._refresh_tokens[refresh_payload['jti']] = now + timedelta(seconds=self.refresh_token_expire)
        
        token_info = {
            'token_type': 'Bearer',
            'expires_in': self.access_token_expire,
            'refresh_expires_in': self.refresh_token_expire,
            'user_id': user_id,
            'role': role,
            'issued_at': now.isoformat()
        }
        
        logger.info(f"用户 {username} ({user_id}) 获取了新的Token对")
        
        return access_token, refresh_token, token_info
    
    def verify_access_token(self, token: str) -> Optional[Dict]:
        """
        验证Access Token并返回解码后的payload
        
        Returns:
            成功: dict(payload)
            失败: None
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                issuer=self.issuer,
                options={'require': ['exp', 'sub', 'jti']}
            )
            
            # 验证是否为Access Token
            if payload.get('type') != 'access':
                logger.warning("非Access Token被用于认证")
                return None
            
            # 检查黑名单
            jti = payload.get('jti')
            if jti in self._token_blacklist:
                logger.warning(f"Token已在黑名单中: {jti}")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Access Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的Access Token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, Dict]]:
        """
        使用Refresh Token刷新Access Token
        
        Returns:
            成功: (new_access_token, new_token_info)
            失败: None
        """
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': False}  # 允许过期检查在后面处理
            )
            
            # 验证是否为Refresh Token
            if payload.get('type') != 'refresh':
                logger.error("尝试使用非Refresh Token进行刷新")
                return None
            
            # 检查Refresh Token是否过期
            exp_time = datetime.fromtimestamp(payload['exp'])
            if datetime.utcnow() > exp_time:
                logger.warning("Refresh Token已过期，需重新登录")
                return None
            
            # 验证Refresh Token是否存在（防止重放攻击）
            jti = payload.get('jti')
            if jti not in self._refresh_tokens:
                logger.error("未知的Refresh Token")
                return None
            
            # 生成新的Token对
            user_id = int(payload['sub'])
            username = payload.get('username', f'user_{user_id}')
            role = payload.get('role', 'user')
            
            # 将旧Access Token加入黑名单（如果存在）
            old_access_jti = payload.get('access_jti')
            if old_access_jti:
                self.blacklist_token(old_access_jti)
            
            # 清理旧的Refresh Token
            del self._refresh_tokens[jti]
            
            return self.generate_token_pair(user_id, username, role)
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Refresh Token验证失败: {e}")
            return None
    
    def blacklist_token(self, jti: str):
        """将Token加入黑名单"""
        self._token_blacklist.add(jti)
        logger.info(f"Token已加入黑名单: {jti[:8]}...")
    
    def revoke_user_tokens(self, user_id: int):
        """撤销某用户的所有Token（强制重新登录）"""
        revoked_count = 0
        for jti in list(self._refresh_tokens.keys()):
            if jti.startswith(str(user_id)):
                del self._refresh_tokens[jti]
                revoked_count += 1
                
        logger.info(f"用户{user_id}的{revoked_count}个Refresh Token已被撤销")
    
    def cleanup_expired_entries(self):
        """清理过期的黑名单和Refresh Token条目"""
        now = datetime.utcnow()
        
        # 清理Refresh Token
        expired_rt = [jti for jti, exp in self._refresh_tokens.items() if now > exp]
        for jti in expired_rt:
            del self._refresh_tokens[jti]
        
        # 定期清理黑名单（可选，避免内存泄漏）
        if len(self._token_blacklist) > 10000:
            self._token_blacklist.clear()
            logger.info("已清理Token黑名单")
    
    def get_token_info(self, token: str) -> Optional[Dict]:
        """获取Token信息（不验证签名，仅用于调试）"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return {
                'user_id': payload.get('sub'),
                'username': payload.get('username'),
                'role': payload.get('role'),
                'issued_at': datetime.fromtimestamp(payload.get('iat', 0)).isoformat(),
                'expires_at': datetime.fromtimestamp(payload.get('exp', 0)).isoformat(),
                'is_expired': payload.get('exp', 0) < time.time(),
                'token_type': payload.get('type', 'unknown')
            }
        except Exception:
            return None
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希（使用SHA256+Salt）"""
        salt = uuid.uuid4().hex
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${hashed}"
    
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """验证密码"""
        try:
            salt, hashed = stored_hash.split('$')
            new_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return new_hash == hashed
        except ValueError:
            return False


# 全局JWT管理器实例
_jwt_manager: Optional[JWTManager] = None

def get_jwt_manager() -> JWTManager:
    """获取全局JWT管理器实例"""
    global _jwt_manager
    if _jwt_manager is None:
        from config.config import get_config
        cfg = get_config()
        secret = getattr(cfg, 'jwt_secret', "zhihealth-jwt-secret-key-2026")
        _jwt_manager = JWTManager(secret_key=secret)
    return _jwt_manager


def generate_token(user_id: int, role: str = "user") -> str:
    """快捷方法：生成Access Token"""
    manager = get_jwt_manager()
    token, _, _ = manager.generate_token_pair(
        user_id=user_id,
        username=f"user_{user_id}",
        role=role
    )
    return token


def decode_token(token: str) -> Optional[Dict]:
    """快捷方法：解码并验证Token"""
    manager = get_jwt_manager()
    return manager.verify_access_token(token)


# Flask装饰器
def require_auth(f):
    """Flask路由装饰器：要求认证"""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, jsonify
        
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'code': 401,
                'message': '缺少认证Token',
                'error': 'Authorization header required'
            }), 401
        
        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                raise ValueError("Invalid token type")
                
        except ValueError:
            return jsonify({
                'code': 401,
                'message': '无效的认证头格式',
                'error': 'Expected: Bearer <token>'
            }), 401
        
        manager = get_jwt_manager()
        payload = manager.verify_access_token(token)
        
        if not payload:
            return jsonify({
                'code': 401,
                'message': 'Token无效或已过期',
                'error': 'Invalid or expired token'
            }), 401
        
        # 将用户信息注入请求上下文
        request.current_user = {
            'user_id': int(payload['sub']),
            'username': payload.get('username'),
            'role': payload.get('role', 'user'),
            'permissions': payload.get('permissions', [])
        }
        
        return f(*args, **kwargs)
    
    return decorated


def require_role(*allowed_roles):
    """Flask路由装饰器：要求特定角色"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import request, jsonify
            
            if not hasattr(request, 'current_user'):
                return jsonify({
                    'code': 403,
                    'message': '需要先认证',
                    'error': 'Authentication required'
                }), 403
            
            user_role = request.current_user.get('role', 'user')
            
            if user_role not in allowed_roles and 'admin' not in allowed_roles:
                return jsonify({
                    'code': 403,
                    'message': '权限不足',
                    'error': f'Required roles: {allowed_roles}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator