"""
微信平台集成
支持：公众号模板消息、小程序订阅消息、企业微信应用消息
"""

import hashlib
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import requests
from loguru import logger


class WeChatMessageType(Enum):
    """微信消息类型"""
    TEMPLATE_MSG = "template"           # 公众号模板消息
    SUBSCRIBE_MSG = "subscribe"         # 小程序订阅消息
    CUSTOMER_SERVICE = "customer_service"  # 客服消息
    ENTERPRISE = "enterprise"           # 企业微信应用消息


@dataclass
class WeChatConfig:
    """微信配置（各环境独立）"""
    app_id: str = ""
    app_secret: str = ""
    token: str = ""                     # 消息验证Token
    encoding_aes_key: str = ""          # 消息加密密钥
    
    # 小程序配置
    mini_app_id: str = ""
    mini_app_secret: str = ""
    
    # 企业微信配置
    corp_id: str = ""
    agent_id: int = 1000001
    corp_secret: str = ""
    
    # API基础URL
    api_base: str = "https://api.weixin.qq.com"
    
    @classmethod
    def from_env(cls) -> 'WeChatConfig':
        """从环境变量加载配置"""
        import os
        
        return cls(
            app_id=os.getenv('WECHAT_APP_ID', ''),
            app_secret=os.getenv('WECHAT_APP_SECRET', ''),
            token=os.getenv('WECHAT_TOKEN', ''),
            encoding_aes_key=os.getenv('WECHAT_ENCODING_AES_KEY', ''),
            mini_app_id=os.getenv('WECHAT_MINI_APP_ID', ''),
            mini_app_secret=os.getenv('WECHAT_MINI_APP_SECRET', ''),
            corp_id=os.getenv('WECHAT_CORP_ID', ''),
            agent_id=int(os.getenv('WECHAT_AGENT_ID', '1000001')),
            corp_secret=os.getenv('WECHAT_CORP_SECRET', '')
        )


@dataclass
class WeChatMessage:
    """微信消息结构"""
    touser: str                         # 接收者OpenID / UserID
    template_id: str                    # 模板ID
    page: Optional[str] = None          # 小程序跳转页面
    data: Dict[str, Any] = field(default_factory=dict)
    miniprogram_state: str = "formal"   # developer/trial/formal
    lang: str = "zh_CN"
    
    def to_dict(self) -> Dict:
        msg_dict = {
            'touser': self.touser,
            'template_id': self.template_id,
            'data': self.data
        }
        
        if self.page:
            msg_dict['page'] = self.page
        if self.miniprogram_state != 'formal':
            msg_dict['miniprogram_state'] = self.miniprogram_state
            
        return msg_dict


