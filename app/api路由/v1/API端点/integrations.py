"""
第三方集成管理API端点
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel

from app.integrations.manager import integration_manager
from app.integrations.registry import integration_registry
from app.integrations.base import IntegrationConfig, IntegrationType, WebhookEvent
from app.middleware.auth import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter()


class IntegrationConfigRequest(BaseModel):
    """集成配置请求"""
    name: str
    type: IntegrationType
    enabled: bool = True
    config: Dict[str, Any] = {}
    credentials: Dict[str, str] = {}
    webhook_url: Optional[str] = None
    rate_limit: Optional[int] = None
    timeout: int = 30
    retry_count: int = 3
    metadata: Dict[str, Any] = {}


class IntegrationStatusResponse(BaseModel):
    """集成状态响应"""
    name: str
    type: str
    status: str
    enabled: bool
    configured: bool
    last_error: Optional[str]
    last_success: Optional[str]
    last_failure: Optional[str]
    statistics: Dict[str, Any]


class WebhookEventRequest(BaseModel):
    """Webhook事件请求"""
    event_id: str
    event_type: str
    source: str
    data: Dict[str, Any]
    signature: Optional[str] = None
    headers: Dict[str, str] = {}


@router.get("/available", response_model=List[str])
async def get_available_integrations():
    """
    获取可用的集成类型列表
    
    Returns:
        可用集成类型列表
    """
    return integration_manager.get_available_integrations()


@router.get("/registered", response_model=Dict[str, str])
async def get_registered_integrations():
    """
    获取已注册的集成类
    
    Returns:
        已注册集成类信息
    """
    registered = integration_registry.get_registered_integrations()
    return {
        name: cls.__name__ 
        for name, cls in registered.items()
    }


@router.get("/status", response_model=Dict[str, IntegrationStatusResponse])
async def get_all_integration_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取所有集成状态
    
    Args:
        current_user: 当前用户
    
    Returns:
        所有集成状态信息
    """
    status_data = integration_manager.get_all_status()
    
    return {
        name: IntegrationStatusResponse(**status_info)
        for name, status_info in status_data.items()
    }


