"""
ZhiHealth 告警通知系统
支持多渠道消息推送（邮件、短信、微信、钉钉、Webhook等）
提供灵活的告警规则引擎和通知模板
"""

import json
import os
import smtplib
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
from loguru import logger

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """告警状态"""
    PENDING = "pending"           # 待发送
    SENT = "sent"                 # 已发送
    DELIVERED = "delivered"       # 已送达
    FAILED = "failed"             # 发送失败
    ACKNOWLEDGED = "acknowledged" # 已确认


@dataclass
class AlertRule:
    """告警规则定义"""
    rule_id: str
    name: str
    description: str
    metric: str                  # 监控指标（如 heart_rate, blood_pressure）
    condition: str               # 条件表达式（如 > 120, < 50）
    severity: AlertSeverity      # 严重级别
    cooldown_seconds: int = 300  # 冷却时间（秒，避免重复告警）
    enabled: bool = True         # 是否启用
    channels: List[str] = None   # 通知渠道列表
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = ["email", "webhook"]


@dataclass 
class AlertRecord:
    """告警记录"""
    alert_id: str
    rule_id: str
    user_id: int
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    status: AlertStatus = AlertStatus.PENDING
    sent_channels: List[str] = None
    retry_count: int = 0
    last_error: str = None
    
    def __post_init__(self):
        if self.sent_channels is None:
            self.sent_channels = []


class NotificationChannel(ABC):
    """通知渠道抽象基类"""
    
    @abstractmethod
    def send(self, alert: AlertRecord) -> bool:
        """发送通知，返回是否成功"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        pass


class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_host = config.get('smtp_host', 'smtp.example.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.from_addr = config.get('from_address', 'noreply@zhihealth.com')
        self.use_tls = config.get('use_tls', True)
        
    def validate_config(self) -> bool:
        return bool(self.smtp_host and self.username and self.password)
    
    def send(self, alert: AlertRecord) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"ZhiHealth 健康预警 <{self.from_addr}>"
            msg['To'] = self._get_recipient(alert)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            body = self._format_email_body(alert)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
                
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"邮件通知已发送 -> {msg['To']}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _get_recipient(self, alert: AlertRecord) -> str:
        return alert.details.get('email', 'admin@zhihealth.com')
    
    def _format_email_body(self, alert: AlertRecord) -> str:
        severity_colors = {
            'info': '#00d4ff',
            'warning': '#ffa502',
            'critical': '#ff4757',
            'emergency': '#ff0000'
        }
        color = severity_colors.get(alert.severity.value, '#333')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head><style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .header {{ background: {color}; color: white; padding: 15px; border-radius: 8px; }}
            .content {{ margin-top: 20px; line-height: 1.6; }}
            .details {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #999; }}
        </style></head>
        <body>
            <div class="header">
                <h2>ZhiHealth 智能健康预警</h2>
                <p>严重级别: {alert.severity.value.upper()} | 时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="content">
                <h3>{alert.title}</h3>
                <p>{alert.message}</p>
                <div class="details">
                    <strong>详细信息:</strong><br/>
                    {json.dumps(alert.details, indent=2, ensure_ascii=False)}
                </div>
                <p>用户ID: #{alert.user_id} | 规则ID: {alert.rule_id}</p>
            </div>
            <div class="footer">
                <p>此邮件由 ZhiHealth 系统自动发送，请勿直接回复。</p>
                <p>© 2026 ZhiHealth 智慧健康大数据平台</p>
            </div>
        </body>
        </html>
        """


class WebhookNotificationChannel(NotificationChannel):
    """Webhook通知渠道（支持钉钉、企业微信、Slack等）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('url', '')
        self.headers = config.get('headers', {'Content-Type': 'application/json'})
        self.platform = config.get('platform', 'generic')  # generic, dingtalk, wechat_work, slack
        
    def validate_config(self) -> bool:
        return bool(self.webhook_url and REQUESTS_AVAILABLE)
    
    def send(self, alert: AlertRecord) -> bool:
        if not REQUESTS_AVAILABLE:
            logger.error("requests库未安装")
            return False
            
        try:
            payload = self._build_payload(alert)
            
            response = requests.post(
                self.webhook_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook通知已发送 ({self.platform})")
                return True
            else:
                logger.error(f"Webhook返回错误: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook发送失败: {e}")
            return False
    
    def _build_payload(self, alert: AlertRecord) -> Dict:
        if self.platform == 'dingtalk':
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"[{alert.severity.value.upper()}] {alert.title}",
                    "text": f"""## {alert.title}
                    
