"""
数据加密与安全工具
提供敏感数据保护、字段级加密、安全哈希等功能
"""

import os
import base64
import hashlib
import json
from typing import Any, Dict, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


class EncryptionManager:
    """数据加密管理器"""
    
    # 需要自动加密的敏感字段（配置）
    SENSITIVE_FIELDS = {
        'password',
        'phone', 
        'email',
        'id_card',
        'bank_card',
        'medical_record_number',
        'address'
    }
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化加密管理器
        
        Args:
            master_key: 主密钥（32字节base64编码），如果为None则自动生成
        """
        if master_key:
            self._fernet = Fernet(master_key.encode() if isinstance(master_key, str) else master_key)
        else:
            self._key = Fernet.generate_key()
            self._fernet = Fernet(self._key)
            logger.warning("使用随机生成的加密密钥，请妥善保存！")
    
    @property
    def key(self) -> str:
        """获取当前使用的加密密钥"""
        return self._fernet._signing_key.decode() if hasattr(self._fernet, '_signing_key') else "N/A"
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        
        Returns:
            Base64编码的密文
        """
        if not plaintext:
            return ""
            
        try:
            encrypted = self._fernet.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串
        
        Args:
            ciphertext: Base64编码的密文
            
        Returns:
            原始明文
        """
        if not ciphertext:
            return ""
            
        try:
            raw = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted = self._fernet.decrypt(raw)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise ValueError("解密失败，可能密钥不匹配或数据损坏")
    
    def encrypt_dict(self, data: Dict[str, Any], 
                    fields_to_encrypt: set = None) -> Dict[str, Any]:
        """
        加密字典中的指定字段
        
        Args:
            data: 原始字典
            fields_to_encrypt: 要加密的字段集合（默认使用SENSITIVE_FIELDS）
            
        Returns:
            新字典（包含加密后的字段）
        """
        target_fields = fields_to_encrypt or self.SENSITIVE_FIELDS
        result = data.copy()
        
        for key in target_fields:
            if key in result and result[key] is not None:
                original_value = str(result[key])
                result[key] = self.encrypt(original_value)
                result[f"{key}_encrypted"] = True  # 标记已加密
                
        return result
    
    def decrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密字典中的加密字段
        
        Args:
            data: 包含加密字段的字典
            
        Returns:
            解密后的新字典
        """
        result = data.copy()
        
        for key in list(result.keys()):
            if key.endswith('_encrypted'):
                continue
                
            f"{key}_encrypted" in result and result.pop(f"{key}_encrypted", None)
                
            if key in result and result[key] is not None:
                try:
                    # 尝试解密（如果是加密值则成功）
                    decrypted_value = self.decrypt(str(result[key]))
                    result[key] = decrypted_value
                except (ValueError, Exception):
                    # 如果不是加密值，保持原样
                    pass
                    
        return result
    
    def encrypt_json(self, obj: Any) -> str:
        """加密JSON对象"""
        json_str = json.dumps(obj, ensure_ascii=False, default=str)
        return self.encrypt(json_str)
    
    def decrypt_json(self, ciphertext: str) -> Any:
        """解密JSON对象"""
        plaintext = self.decrypt(ciphertext)
        return json.loads(plaintext)


