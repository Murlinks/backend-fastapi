"""
跨设备同步API端点
提供WebSocket实时同步和冲突解决接口
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.sync_service import sync_service, ConflictResolution, ConflictResolutionStrategy
from app.middleware.auth import get_current_user_websocket, get_current_user
from app.models.user import User

router = APIRouter()


class ConflictResolutionRequest(BaseModel):
    """冲突解决请求"""
    conflict_id: str
    strategy: ConflictResolutionStrategy
    chosen_version: Optional[Dict[str, Any]] = None
    merged_data: Optional[Dict[str, Any]] = None


class SyncStatusResponse(BaseModel):
    """同步状态响应"""
    user_id: str
    connected_devices: list[str]
    pending_conflicts: int
    last_sync: Optional[str] = None


@router.websocket("/ws/{user_id}/{device_id}")
async def websocket_sync_endpoint(
    websocket: WebSocket, 
    user_id: str, 
    device_id: str
):
    """
    WebSocket实时同步端点
    
    连接格式: /api/v1/sync/ws/{user_id}/{device_id}
    
    消息格式:
    {
        "event_type": "sync_request|expense_created|expense_updated|...",
        "data": {...},
        "timestamp": "2024-01-01T00:00:00Z",
        "last_sync": "2024-01-01T00:00:00Z"  // 仅sync_request需要
    }
    """
    # 验证用户身份 (简化版本，实际应该验证token)
    # user = await get_current_user_websocket(websocket)
    
    # 初始化同步服务
    if not sync_service.redis_client:
        await sync_service.initialize()
    
    # 处理WebSocket连接
    await sync_service.handle_websocket_connection(websocket, user_id, device_id)


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution_request: ConflictResolutionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    解决数据冲突
    
    Args:
        conflict_id: 冲突ID
        resolution_request: 冲突解决方案
        current_user: 当前用户
    
    Returns:
        解决结果
    """
    # 验证冲突是否属于当前用户
    if conflict_id not in sync_service.websocket_manager.pending_conflicts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="冲突不存在或已解决"
        )
    
    conflict = sync_service.websocket_manager.pending_conflicts[conflict_id]
    conflict_user_id = conflict.local_version.get("user_id")
    
    if conflict_user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限解决此冲突"
        )
    
    # 创建冲突解决方案
    resolution = ConflictResolution(
        conflict_id=conflict_id,
        strategy=resolution_request.strategy,
        chosen_version=resolution_request.chosen_version,
        merged_data=resolution_request.merged_data
    )
    
    # 解决冲突
    success = await sync_service.resolve_conflict(conflict_id, resolution)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="冲突解决失败"
        )
    
    return {
        "success": True,
        "message": "冲突已成功解决",
        "conflict_id": conflict_id
    }


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(current_user: User = Depends(get_current_user)):
    """
    获取用户同步状态
    
    Args:
        current_user: 当前用户
    
    Returns:
        同步状态信息
    """
    user_id = str(current_user.id)
    
    # 获取连接的设备
    connected_devices = sync_service.websocket_manager.get_user_devices(user_id)
    
    # 获取待处理冲突数量
    pending_conflicts = sum(
        1 for conflict in sync_service.websocket_manager.pending_conflicts.values()
        if conflict.local_version.get("user_id") == user_id
    )
    
    return SyncStatusResponse(
        user_id=user_id,
        connected_devices=connected_devices,
        pending_conflicts=pending_conflicts
    )


@router.get("/conflicts")
async def get_pending_conflicts(current_user: User = Depends(get_current_user)):
    """
    获取用户的待处理冲突列表
    
    Args:
        current_user: 当前用户
    
    Returns:
        冲突列表
    """
    user_id = str(current_user.id)
    
    user_conflicts = [
        {
            "conflict_id": conflict_id,
            "resource_type": conflict.resource_type,
            "resource_id": conflict.resource_id,
            "local_version": conflict.local_version,
            "remote_version": conflict.remote_version,
            "timestamp": conflict.timestamp.isoformat()
        }
        for conflict_id, conflict in sync_service.websocket_manager.pending_conflicts.items()
        if conflict.local_version.get("user_id") == user_id
    ]
    
    return {
        "conflicts": user_conflicts,
        "total": len(user_conflicts)
    }


@router.post("/force-sync")
async def force_sync(current_user: User = Depends(get_current_user)):
    """
    强制触发全量同步
    
    Args:
        current_user: 当前用户
    
    Returns:
        同步触发结果
    """
    user_id = str(current_user.id)
    
    # 获取用户的所有连接设备
    connected_devices = sync_service.websocket_manager.get_user_devices(user_id)
    
    if not connected_devices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有连接的设备"
        )
    
    # 向所有设备发送同步请求
    from app.services.sync_service import SyncEvent, SyncEventType
    from datetime import datetime
    from uuid import uuid4
    
    sync_event = SyncEvent(
        event_id=str(uuid4()),
        event_type=SyncEventType.SYNC_REQUEST,
        user_id=user_id,
        device_id="server",
        data={"force_sync": True},
        timestamp=datetime.utcnow()
    )
    
    await sync_service.websocket_manager.broadcast_to_user_devices(user_id, sync_event)
    
    return {
        "success": True,
        "message": f"已向 {len(connected_devices)} 个设备发送同步请求",
        "devices": connected_devices
    }