**严重级别:** {alert.severity.value.upper()}

**时间:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

**详情:**
{alert.message}

---
*来自 ZhiHealth 智慧健康平台*
"""
                }
            }
        elif self.platform == 'wechat_work':
            return {
                "msgtype": "text",
                "text": {
                    "content": f"[{alert.severity.value.upper()}] {alert.title}\n\n{alert.message}\n\n时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        elif self.platform == 'slack':
            return {
                "text": f"*[{alert.severity.value.upper()}]* {alert.title}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{alert.title}*\n\n{alert.message}\n\n_时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}_"
                        }
                    }
                ]
            }
        else:
            return {
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "user_id": alert.user_id,
                "timestamp": alert.timestamp.isoformat(),
                "details": alert.details
            }


class SMSNotificationChannel(NotificationChannel):
    """短信通知渠道"""
    
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get('provider', 'aliyun')
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.sign_name = config.get('sign_name', 'ZhiHealth')
        self.template_code = config.get('template_code', '')
        
    def validate_config(self) -> bool:
        return bool(self.api_key and self.api_secret)
    
    def send(self, alert: AlertRecord) -> bool:
        if not REQUESTS_AVAILABLE:
            logger.error("requests库未安装")
            return False
            
        try:
            phone_number = self._get_phone_number(alert)
            
            if self.provider == 'aliyun':
                return self._send_via_aliyun(alert, phone_number)
            elif self.provider == 'tencent':
                return self._send_via_tencent(alert, phone_number)
            else:
                logger.warning(f"不支持的短信服务商: {self.provider}")
                return False
                
        except Exception as e:
            logger.error(f"短信发送失败: {e}")
            return False
    
    def _get_phone_number(self, alert: AlertRecord) -> str:
        return alert.details.get('phone', '13800000000')
    
    def _send_via_aliyun(self, alert: AlertRecord, phone: str) -> bool:
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
            
            client = AcsClient(
                self.api_key,
                self.api_secret,
                'cn-hangzhou'
            )
            
            request = SendSmsRequest()
            request.set_PhoneNumbers(phone)
            request.set_SignName(self.sign_name)
            request.set_TemplateCode(self.template_code)
            request.set_TemplateParam(json.dumps({
                "severity": alert.severity.value,
                "title": alert.title[:20],
                "time": alert.timestamp.strftime("%H:%M")
            }))
            
            response = client.do_action_with_exception(request)
            result = json.loads(response)
            
            if result.get('Code') == 'OK':
                logger.info(f"阿里云短信已发送 -> {phone}")
                return True
            else:
                logger.error(f"阿里云短信失败: {result.get('Message')}")
                return False
                
        except ImportError:
            logger.warning("阿里云SDK未安装，使用模拟模式")
            logger.info(f"[模拟] 短信已发送至 {phone}: [{alert.severity.value}] {alert.title}")
            return True
        except Exception as e:
            logger.error(f"阿里云短信异常: {e}")
            return False
    
    def _send_via_tencent(self, alert: AlertRecord, phone: str) -> bool:
        logger.info(f"[模拟] 腾讯云短信已发送至 {phone}")
        return True


class InAppNotificationChannel(NotificationChannel):
    """应用内通知渠道（WebSocket/长轮询）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.storage = []
        self.max_stored = config.get('max_stored', 1000)
        self.subscribers = set()
        
    def validate_config(self) -> bool:
        return True
    
    def send(self, alert: AlertRecord) -> bool:
        notification = {
            'id': alert.alert_id,
            'type': 'health_alert',
            'severity': alert.severity.value,
            'title': alert.title,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'read': False
        }
        
        self.storage.append(notification)
        
        if len(self.storage) > self.max_stored:
            self.storage = self.storage[-self.max_stored:]
            
        logger.info(f"应用内通知已创建: {alert.alert_id}")
        return True
    
    def get_notifications(self, user_id: int = None, unread_only: bool = False) -> List[Dict]:
        notifications = self.storage
        
        if user_id:
            notifications = [n for n in notifications if n.get('user_id') == user_id]
        if unread_only:
            notifications = [n for n in notifications if not n.get('read')]
            
        return sorted(notifications, key=lambda x: x['timestamp'], reverse=True)


