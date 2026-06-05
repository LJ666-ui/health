# ZhiHealth 第三方集成模块
# 提供：微信通知、钉钉集成、HIS医院系统对接

from .wechat import (
    WeChatIntegration,
    WeChatConfig,
    WeChatMessage,
    WeChatMessageType,
    get_wechat_integration,
    create_health_alert_message,
    create_daily_report_message
)

from .dingtalk import (
    DingTalkIntegration,
    DingTalkConfig,
    DingTalkMessage,
    DingTalkMessageType,
    get_dingtalk_integration,
    create_text_message,
    create_markdown_message,
    create_action_card_message,
    build_health_alert_card,
    build_daily_health_report
)

from .his_connector import (
    HL7Parser,
    FHIRClient,
    HISConnectionConfig,
    HISDataSynchronizer,
    PatientRecord,
    HL7MessageType,
    FHIRResourceType,
    get_fhir_client,
    get_his_synchronizer
)

__all__ = [
    'WeChatIntegration',
    'WeChatConfig',
    'WeChatMessage',
    'WeChatMessageType',
    'get_wechat_integration',
    'create_health_alert_message',
    'create_daily_report_message',
    'DingTalkIntegration',
    'DingTalkConfig',
    'DingTalkMessage',
    'DingTalkMessageType',
    'get_dingtalk_integration',
    'create_text_message',
    'create_markdown_message',
    'create_action_card_message',
    'build_health_alert_card',
    'build_daily_health_report',
    'HL7Parser',
    'FHIRClient',
    'HISConnectionConfig',
    'HISDataSynchronizer',
    'PatientRecord',
    'HL7MessageType',
    'FHIRResourceType',
    'get_fhir_client',
    'get_his_synchronizer'
]