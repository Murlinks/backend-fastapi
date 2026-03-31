"""
第三方集成注册表
自动发现和注册所有集成类
"""
import importlib
import pkgutil
from typing import Dict, Type
import logging

from .base import BaseIntegration
from .manager import integration_manager

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    """集成注册表"""
    
    def __init__(self):
        self._registered_integrations: Dict[str, Type[BaseIntegration]] = {}
    
    def register(self, name: str, integration_class: Type[BaseIntegration]):
        """手动注册集成"""
        self._registered_integrations[name] = integration_class
        integration_manager.register_integration(integration_class, name)
        logger.info(f"手动注册集成: {name}")
    
    def auto_discover(self, package_name: str = "app.integrations.providers"):
        """自动发现并注册集成"""
        try:
            package = importlib.import_module(package_name)
            
            for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                if not ispkg:
                    try:
                        module = importlib.import_module(modname)
                        self._discover_integrations_in_module(module)
                    except Exception as e:
                        logger.warning(f"导入模块 {modname} 失败: {e}")
                        
        except ImportError as e:
            logger.warning(f"自动发现集成失败，包 {package_name} 不存在: {e}")
    
    def _discover_integrations_in_module(self, module):
        """在模块中发现集成类"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            if (isinstance(attr, type) and 
                issubclass(attr, BaseIntegration) and 
                attr != BaseIntegration and
                not attr.__name__.startswith('_')):
                
                # 生成集成名称
                integration_name = attr_name.lower().replace('integration', '')
                
                self._registered_integrations[integration_name] = attr
                integration_manager.register_integration(attr, integration_name)
                logger.info(f"自动发现集成: {integration_name} ({attr.__name__})")
    
    def get_registered_integrations(self) -> Dict[str, Type[BaseIntegration]]:
        """获取已注册的集成"""
        return self._registered_integrations.copy()
    
    def is_registered(self, name: str) -> bool:
        """检查集成是否已注册"""
        return name in self._registered_integrations
    
    def get_integration_class(self, name: str) -> Type[BaseIntegration]:
        """获取集成类"""
        return self._registered_integrations.get(name)


# 全局注册表实例
integration_registry = IntegrationRegistry()


def register_integration(name: str):
    """装饰器：注册集成"""
    def decorator(cls: Type[BaseIntegration]):
        integration_registry.register(name, cls)
        return cls
    return decorator


# 自动发现和注册集成
def initialize_integrations():
    """初始化集成注册表"""
    integration_registry.auto_discover()
    logger.info(f"集成注册表初始化完成，共注册 {len(integration_registry.get_registered_integrations())} 个集成")