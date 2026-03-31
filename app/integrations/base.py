"""
集成基础类模块
"""
from app.第三方集成.base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationResponse,
    IntegrationStatus,
    IntegrationType,
    WebhookEvent,
    PaymentIntegration,
    AIServiceIntegration,
    SMSIntegration,
    NotificationIntegration,
    OCRIntegration,
    VoiceIntegration
)

# 导出所有基础类
__all__ = [
    "BaseIntegration",
    "IntegrationConfig",
    "IntegrationResponse",
    "IntegrationStatus",
    "IntegrationType",
    "WebhookEvent",
    "PaymentIntegration",
    "AIServiceIntegration",
    "SMSIntegration",
    "NotificationIntegration",
    "OCRIntegration",
    "VoiceIntegration"
]