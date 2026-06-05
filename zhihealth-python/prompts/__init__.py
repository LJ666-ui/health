"""
ZhiHealth Prompt工程模板库初始化
"""

from .prompt_templates import (
    PromptTemplate,
    PromptTemplateManager,
    TREND_ANALYSIS_PROMPT,
    RISK_ASSESSMENT_PROMPT,
    PERSONALIZED_SUGGESTION_PROMPT,
    CHATBOT_SYSTEM_PROMPT,
    REPORT_GENERATION_PROMPT,
    prompt_manager
)

__all__ = [
    'PromptTemplate',
    'PromptTemplateManager',
    'TREND_ANALYSIS_PROMPT',
    'RISK_ASSESSMENT_PROMPT',
    'PERSONALIZED_SUGGESTION_PROMPT',
    'CHATBOT_SYSTEM_PROMPT',
    'REPORT_GENERATION_PROMPT',
    'prompt_manager'
]
