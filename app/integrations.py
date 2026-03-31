"""
集成模块
提供第三方服务集成功能
"""
from app.第三方集成 import (
    # 基础类
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
    VoiceIntegration,
    
    # 管理器
    integration_manager,
    integration_registry,
    initialize_integrations,
    
    # 集成函数
    setup_integrations,
    cleanup_integrations
)

# 导出管理器，以便其他模块可以直接导入
manager = integration_manager
registry = integration_registry

__all__ = [
    # 基础类
    "BaseIntegration",
    "IntegrationConfig", 
    "IntegrationResponse",
    "IntegrationStatus",
    "IntegrationType",
    "WebhookEvent",
    
    # 专用基础类
    "PaymentIntegration",
    "AIServiceIntegration", 
    "SMSIntegration",
    "NotificationIntegration",
    "OCRIntegration",
    "VoiceIntegration",
    
    # 管理器
    "integration_manager",
    "integration_registry",
    "manager",
    "registry",
    "initialize_integrations",
    
    # 集成函数
    "setup_integrations",
    "cleanup_integrations"
]