class WeChatIntegration:
    """
    微信平台集成核心类
    统一管理AccessToken、消息发送、用户管理等功能
    """
    
    def __init__(self, config: Optional[WeChatConfig] = None):
        self.config = config or WeChatConfig.from_env()
        
        # Token缓存（避免频繁请求）
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._jsapi_ticket: Optional[str] = None
        self._ticket_expires_at: float = 0
        
        # 发送统计
        self._send_stats = {
            'total_sent': 0,
            'success_count': 0,
            'fail_count': 0,
            'last_send_time': None
        }
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        获取AccessToken（带自动刷新和缓存）
        
        Args:
            force_refresh: 是否强制刷新
            
        Returns:
            AccessToken字符串
        """
        current_time = time.time()
        
        if not force_refresh and self._access_token and current_time < self._token_expires_at:
            return self._access_token
        
        try:
            url = f"{self.config.api_base}/cgi-bin/token"
            params = {
                'grant_type': 'client_credential',
                'appid': self.config.app_id,
                'secret': self.config.app_secret
            }
            
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            
            if 'access_token' in result:
                self._access_token = result['access_token']
                self._token_expires_at = current_time + result.get('expires_in', 7200) - 300  # 提前5分钟过期
                
                logger.debug(f"微信AccessToken获取成功，有效期至: {datetime.fromtimestamp(self._token_expires_at)}")
                return self._access_token
            else:
                error_msg = result.get('errmsg', 'Unknown error')
                raise Exception(f"获取AccessToken失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"微信AccessToken请求异常: {e}")
            raise
    
    def send_template_message(self, message: WeChatMessage) -> Dict:
        """
        发送公众号模板消息
        
        Args:
            message: 消息对象
            
        Returns:
            发送结果字典
        """
        try:
            access_token = self.get_access_token()
            
            url = f"{self.config.api_base}/cgi-bin/message/template/send?access_token={access_token}"
            payload = message.to_dict()
            
            response = requests.post(url, json=payload, timeout=15)
            result = response.json()
            
            self._update_stats(result)
            
            if result.get('errcode') == 0:
                logger.info(f"[WeChat] 模板消息发送成功 | ToUser: {message.touser[:8]}... | MsgID: {result.get('msgid')}")
                return {'success': True, 'msgid': result.get('msgid'), 'raw': result}
            else:
                logger.warning(f"[WeChat] 模板消息发送失败 | ErrCode: {result.get('errcode')} | ErrMsg: {result.get('errmsg')}")
                return {'success': False, 'error': result.get('errmsg'), 'error_code': result.get('errcode')}
                
        except Exception as e:
            logger.error(f"[WeChat] 模板消息发送异常: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def send_subscribe_message(self, 
                              open_id: str,
                              template_id: str,
                              data: Dict[str, str],
                              page: Optional[str] = None) -> Dict:
        """
        发送小程序订阅消息
        
        Args:
            open_id: 用户OpenID
            template_id: 订阅消息模板ID
            data: 模板数据键值对
            page: 点击后跳转的小程序页面路径
        """
        try:
            access_token = self.get_access_token()
            
            url = f"{self.config.api_base}/cgi-bin/message/subscribe/send?access_token={access_token}"
            
            payload = {
                'touser': open_id,
                'template_id': template_id,
                'page': page or '',
                'data': data
            }
            
            response = requests.post(url, json=payload, timeout=15)
            result = response.json()
            
            self._update_stats(result)
            
            if result.get('errcode') == 0:
                logger.info(f"[WeChat Mini] 订阅消息发送成功 | OpenID: {open_id[:8]}...")
                return {'success': True, 'msgid': result.get('msgid')}
            else:
                logger.warning(f"[WeChat Mini] 订阅消息发送失败: {result.get('errmsg')}")
                return {'success': False, 'error': result.get('errmsg')}
                
        except Exception as e:
            logger.error(f"[WeChat Mini] 订阅消息发送异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_enterprise_message(self,
                               user_ids: List[str],
                               content: Dict,
                               msg_type: str = "text") -> Dict:
        """
        发送企业微信应用消息
        
        Args:
            user_ids: 企业微信UserID列表
            content: 消息内容（根据msg_type不同格式不同）
            msg_type: text/image/markdown/news等
        """
        try:
            access_token = self._get_corp_token()
            
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            payload = {
                'touser': '|'.join(user_ids),
                'msgtype': msg_type,
                'agentid': self.config.agent_id,
                msg_type: content
            }
            
            response = requests.post(url, json=payload, timeout=15)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"[WeChat Enterprise] 应用消息发送成功 | Users: {len(user_ids)}")
                return {'success': True}
            else:
                logger.error(f"[WeChat Enterprise] 发送失败: {result.get('errmsg')}")
                return {'success': False, 'error': result.get('errmsg')}
                
        except Exception as e:
            logger.error(f"[WeChat Enterprise] 发送异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_jsapi_signature(self, url: str) -> Dict:
        """
        生成JS-SDK签名（用于网页授权）
        
        Args:
            url: 当前页面完整URL（不含#后面部分）
            
        Returns:
            签名参数字典
        """
        jsapi_ticket = self._get_jsapi_ticket()
        
        timestamp = int(time.time())
        nonce_str = hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
        
        string = (
            f"jsapi_ticket={jsapi_ticket}&noncestr={nonce_str}&timestamp={timestamp}&url={url}"
        )
        signature = hashlib.sha1(string.encode()).hexdigest()
        
        return {
            'appId': self.config.app_id,
            'timestamp': timestamp,
            'nonceStr': nonce_str,
            'signature': signature
        }
    
    def _get_corp_token(self) -> str:
        """获取企业微信AccessToken"""
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            'corpid': self.config.corp_id,
            'corpsecret': self.config.corp_secret
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if 'access_token' in result:
            return result['access_token']
        else:
            raise Exception(f"企业微信Token获取失败: {result.get('errmsg')}")
    
    def _get_jsapi_ticket(self) -> str:
        """获取JSAPI Ticket（带缓存）"""
        current_time = time.time()
        
        if self._jsapi_ticket and current_time < self._ticket_expires_at:
            return self._jsapi_ticket
        
        access_token = self.get_access_token()
        
        url = f"{self.config.api_base}/cgi-bin/ticket/getticket?access_token={access_token}&type=jsapi"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if 'ticket' in result:
            self._jsapi_ticket = result['ticket']
            self._ticket_expires_at = current_time + result.get('expires_in', 7200) - 300
            return self._jsapi_ticket
        else:
            raise Exception(f"JSAPI Ticket获取失败: {result.get('errmsg')}")
    
    def _update_stats(self, result: Dict):
        """更新发送统计"""
        self._send_stats['total_sent'] += 1
        self._send_stats['last_send_time'] = datetime.now().isoformat()
        
        if result.get('errcode') == 0:
            self._send_stats['success_count'] += 1
        else:
            self._send_stats['fail_count'] += 1
    
    def get_statistics(self) -> Dict:
        """获取发送统计信息"""
        return {
            **self._send_stats,
            'config_status': {
                'app_configured': bool(self.config.app_id),
                'mini_app_configured': bool(self.config.mini_app_id),
                'enterprise_configured': bool(self.config.corp_id),
                'token_valid': bool(self._access_token and time.time() < self._token_expires_at)
            }
        }


# 全局实例
_wechat_integration: Optional[WeChatIntegration] = None

def get_wechat_integration() -> WeChatIntegration:
    """获取全局微信集成实例"""
    global _wechat_integration
    if _wechat_integration is None:
        _wechat_integration = WeChatIntegration()
    return _wechat_integration


# ==================== 预定义消息模板 ====================

def create_health_alert_message(open_id: str,
                                alert_title: str,
                                alert_content: str,
                                alert_time: str,
                                risk_level: str = "warning") -> WeChatMessage:
    """
    创建健康告警模板消息
    
    Args:
        open_id: 用户OpenID
        alert_title: 告警标题
        alert_content: 告警内容详情
        alert_time: 告警时间
        risk_level: 风险等级 (info/warning/critical)
    """
    level_emoji = {'info': 'ℹ️', 'warning': '⚠️', 'critical': '🚨'}.get(risk_level, '📋')
    
    return WeChatMessage(
        touser=open_id,
        template_id="HEALTH_ALERT_TEMPLATE_ID",  # 实际使用时替换为真实ID
        data={
            'first': {'value': f'{level_emoji} 健康提醒', 'color': '#FF6600' if risk_level == 'warning' else '#CC0000'},
            'keyword1': {'value': alert_title},
            'keyword2': {'value': alert_content},
            'keyword3': {'value': alert_time},
            'remark': {'value': '请及时关注您的健康状况，如有不适请就医。'}
        },
        page="pages/alert/detail?id=latest"
    )


def create_daily_report_message(open_id: str,
                                health_score: int,
                                steps: int,
                                sleep_hours: float,
                                heart_rate_avg: int) -> WeChatMessage:
    """
    创建每日健康报告模板消息
    """
    score_color = '#52C41A' if health_score >= 80 else ('#FAAD14' if health_score >= 60 else '#FF4D4F')
    
    return WeChatMessage(
        touser=open_id,
        template_id="DAILY_REPORT_TEMPLATE_ID",
        data={
            'first': {'value': '📊 您的今日健康报告已生成', 'color': '#1890FF'},
            'keyword1': {'value': datetime.now().strftime('%Y年%m月%d日')},
            'keyword2': {'value': f'{health_score}分', 'color': score_color},
            'keyword3': {'value': f'{steps:,}步'},
            'keyword4': {'value': f'{sleep_hours}小时'},
            'keyword5': {'value': f'{heart_rate_avg} bpm'},
            'remark': {'value': '点击查看详细分析报告和改善建议'}
        },
        page="pages/report/daily"
    )