@router.get("/status/{integration_name}", response_model=IntegrationStatusResponse)
async def get_integration_status(
    integration_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取指定集成状态
    
    Args:
        integration_name: 集成名称
        current_user: 当前用户
    
    Returns:
        集成状态信息
    """
    status_info = integration_manager.get_integration_status(integration_name)
    
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"集成 {integration_name} 不存在"
        )
    
    return IntegrationStatusResponse(**status_info)


@router.post("/configure/{integration_name}")
async def configure_integration(
    integration_name: str,
    config_request: IntegrationConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """
    配置集成
    
    Args:
        integration_name: 集成名称
        config_request: 配置请求
        current_user: 当前用户
    
    Returns:
        配置结果
    """
    if integration_name not in integration_manager.get_available_integrations():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"集成类型 {integration_name} 不可用"
        )
    
    try:
        # 创建集成配置
        config = IntegrationConfig(
            name=config_request.name,
            type=config_request.type,
            enabled=config_request.enabled,
            config=config_request.config,
            credentials=config_request.credentials,
            webhook_url=config_request.webhook_url,
            rate_limit=config_request.rate_limit,
            timeout=config_request.timeout,
            retry_count=config_request.retry_count,
            metadata=config_request.metadata
        )
        
        # 初始化集成
        success = await integration_manager.initialize_integration(integration_name, config)
        
        if success:
            return {
                "success": True,
                "message": f"集成 {integration_name} 配置成功",
                "integration_name": integration_name
            }
        else:
            return {
                "success": False,
                "message": f"集成 {integration_name} 配置失败，请检查配置参数",
                "integration_name": integration_name
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置集成失败: {str(e)}"
        )


@router.post("/reload/{integration_name}")
async def reload_integration(
    integration_name: str,
    config_request: IntegrationConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """
    重新加载集成
    
    Args:
        integration_name: 集成名称
        config_request: 配置请求
        current_user: 当前用户
    
    Returns:
        重新加载结果
    """
    try:
        # 创建集成配置
        config = IntegrationConfig(
            name=config_request.name,
            type=config_request.type,
            enabled=config_request.enabled,
            config=config_request.config,
            credentials=config_request.credentials,
            webhook_url=config_request.webhook_url,
            rate_limit=config_request.rate_limit,
            timeout=config_request.timeout,
            retry_count=config_request.retry_count,
            metadata=config_request.metadata
        )
        
        # 重新加载集成
        success = await integration_manager.reload_integration(integration_name, config)
        
        if success:
            return {
                "success": True,
                "message": f"集成 {integration_name} 重新加载成功",
                "integration_name": integration_name
            }
        else:
            return {
                "success": False,
                "message": f"集成 {integration_name} 重新加载失败",
                "integration_name": integration_name
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载集成失败: {str(e)}"
        )


@router.post("/test/{integration_name}")
async def test_integration(
    integration_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    测试集成连接
    
    Args:
        integration_name: 集成名称
        current_user: 当前用户
    
    Returns:
        测试结果
    """
    try:
        result = await integration_manager.test_integration(integration_name)
        
        return {
            "success": result.success,
            "message": "连接测试完成",
            "integration_name": integration_name,
            "test_result": {
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "status_code": result.status_code,
                "response_time": result.response_time
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试集成失败: {str(e)}"
        )


@router.post("/test-all")
async def test_all_integrations(
    current_user: User = Depends(get_current_user)
):
    """
    测试所有集成连接
    
    Args:
        current_user: 当前用户
    
    Returns:
        所有集成测试结果
    """
    try:
        results = await integration_manager.test_all_integrations()
        
        test_results = {}
        success_count = 0
        
        for name, result in results.items():
            test_results[name] = {
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "status_code": result.status_code,
                "response_time": result.response_time
            }
            
            if result.success:
                success_count += 1
        
        return {
            "success": True,
            "message": f"测试完成，成功: {success_count}/{len(results)}",
            "results": test_results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "failed": len(results) - success_count
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试所有集成失败: {str(e)}"
        )


@router.post("/enable/{integration_name}")
async def enable_integration(
    integration_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    启用集成
    
    Args:
        integration_name: 集成名称
        current_user: 当前用户
    
    Returns:
        启用结果
    """
    try:
        success = await integration_manager.enable_integration(integration_name)
        
        if success:
            return {
                "success": True,
                "message": f"集成 {integration_name} 已启用",
                "integration_name": integration_name
            }
        else:
            return {
                "success": False,
                "message": f"集成 {integration_name} 启用失败，请检查配置",
                "integration_name": integration_name
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启用集成失败: {str(e)}"
        )


@router.post("/disable/{integration_name}")
async def disable_integration(
    integration_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    禁用集成
    
    Args:
        integration_name: 集成名称
        current_user: 当前用户
    
    Returns:
        禁用结果
    """
    try:
        success = await integration_manager.disable_integration(integration_name)
        
        if success:
            return {
                "success": True,
                "message": f"集成 {integration_name} 已禁用",
                "integration_name": integration_name
            }
        else:
            return {
                "success": False,
                "message": f"集成 {integration_name} 禁用失败",
                "integration_name": integration_name
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"禁用集成失败: {str(e)}"
        )


@router.get("/by-type/{integration_type}")
async def get_integrations_by_type(
    integration_type: IntegrationType,
    current_user: User = Depends(get_current_user)
):
    """
    根据类型获取集成
    
    Args:
        integration_type: 集成类型
        current_user: 当前用户
    
    Returns:
        指定类型的集成列表
    """
    try:
        integrations = integration_manager.get_integrations_by_type(integration_type)
        
        return {
            "integration_type": integration_type,
            "count": len(integrations),
            "integrations": [
                {
                    "name": integration.name,
                    "status": integration.status,
                    "enabled": integration.config.enabled,
                    "configured": integration.is_configured()
                }
                for integration in integrations
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取集成列表失败: {str(e)}"
        )


@router.post("/webhook/{webhook_url:path}")
async def handle_webhook(
    webhook_url: str,
    event_request: WebhookEventRequest
):
    """
    处理Webhook事件
    
    Args:
        webhook_url: Webhook URL
        event_request: 事件请求
    
    Returns:
        处理结果
    """
    try:
        # 创建Webhook事件
        event = WebhookEvent(
            event_id=event_request.event_id,
            event_type=event_request.event_type,
            source=event_request.source,
            timestamp=datetime.now(),
            data=event_request.data,
            signature=event_request.signature,
            headers=event_request.headers
        )
        
        # 处理事件
        result = await integration_manager.handle_webhook(webhook_url, event)
        
        return {
            "success": result.success,
            "message": "Webhook事件处理完成",
            "event_id": event_request.event_id,
            "event_type": event_request.event_type,
            "result": {
                "success": result.success,
                "error": result.error,
                "data": result.data,
                "response_time": result.response_time
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理Webhook事件失败: {str(e)}"
        )


@router.get("/health")
async def integration_health_check():
    """
    集成健康检查
    
    Returns:
        健康检查结果
    """
    try:
        health_info = await integration_manager.health_check()
        
        return {
            "success": True,
            "message": "集成健康检查完成",
            "health": health_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get("/config-template/{integration_name}")
async def get_integration_config_template(
    integration_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取集成配置模板
    
    Args:
        integration_name: 集成名称
        current_user: 当前用户
    
    Returns:
        配置模板
    """
    if integration_name not in integration_manager.get_available_integrations():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"集成类型 {integration_name} 不存在"
        )
    
    # 获取集成类
    integration_class = integration_registry.get_integration_class(integration_name)
    
    if not integration_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"集成类 {integration_name} 未注册"
        )
    
    # 创建临时实例获取配置信息
    temp_config = IntegrationConfig(
        name=integration_name,
        type=integration_class.type if hasattr(integration_class, 'type') else IntegrationType.PAYMENT
    )
    temp_instance = integration_class(temp_config)
    
    return {
        "integration_name": integration_name,
        "display_name": temp_instance.name,
        "type": temp_instance.type,
        "required_credentials": temp_instance.required_credentials,
        "config_template": {
            "name": integration_name,
            "type": temp_instance.type,
            "enabled": True,
            "config": {},
            "credentials": {
                field: f"请填写{field}"
                for field in temp_instance.required_credentials
            },
            "webhook_url": None,
            "rate_limit": None,
            "timeout": 30,
            "retry_count": 3,
            "metadata": {}
        }
    }