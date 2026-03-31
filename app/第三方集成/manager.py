"""
第三方集成管理器
统一管理所有第三方服务集成
"""
from typing import Dict, List, Optional, Type, Any
from datetime import datetime
import logging
import asyncio

from .base import (
    BaseIntegration, IntegrationConfig, IntegrationResponse, 
    IntegrationStatus, IntegrationType, WebhookEvent
)

logger = logging.getLogger(__name__)


class IntegrationManager:
    """集成管理器"""
    
    def __init__(self):
        self._integrations: Dict[str, BaseIntegration] = {}
        self._integration_classes: Dict[str, Type[BaseIntegration]] = {}
        self._webhook_handlers: Dict[str, BaseIntegration] = {}
        self._initialized = False
    
    def register_integration(self, integration_class: Type[BaseIntegration], name: Optional[str] = None):
        """注册集成类"""
        integration_name = name or integration_class.__name__.lower().replace('integration', '')
        self._integration_classes[integration_name] = integration_class
        logger.info(f"已注册集成类: {integration_name}")
    
    async def initialize_integration(self, name: str, config: IntegrationConfig) -> bool:
        """初始化集成"""
        if name not in self._integration_classes:
            logger.error(f"未找到集成类: {name}")
            return False
        
        try:
            integration_class = self._integration_classes[name]
            integration = integration_class(config)
            
            if not integration.is_configured():
                logger.warning(f"集成 {name} 配置不完整，跳过初始化")
                integration.status = IntegrationStatus.DISABLED
                self._integrations[name] = integration
                return False
            
            success = await integration.initialize()
            
            if success:
                integration.status = IntegrationStatus.ACTIVE
                logger.info(f"集成 {name} 初始化成功")
            else:
                integration.status = IntegrationStatus.ERROR
                logger.error(f"集成 {name} 初始化失败")
            
            self._integrations[name] = integration
            
            # 注册Webhook处理器
            if integration.config.webhook_url:
                self._webhook_handlers[integration.config.webhook_url] = integration
            
            return success
            
        except Exception as e:
            logger.error(f"初始化集成 {name} 时发生异常: {e}")
            return False
    
    async def initialize_all(self, configs: Dict[str, IntegrationConfig]) -> Dict[str, bool]:
        """初始化所有集成"""
        results = {}
        
        for name, config in configs.items():
            if config.enabled:
                results[name] = await self.initialize_integration(name, config)
            else:
                logger.info(f"集成 {name} 已禁用，跳过初始化")
                results[name] = False
        
        self._initialized = True
        logger.info(f"集成管理器初始化完成，成功: {sum(results.values())}/{len(results)}")
        
        return results
    
    def get_integration(self, name: str) -> Optional[BaseIntegration]:
        """获取集成实例"""
        return self._integrations.get(name)
    
    def get_integrations_by_type(self, integration_type: IntegrationType) -> List[BaseIntegration]:
        """根据类型获取集成"""
        return [
            integration for integration in self._integrations.values()
            if integration.type == integration_type and integration.status == IntegrationStatus.ACTIVE
        ]
    
    def get_all_integrations(self) -> Dict[str, BaseIntegration]:
        """获取所有集成"""
        return self._integrations.copy()
    
    async def test_integration(self, name: str) -> IntegrationResponse:
        """测试集成连接"""
        integration = self.get_integration(name)
        if not integration:
            return IntegrationResponse(
                success=False,
                error=f"集成 {name} 不存在"
            )
        
        return await integration.test_connection()
    
    async def test_all_integrations(self) -> Dict[str, IntegrationResponse]:
        """测试所有集成连接"""
        results = {}
        
        for name, integration in self._integrations.items():
            if integration.status == IntegrationStatus.ACTIVE:
                results[name] = await integration.test_connection()
            else:
                results[name] = IntegrationResponse(
                    success=False,
                    error=f"集成状态: {integration.status}"
                )
        
        return results
    
    def get_integration_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取集成状态"""
        integration = self.get_integration(name)
        return integration.get_status() if integration else None
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有集成状态"""
        return {
            name: integration.get_status()
            for name, integration in self._integrations.items()
        }
    
    async def handle_webhook(self, webhook_url: str, event: WebhookEvent) -> IntegrationResponse:
        """处理Webhook事件"""
        if webhook_url not in self._webhook_handlers:
            return IntegrationResponse(
                success=False,
                error=f"未找到Webhook处理器: {webhook_url}"
            )
        
        integration = self._webhook_handlers[webhook_url]
        return await integration.handle_webhook(event)
    
    async def reload_integration(self, name: str, config: IntegrationConfig) -> bool:
        """重新加载集成"""
        # 清理旧的集成
        if name in self._integrations:
            old_integration = self._integrations[name]
            try:
                await old_integration.cleanup()
            except Exception as e:
                logger.warning(f"清理旧集成 {name} 时发生异常: {e}")
            
            # 移除Webhook处理器
            webhook_url = old_integration.config.webhook_url
            if webhook_url and webhook_url in self._webhook_handlers:
                del self._webhook_handlers[webhook_url]
        
        # 初始化新的集成
        return await self.initialize_integration(name, config)
    
    async def disable_integration(self, name: str) -> bool:
        """禁用集成"""
        integration = self.get_integration(name)
        if not integration:
            return False
        
        try:
            await integration.cleanup()
            integration.status = IntegrationStatus.DISABLED
            integration.config.enabled = False
            
            # 移除Webhook处理器
            webhook_url = integration.config.webhook_url
            if webhook_url and webhook_url in self._webhook_handlers:
                del self._webhook_handlers[webhook_url]
            
            logger.info(f"集成 {name} 已禁用")
            return True
            
        except Exception as e:
            logger.error(f"禁用集成 {name} 时发生异常: {e}")
            return False
    
    async def enable_integration(self, name: str) -> bool:
        """启用集成"""
        integration = self.get_integration(name)
        if not integration:
            return False
        
        if not integration.is_configured():
            logger.warning(f"集成 {name} 配置不完整，无法启用")
            return False
        
        try:
            integration.config.enabled = True
            success = await integration.initialize()
            
            if success:
                integration.status = IntegrationStatus.ACTIVE
                
                # 重新注册Webhook处理器
                if integration.config.webhook_url:
                    self._webhook_handlers[integration.config.webhook_url] = integration
                
                logger.info(f"集成 {name} 已启用")
                return True
            else:
                integration.status = IntegrationStatus.ERROR
                logger.error(f"启用集成 {name} 失败")
                return False
                
        except Exception as e:
            logger.error(f"启用集成 {name} 时发生异常: {e}")
            integration.status = IntegrationStatus.ERROR
            return False
    
    async def cleanup_all(self):
        """清理所有集成"""
        for name, integration in self._integrations.items():
            try:
                await integration.cleanup()
                logger.info(f"集成 {name} 已清理")
            except Exception as e:
                logger.warning(f"清理集成 {name} 时发生异常: {e}")
        
        self._integrations.clear()
        self._webhook_handlers.clear()
        self._initialized = False
        logger.info("所有集成已清理")
    
    def get_available_integrations(self) -> List[str]:
        """获取可用的集成类型"""
        return list(self._integration_classes.keys())
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        total_integrations = len(self._integrations)
        active_integrations = sum(
            1 for integration in self._integrations.values()
            if integration.status == IntegrationStatus.ACTIVE
        )
        error_integrations = sum(
            1 for integration in self._integrations.values()
            if integration.status == IntegrationStatus.ERROR
        )
        
        return {
            "initialized": self._initialized,
            "total_integrations": total_integrations,
            "active_integrations": active_integrations,
            "error_integrations": error_integrations,
            "health_score": active_integrations / max(total_integrations, 1) * 100,
            "timestamp": datetime.now().isoformat()
        }


# 全局集成管理器实例
integration_manager = IntegrationManager()