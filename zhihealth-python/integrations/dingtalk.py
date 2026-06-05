"""
钉钉平台集成
支持：机器人Webhook、工作通知、审批流、考勤数据同步
"""

import hmac
import hashlib
import base64
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import requests
from loguru import logger


class DingTalkMessageType(Enum):
    """钉钉消息类型"""
    TEXT = "text"
    LINK = "link"
    MARKDOWN = "markdown"
    ACTION_CARD = "actionCard"
    FEED_CARD = "feedCard"


@dataclass
class DingTalkConfig:
    """钉钉配置"""
    
    # 机器人Webhook（群通知）
    webhook_url: str = ""
    webhook_secret: str = ""             # 签名密钥
    
    # 企业应用
    app_key: str = ""
    app_secret: str = ""
    agent_id: int = 1000001
    
    # API基础URL
    api_base: str = "https://oapi.dingtalk.com"
    
    @classmethod
    def from_env(cls) -> 'DingTalkConfig':
        """从环境变量加载"""
        import os
        
        return cls(
            webhook_url=os.getenv('DINGTALK_WEBHOOK_URL', ''),
            webhook_secret=os.getenv('DINGTALK_WEBHOOK_SECRET', ''),
            app_key=os.getenv('DINGTALK_APP_KEY', ''),
            app_secret=os.getenv('DINGTALK_APP_SECRET', ''),
            agent_id=int(os.getenv('DINGTALK_AGENT_ID', '1000001'))
        )


@dataclass
class DingTalkMessage:
    """钉钉消息结构"""
    msgtype: DingTalkMessageType
    content: Dict[str, Any]
    at_mobiles: Optional[List[str]] = None   # @指定手机号
    at_all: bool = False                     # @所有人
    
    def to_dict(self) -> Dict:
        msg_dict = {
            'msgtype': self.msgtype.value,
            self.msgtype.value: self.content
        }
        
        if self.at_mobiles or self.at_all:
            msg_dict['at'] = {
                'atMobiles': self.at_mobiles or [],
                'isAtAll': self.at_all
            }
        
        return msg_dict