class PasswordSecurity:
    """密码安全工具类"""
    
    @staticmethod
    def hash_password(password: str, 
                     salt: Optional[bytes] = None,
                     iterations: int = 260000) -> Tuple[str, str]:
        """
        使用PBKDF2-HMAC-SHA256进行密码哈希
        
        Returns:
            (salt_hex, hash_hex)
        """
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        
        password_bytes = password.encode('utf-8')
        hashed = kdf.derive(password_bytes)
        
        return (salt.hex(), hashed.hex())
    
    @staticmethod
    def verify_password(password: str, 
                       stored_salt_hex: str, 
                       stored_hash_hex: str,
                       iterations: int = 260000) -> bool:
        """验证密码"""
        try:
            salt = bytes.fromhex(stored_salt_hex)
            _, new_hash = PasswordSecurity.hash_password(password, salt, iterations)
            
            # 使用恒定时间比较防止时序攻击
            from hmac import compare_digest
            return compare_digest(new_hash, stored_hash_hex)
        except Exception:
            return False
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """生成安全的随机Token"""
        return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8').rstrip('=')
    
    @staticmethod
    def check_password_strength(password: str) -> Dict[str, Any]:
        """
        检查密码强度
        
        Returns:
            {
                'score': 0-4 (0最弱, 4最强),
                'strength': 'very_weak' | 'weak' | 'medium' | 'strong' | 'very_strong',
                'suggestions': [...]
            }
        """
        score = 0
        suggestions = []
        
        # 长度检查
        if len(password) < 6:
            suggestions.append("密码长度至少为6个字符")
        elif len(password) >= 12:
            score += 1
        elif len(password) >= 8:
            score += 0.5
            
        # 复杂度检查
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        complexity_count = sum([has_upper, has_lower, has_digit, has_special])
        
        if complexity_count == 1:
            score += 0.5
            suggestions.append("建议混合使用大小写字母、数字和特殊字符")
        elif complexity_count == 2:
            score += 1
        elif complexity_count == 3:
            score += 1.5
        elif complexity_count == 4:
            score += 2
            
        # 常见弱密码检测
        common_passwords = {'123456', 'password', '12345678', 'qwerty', 'abc123'}
        if password.lower() in common_passwords:
            score = 0
            suggestions.append("此密码过于常见，容易被破解")
            
        strength_map = {
            0: ('very_weak', '非常弱'),
            0.5: ('weak', '弱'),
            1.5: ('medium', '中等'),
            2.5: ('strong', '强'),
            3.5: ('very_strong', '非常强'),
        }
        
        closest_score = min(strength_map.keys(), key=lambda x: abs(x - score))
        level_name, label = strength_map.get(closest_score, ('unknown', '未知'))
        
        return {
            'score': min(score, 4),
            'strength': level_name,
            'strength_label': label,
            'suggestions': suggestions,
            'is_acceptable': score >= 1.5
        }


class DataMasking:
    """数据脱敏工具类"""
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏：138****1234"""
        if len(phone) >= 7:
            return phone[:3] + '****' + phone[-4:]
        return '*' * len(phone)
    
    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏：a***@example.com"""
        if '@' in email:
            local, domain = email.split('@', 1)
            masked_local = local[0] + '***' if len(local) > 1 else '***'
            return f"{masked_local}@{domain}"
        return '***@***.***'
    
    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证脱敏：110***********1234"""
        if len(id_card) >= 10:
            return id_card[:3] + '*' * (len(id_card) - 7) + id_card[-4:]
        return '*' * len(id_card)
    
    @staticmethod
    def mask_bank_card(card_number: str) -> str:
        """银行卡号脱敏：**** **** **** 1234"""
        clean = ''.join(filter(str.isdigit, card_number))
        if len(clean) > 4:
            return '**** **** **** ' + clean[-4:]
        return '****' * 4
    
    @staticmethod 
    def mask_name(name: str) -> str:
        """姓名脱敏：张** 或 李*"""
        if len(name) <= 1:
            return '*'
        elif len(name) == 2:
            return name[0] + '*'
        else:
            return name[0] + '*' * (len(name) - 1)
    
    @staticmethod
    def mask_sensitive_data(data: dict, mask_rules: dict = None) -> dict:
        """
        批量对字典中的敏感数据进行脱敏
        
        Args:
            data: 原始数据
            mask_rules: 自定义脱敏规则 {field_name: mask_function}
                        默认规则：
                            - phone -> mask_phone
                            - email -> mask_email  
                            - id_card -> mask_id_card
                            - bank_card -> mask_bank_card
                            - real_name -> mask_name
        """
        default_rules = {
            'phone': DataMasking.mask_phone,
            'email': DataMasking.mask_email,
            'id_card': DataMasking.mask_id_card,
            'bank_card': DataMasking.mask_bank_card,
            'real_name': DataMasking.mask_name,
            'username': DataMasking.mask_name,
        }
        
        rules = mask_rules or default_rules
        result = data.copy()
        
        for field, mask_func in rules.items():
            if field in result and result[field]:
                result[field] = mask_func(str(result[field]))
                
        return result


# 全局实例
_encryption_manager: Optional[EncryptionManager] = None

def get_encryption_manager(key: Optional[str] = None) -> EncryptionManager:
    """获取全局加密管理器"""
    global _encryption_manager
    if _encryption_manager is None or key:
        _encryption_manager = EncryptionManager(master_key=key)
    return _encryption_manager