"""
第三方集成模块
提供统一的第三方服务集成框架
"""
from .base import (
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
from .manager import integration_manager
from .registry import integration_registry, initialize_integrations
from .providers import *

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
    "initialize_integrations"
]


async def setup_integrations():
    """设置集成系统"""
    from app.core.config import settings
    
    # 初始化注册表
    initialize_integrations()
    
    # 如果启用自动初始化
    if settings.INTEGRATIONS_AUTO_INIT:
        # 获取集成配置
        integration_configs = settings.get_integration_configs()
        
        # 转换为IntegrationConfig对象
        configs = {}
        for name, config_dict in integration_configs.items():
            if config_dict.get("enabled", False):
                configs[name] = IntegrationConfig(**config_dict)
        
        # 初始化所有集成
        if configs:
            results = await integration_manager.initialize_all(configs)
            
            success_count = sum(results.values())
            total_count = len(results)
            
            print(f"集成系统初始化完成: {success_count}/{total_count} 个集成成功启动")
            
            # 打印详细结果
            for name, success in results.items():
                status = "✓" if success else "✗"
                print(f"  {status} {name}")
        else:
            print("未找到可用的集成配置")
    else:
        print("集成自动初始化已禁用")


async def cleanup_integrations():
    """清理集成系统"""
    await integration_manager.cleanup_all()
    print("集成系统已清理")