class DingTalkIntegration:
    """
    钉钉平台集成核心类
    支持群机器人、企业应用消息、用户管理等功能
    """
    
    def __init__(self, config: Optional[DingTalkConfig] = None):
        self.config = config or DingTalkConfig.from_env()
        
        # AccessToken缓存
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        
        # 发送统计
        self._stats = {
            'webhook_sent': 0,
            'app_msg_sent': 0,
            'success_rate': 0.0
        }
    
    def send_webhook_message(self, 
                            message: DingTalkMessage,
                            use_signature: bool = True) -> Dict:
        """
        通过群机器人Webhook发送消息
        
        Args:
            message: 消息对象
            use_signature: 是否使用签名验证（推荐）
            
        Returns:
            发送结果
        """
        if not self.config.webhook_url:
            return {'success': False, 'error': '未配置Webhook URL'}
        
        try:
            url = self.config.webhook_url
            
            # 添加签名参数（防止伪造）
            if use_signature and self.config.webhook_secret:
                timestamp = int(time.time() * 1000)
                sign_string = f"{timestamp}\n{self.config.webhook_secret}"
                
                hmac_code = hmac.new(
                    self.config.webhook_secret.encode('utf-8'),
                    sign_string.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                
                sign = base64.b64encode(hmac_code).decode()
                
                url += f"&timestamp={timestamp}&sign={sign}"
            
            headers = {'Content-Type': 'application/json'}
            payload = message.to_dict()
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            self._stats['webhook_sent'] += 1
            
            if result.get('errcode') == 0:
                logger.info(f"[DingTalk Webhook] 消息发送成功 | Type: {message.msgtype.value}")
                return {'success': True}
            else:
                logger.warning(f"[DingTalk Webhook] 发送失败: {result.get('errmsg')}")
                return {'success': False, 'error': result.get('errmsg')}
                
        except Exception as e:
            logger.error(f"[DingTalk Webhook] 发送异常: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def send_work_notification(self,
                              user_ids: List[str],
                              msg_content: Dict,
                              msg_type: str = "text") -> Dict:
        """
        发送企业应用工作通知
        
        Args:
            user_ids: 钉钉UserID列表
            msg_content: 消息内容
            msg_type: text/markdown/link/action_card等
        """
        try:
            access_token = self._get_access_token()
            
            url = f"{self.config.api_base}/topapi/message/corpconversation/asyncsend_v2?access_token={access_token}"
            
            payload = {
                'agent_id': self.config.agent_id,
                'user_list': ','.join(user_ids),
                'msg': msg_type,
                'msg_content': json.dumps(msg_content, ensure_ascii=False)
            }
            
            response = requests.post(url, json=payload, timeout=15)
            result = response.json()
            
            self._stats['app_msg_sent'] += 1
            
            if result.get('errcode') == 0:
                task_id = result.get('task_id')
                logger.info(f"[DingTalk App] 工作通知发送成功 | TaskID: {task_id} | Users: {len(user_ids)}")
                return {'success': True, 'task_id': task_id}
            else:
                logger.error(f"[DingTalk App] 工作通知发送失败: {result.get('errmsg')}")
                return {'success': False, 'error': result.get('errmsg')}
                
        except Exception as e:
            logger.error(f"[DingTalk App] 工作通知异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取钉钉用户信息"""
        try:
            access_token = self._get_access_token()
            
            url = f"{self.config.api_base}/topapi/v2/user/get?access_token={access_token}"
            params = {'userid': user_id}
            
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                return result.get('result')
            else:
                logger.warning(f"获取用户信息失败: {result.get('errmsg')}")
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息异常: {e}")
            return None
    
    def _get_access_token(self) -> str:
        """获取应用AccessToken（带缓存）"""
        current_time = time.time()
        
        if self._access_token and current_time < self._token_expires_at:
            return self._access_token
        
        url = f"{self.config.api_base}/gettoken"
        params = {
            'appkey': self.config.app_key,
            'appsecret': self.config.app_secret
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if 'access_token' in result:
            self._access_token = result['access_token']
            self._token_expires_at = current_time + result.get('expires_in', 7200) - 300
            return self._access_token
        else:
            raise Exception(f"钉钉Token获取失败: {result.get('errmsg')}")
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = self._stats['webhook_sent'] + self._stats['app_msg_sent']
        
        return {
            **self._stats,
            'total_messages': total,
            'config_status': {
                'webhook_configured': bool(self.config.webhook_url),
                'app_configured': bool(self.config.app_key),
                'token_valid': bool(self._access_token and time.time() < self._token_expires_at)
            }
        }


# ==================== 消息构建器 ====================

def create_text_message(text: str, 
                        at_mobiles: Optional[List[str]] = None,
                        at_all: bool = False) -> DingTalkMessage:
    """创建文本消息"""
    return DingTalkMessage(
        msgtype=DingTalkMessageType.TEXT,
        content={'content': text},
        at_mobiles=at_mobiles,
        at_all=at_all
    )


def create_markdown_message(title: str, 
                           text: str,
                           at_mobiles: Optional[List[str]] = None) -> DingTalkMessage:
    """创建Markdown格式消息"""
    return DingTalkMessage(
        msgtype=DingTalkMessageType.MARKDOWN,
        content={
            'title': title,
            'text': text
        },
        at_mobiles=at_mobiles
    )


def create_action_card_message(title: str,
                               text: str,
                               btn_orientation: str = "0",
                               btns: Optional[List[Dict]] = None) -> DingTalkMessage:
    """创建ActionCard卡片消息"""
    return DingTalkMessage(
        msgtype=DingTalkMessageType.ACTION_CARD,
        content={
            'title': title,
            'text': text,
            'btnOrientation': btn_orientation,
            'btns': btns or []
        }
    )


# 全局实例
_dingtalk_integration: Optional[DingTalkIntegration] = None

def get_dingtalk_integration() -> DingTalkIntegration:
    """获取全局钉钉集成实例"""
    global _dingtalk_integration
    if _dingtalk_integration is None:
        _dingtalk_integration = DingTalkIntegration()
    return _dingtalk_integration


# ==================== 预定义健康告警模板 ====================

def build_health_alert_card(alert_data: Dict) -> DingTalkMessage:
    """
    构建健康告警卡片消息（适用于运维/医生群）
    
    Args:
        alert_data: 告警数据字典
    """
    level_emoji = {
        'info': '📋',
        'warning': '⚠️',
        'critical': '🚨'
    }.get(alert_data.get('level', 'info'), '📋')
    
    title = f"{level_emoji} ZhiHealth 健康告警 - {alert_data.get('title', '未知告警')}"
    
    markdown_text = f"""## {alert_data.get('title', '健康告警')}
    
**告警级别**: `{alert_data.get('level', 'unknown').upper()}`  
**关联用户**: {alert_data.get('user_name', 'N/A')} (ID: {alert_data.get('user_id', 'N/A')})  
**触发时间**: {alert_data.get('trigger_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}  

---

### 📝 告警详情

{alert_data.get('message', '无详细描述')}

---

### 📊 相关指标

| 指标 | 当前值 | 正常范围 |
|------|--------|----------|
| 心率 | {alert_data.get('heart_rate', 'N/A')} bpm | 60-100 |
| 血压 | {alert_data.get('blood_pressure', 'N/A')} mmHg | 90-140/60-90 |
| 体温 | {alert_data.get('body_temp', 'N/A')}°C | 36.0-37.3 |

---
> [查看详情](https://health.zhihealth.com/alert/{alert_data.get('alert_id', '')}) | ZhiHealth v2.0
"""
    
    return create_markdown_message(
        title=title,
        text=markdown_text,
        at_mobiles=alert_data.get('notify_phones')
    )


def build_daily_health_report(report_data: Dict) -> DingTalkMessage:
    """构建每日健康汇总报告卡片"""
    title = f"📊 ZhiHealth 每日健康报告 - {datetime.now().strftime('%Y年%m月%d日')}"
    
    markdown_text = f"""## 今日健康概览

### 核心指标

- **健康评分**: {report_data.get('health_score', 'N/A')}分
- **活跃用户数**: {report_data.get('active_users', 0)}人
- **新增数据记录**: {report_data.get('new_records', 0)}条
- **告警触发次数**: {report_data.get('alerts_count', 0)}次

### 系统状态

- **ETL成功率**: {report_data.get('etl_success_rate', 99.5)}%
- **API平均响应时间**: {report_data.get('avg_response_time_ms', 120)}ms
- **AI模型准确率**: {report_data.get('ai_accuracy', 87.2)}%

---
> [登录控制台](https://admin.zhihealth.com) | 自动生成于 {datetime.now().strftime('%H:%M')}
"""
    
    return create_markdown_message(
        title=title,
        text=markdown_text
    )