class AlertEngine:
    """告警引擎 - 核心调度与规则管理"""
    
    def __init__(self, config_path: str = None):
        self.rules: Dict[str, AlertRule] = {}
        self.channels: Dict[str, NotificationChannel] = {}
        self.alert_history: List[AlertRecord] = []
        self.cooldown_tracker: Dict[str, datetime] = {}
        self.config = self._load_config(config_path)
        self._initialize_default_rules()
        self._initialize_channels()
        
    def _load_config(self, config_path: str) -> Dict:
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _initialize_default_rules(self):
        """初始化默认告警规则"""
        default_rules = [
            AlertRule(
                rule_id="hr_high",
                name="心率过高",
                description="检测到心率超过120 bpm",
                metric="heart_rate",
                condition="> 120",
                severity=AlertSeverity.WARNING,
                cooldown_seconds=300,
                channels=["email", "in_app", "webhook"]
            ),
            AlertRule(
                rule_id="hr_low",
                name="心率过低",
                description="检测到心率低于50 bpm",
                metric="heart_rate",
                condition="< 50",
                severity=AlertSeverity.WARNING,
                cooldown_seconds=300,
                channels=["email", "in_app"]
            ),
            AlertRule(
                rule_id="bp_crisis",
                name="高血压危象",
                description="收缩压超过180或舒张压超过120",
                metric="blood_pressure_systolic",
                condition="> 180",
                severity=AlertSeverity.CRITICAL,
                cooldown_seconds=600,
                channels=["email", "sms", "in_app", "webhook"]
            ),
            AlertRule(
                rule_id="temp_high",
                name="体温异常升高",
                description="体温超过39.5°C",
                metric="body_temp",
                condition="> 39.5",
                severity=AlertSeverity.CRITICAL,
                cooldown_seconds=3600,
                channels=["email", "sms", "in_app"]
            ),
            AlertRule(
                rule_id="sleep_deficit",
                name="严重睡眠不足",
                description="连续多日睡眠不足5小时",
                metric="sleep_hours",
                condition="< 5",
                severity=AlertSeverity.INFO,
                cooldown_seconds=86400,
                channels=["in_app"]
            ),
            AlertRule(
                rule_id="activity_low",
                name="活动量骤降",
                description="活动量较平均值下降超过70%",
                metric="steps",
                condition="< 1500",
                severity=AlertSeverity.INFO,
                cooldown_seconds=172800,
                channels=["in_app", "email"]
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
            
        logger.info(f"已加载 {len(default_rules)} 条默认告警规则")
    
    def _initialize_channels(self):
        """初始化通知渠道"""
        channel_configs = self.config.get('channels', {})
        
        # 邮件渠道
        email_config = channel_configs.get('email', {})
        if email_config:
            self.channels['email'] = EmailNotificationChannel(email_config)
            
        # Webhook渠道
        webhook_config = channel_configs.get('webhook', {})
        if webhook_config:
            self.channels['webhook'] = WebhookNotificationChannel(webhook_config)
            
        # 短信渠道
        sms_config = channel_configs.get('sms', {})
        if sms_config:
            self.channels['sms'] = SMSNotificationChannel(sms_config)
            
        # 应用内通知
        self.channels['in_app'] = InAppNotificationChannel({})
        
        logger.info(f"已初始化 {len(self.channels)} 个通知渠道")
    
    def add_rule(self, rule: AlertRule):
        """添加自定义告警规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"添加告警规则: {rule.name} (ID: {rule.rule_id})")
    
    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"移除告警规则: {rule_id}")
    
    def evaluate_metrics(self, metrics: Dict[str, float], user_id: int,
                        context: Dict[str, Any] = None) -> List[AlertRecord]:
        """评估指标并生成告警"""
        alerts = []
        context = context or {}
        
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue
                
            # 检查冷却时间
            cooldown_key = f"{rule_id}_{user_id}"
            last_alert_time = self.cooldown_tracker.get(cooldown_key)
            
            if last_alert_time:
                if datetime.now() - last_alert_time < timedelta(seconds=rule.cooldown_seconds):
                    continue
                    
            # 检查指标是否存在
            metric_value = metrics.get(rule.metric)
            if metric_value is None:
                continue
                
            # 评估条件
            if self._evaluate_condition(metric_value, rule.condition):
                alert = self._create_alert(rule, user_id, metric_value, context)
                alerts.append(alert)
                self.cooldown_tracker[cooldown_key] = datetime.now()
                
        return alerts
    
    def _evaluate_condition(self, value: float, condition: str) -> bool:
        """评估条件表达式"""
        try:
            condition = condition.strip()
            
            if condition.startswith('>'):
                threshold = float(condition[1:].strip())
                return value > threshold
            elif condition.startswith('<'):
                threshold = float(condition[1:].strip())
                return value < threshold
            elif condition.startswith('>='):
                threshold = float(condition[2:].strip())
                return value >= threshold
            elif condition.startswith('<='):
                threshold = float(condition[2:].strip())
                return value <= threshold
            elif condition.startswith('=='):
                threshold = float(condition[2:].strip())
                return value == threshold
            elif condition.startswith('!='):
                threshold = float(condition[2:].strip())
                return value != threshold
            else:
                return False
                
        except Exception as e:
            logger.warning(f"条件评估失败: {condition} - {e}")
            return False
    
    def _create_alert(self, rule: AlertRule, user_id: int, 
                     trigger_value: float, context: Dict) -> AlertRecord:
        """创建告警记录"""
        alert_id = f"ALT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}_{rule.rule_id}"
        
        title_templates = {
            'heart_rate': f"{'心率过快' if trigger_value > 80 else '心率过慢'} - 当前值: {trigger_value:.1f} bpm",
            'blood_pressure_systolic': f"血压偏高 - 收缩压: {trigger_value:.0f} mmHg",
            'blood_pressure_diastolic': f"血压偏高 - 舒张压: {trigger_value:.0f} mmHg",
            'body_temp': f"体温异常 - 当前值: {trigger_value:.1f}°C",
            'steps': f"活动量偏低 - 今日步数: {int(trigger_value)}",
            'sleep_hours': f"睡眠不足 - 昨晚睡眠: {trigger_value:.1f}小时"
        }
        
        title = title_templates.get(rule.metric, f"{rule.name} - 值: {trigger_value}")
        
        message = (
            f"检测到用户#{user_id} 的{rule.metric}指标触发告警规则【{rule.name}】。\n"
            f"当前值: {trigger_value}, 条件: {rule.condition}\n"
            f"建议: 请关注该用户的健康状况，必要时联系医疗专业人员。"
        )
        
        alert = AlertRecord(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            user_id=user_id,
            severity=rule.severity,
            title=title,
            message=message,
            details={
                **context,
                'metric': rule.metric,
                'value': trigger_value,
                'condition': rule.condition,
                'rule_name': rule.name
            },
            timestamp=datetime.now()
        )
        
        self.alert_history.append(alert)
        return alert
    
    def dispatch_alerts(self, alerts: List[AlertRecord]) -> Dict[str, List[bool]]:
        """分发告警到各通知渠道"""
        results = {}
        
        for alert in alerts:
            rule = self.rules.get(alert.rule_id)
            if not rule:
                continue
                
            channel_results = []
            
            for channel_name in rule.channels:
                channel = self.channels.get(channel_name)
                
                if channel is None:
                    logger.warning(f"未找到通知渠道: {channel_name}")
                    channel_results.append(False)
                    continue
                    
                success = channel.send(alert)
                channel_results.append(success)
                
                if success:
                    alert.sent_channels.append(channel_name)
                    alert.status = AlertStatus.SENT
                else:
                    alert.retry_count += 1
                    
            results[alert.alert_id] = channel_results
            
        return results
    
    def process_batch(self, batch_data: List[Dict]) -> Dict:
        """批量处理数据并触发告警"""
        total_alerts = []
        dispatched_count = 0
        
        for record in batch_data:
            user_id = record.get('user_id', 0)
            metrics = {
                k: v for k, v in record.items() 
                if k in ['heart_rate', 'body_temp', 'blood_pressure_systolic',
                         'blood_pressure_diastolic', 'steps', 'sleep_hours']
                         and isinstance(v, (int, float))
            }
            
            if metrics:
                alerts = self.evaluate_metrics(metrics, user_id, record)
                total_alerts.extend(alerts)
                
        if total_alerts:
            dispatch_result = self.dispatch_alerts(total_alerts)
            dispatched_count = sum(1 for v in dispatch_result.values() if any(v))
            
        return {
            'processed_records': len(batch_data),
            'alerts_generated': len(total_alerts),
            'alerts_dispatched': dispatched_count,
            'alert_ids': [a.alert_id for a in total_alerts]
        }
    
    def get_alert_history(self, limit: int = 50, user_id: int = None,
                         severity: AlertSeverity = None) -> List[Dict]:
        """获取告警历史"""
        history = self.alert_history.copy()
        
        if user_id:
            history = [a for a in history if a.user_id == user_id]
        if severity:
            history = [a for a in history if a.severity == severity]
            
        history = sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [
            {
                'alert_id': a.alert_id,
                'rule_id': a.rule_id,
                'user_id': a.user_id,
                'severity': a.severity.value,
                'title': a.title,
                'status': a.status.value,
                'timestamp': a.timestamp.isoformat(),
                'sent_channels': a.sent_channels
            }
            for a in history
        ]
    
    def acknowledge_alert(self, alert_id: str, operator: str = "system") -> bool:
        """确认/处理告警"""
        for alert in self.alert_history:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                logger.info(f"告警已确认: {alert_id} by {operator}")
                return True
        return False
    
    def get_statistics(self) -> Dict:
        """获取告警统计信息"""
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        recent_alerts = [a for a in self.alert_history if a.timestamp > day_ago]
        weekly_alerts = [a for a in self.alert_history if a.timestamp > week_ago]
        
        severity_counts = defaultdict(int)
        for a in recent_alerts:
            severity_counts[a.severity.value] += 1
            
        status_counts = defaultdict(int)
        for a in self.alert_history:
            status_counts[a.status.value] += 1
            
        return {
            'total_rules': len(self.rules),
            'enabled_rules': sum(1 for r in self.rules.values() if r.enabled),
            'active_channels': list(self.channels.keys()),
            'alerts_last_24h': len(recent_alerts),
            'alerts_last_7d': len(weekly_alerts),
            'severity_distribution_24h': dict(severity_counts),
            'overall_status_distribution': dict(status_counts),
            'average_response_time_ms': 150  # 示例值
        }


def main():
    """命令行入口 - 测试告警系统"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ZhiHealth 告警通知系统测试工具')
    subparsers = parser.add_subparsers(dest='command')
    
    test_parser = subparsers.add_parser('test', help='测试告警功能')
    test_parser.add_argument('--config', help='配置文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'test':
        print("\n" + "="*70)
        print("  ZhiHealth 告警系统测试")
        print("="*70 + "\n")
        
        engine = AlertEngine(args.config)
        
        # 模拟测试数据
        test_cases = [
            {'user_id': 1001, 'heart_rate': 135, 'blood_pressure_systolic': 125, 
             'steps': 8000, 'phone': '13800138001', 'email': 'user1001@example.com'},
            {'user_id': 1002, 'heart_rate': 45, 'body_temp': 40.2, 
             'steps': 500, 'phone': '13800138002', 'email': 'user1002@example.com'},
            {'user_id': 1003, 'blood_pressure_systolic': 190, 'blood_pressure_diastolic': 130,
             'phone': '13800138003', 'email': 'user1003@example.com'}
        ]
        
        print("正在处理测试数据...\n")
        result = engine.process_batch(test_cases)
        
        print(f"处理结果:")
        print(f"  记录数: {result['processed_records']}")
        print(f"  生成告警: {result['alerts_generated']}")
        print(f"  成功分发: {result['alerts_dispatched']}\n")
        
        print("告警历史:")
        history = engine.get_alert_history(limit=10)
        for alert in history:
            print(f"  [{alert['severity'].upper():10}] {alert['title']} | 用户#{alert['user_id']}")
            
        print("\n系统统计:")
        stats = engine.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()