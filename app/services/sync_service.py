"""
跨设备同步服务
实现WebSocket实时同步、数据冲突检测和解决机制
"""
import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import redis.asyncio as redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.models.expense import Expense
from app.models.budget import Budget


class SyncEventType(str, Enum):
    """同步事件类型"""
    EXPENSE_CREATED = "expense_created"
    EXPENSE_UPDATED = "expense_updated"
    EXPENSE_DELETED = "expense_deleted"
    BUDGET_CREATED = "budget_created"
    BUDGET_UPDATED = "budget_updated"
    BUDGET_DELETED = "budget_deleted"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    CONFLICT_DETECTED = "conflict_detected"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"


class ConflictResolutionStrategy(str, Enum):
    """冲突解决策略"""
    LATEST_WINS = "latest_wins"
    USER_CHOICE = "user_choice"
    MERGE = "merge"


@dataclass
class SyncEvent:
    """同步事件数据结构"""
    event_id: str
    event_type: SyncEventType
    user_id: str
    device_id: str
    data: Dict[str, Any]
    timestamp: datetime
    version: int = 1


@dataclass
class DataConflict:
    """数据冲突信息"""
    conflict_id: str
    resource_type: str
    resource_id: str
    local_version: Dict[str, Any]
    remote_version: Dict[str, Any]
    timestamp: datetime


@dataclass
class ConflictResolution:
    """冲突解决方案"""
    conflict_id: str
    strategy: ConflictResolutionStrategy
    chosen_version: Optional[Dict[str, Any]] = None
    merged_data: Optional[Dict[str, Any]] = None


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接: user_id -> {device_id -> websocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 存储设备信息: device_id -> {user_id, last_seen, version}
        self.device_info: Dict[str, Dict[str, Any]] = {}
        # 存储待处理的冲突: conflict_id -> DataConflict
        self.pending_conflicts: Dict[str, DataConflict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, device_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][device_id] = websocket
        self.device_info[device_id] = {
            "user_id": user_id,
            "last_seen": datetime.utcnow(),
            "version": 1
        }
        
        # 通知其他设备有新设备连接
        await self.broadcast_to_user_devices(
            user_id, 
            SyncEvent(
                event_id=str(uuid4()),
                event_type=SyncEventType.DEVICE_CONNECTED,
                user_id=user_id,
                device_id=device_id,
                data={"device_id": device_id},
                timestamp=datetime.utcnow()
            ),
            exclude_device=device_id
        )
    
    def disconnect(self, user_id: str, device_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            if device_id in self.active_connections[user_id]:
                del self.active_connections[user_id][device_id]
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        if device_id in self.device_info:
            del self.device_info[device_id]
    
    async def send_to_device(self, user_id: str, device_id: str, event: SyncEvent):
        """发送消息到特定设备"""
        if (user_id in self.active_connections and 
            device_id in self.active_connections[user_id]):
            
            websocket = self.active_connections[user_id][device_id]
            try:
                await websocket.send_text(json.dumps(asdict(event), default=str))
            except Exception:
                # 连接已断开，清理连接
                self.disconnect(user_id, device_id)
    
    async def broadcast_to_user_devices(self, user_id: str, event: SyncEvent, exclude_device: Optional[str] = None):
        """广播消息到用户的所有设备"""
        if user_id not in self.active_connections:
            return
        
        for device_id, websocket in self.active_connections[user_id].items():
            if exclude_device and device_id == exclude_device:
                continue
            
            try:
                await websocket.send_text(json.dumps(asdict(event), default=str))
            except Exception:
                # 连接已断开，清理连接
                self.disconnect(user_id, device_id)
    
    def get_user_devices(self, user_id: str) -> List[str]:
        """获取用户的所有在线设备"""
        if user_id in self.active_connections:
            return list(self.active_connections[user_id].keys())
        return []


class SyncService:
    """同步服务"""
    
    def __init__(self):
        self.websocket_manager = WebSocketManager()
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """初始化同步服务"""
        self.redis_client = await get_redis()
    
    async def handle_websocket_connection(self, websocket: WebSocket, user_id: str, device_id: str):
        """处理WebSocket连接"""
        await self.websocket_manager.connect(websocket, user_id, device_id)
        
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                event_data = json.loads(data)
                
                # 处理同步事件
                await self.handle_sync_event(event_data, user_id, device_id)
                
        except WebSocketDisconnect:
            self.websocket_manager.disconnect(user_id, device_id)
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.websocket_manager.disconnect(user_id, device_id)
    
    async def handle_sync_event(self, event_data: Dict[str, Any], user_id: str, device_id: str):
        """处理同步事件"""
        event_type = event_data.get("event_type")
        
        if event_type == SyncEventType.SYNC_REQUEST:
            await self.handle_sync_request(event_data, user_id, device_id)
        elif event_type in [SyncEventType.EXPENSE_CREATED, SyncEventType.EXPENSE_UPDATED, SyncEventType.EXPENSE_DELETED]:
            await self.handle_expense_sync(event_data, user_id, device_id)
        elif event_type in [SyncEventType.BUDGET_CREATED, SyncEventType.BUDGET_UPDATED, SyncEventType.BUDGET_DELETED]:
            await self.handle_budget_sync(event_data, user_id, device_id)
    
    async def handle_sync_request(self, event_data: Dict[str, Any], user_id: str, device_id: str):
        """处理同步请求"""
        # 获取客户端最后同步时间
        last_sync = event_data.get("last_sync")
        
        # 从数据库获取更新的数据
        async for db in get_db():
            # 获取更新的支出记录
            expenses = await self.get_updated_expenses(db, user_id, last_sync)
            # 获取更新的预算记录
            budgets = await self.get_updated_budgets(db, user_id, last_sync)
            
            # 发送同步响应
            sync_response = SyncEvent(
                event_id=str(uuid4()),
                event_type=SyncEventType.SYNC_RESPONSE,
                user_id=user_id,
                device_id=device_id,
                data={
                    "expenses": expenses,
                    "budgets": budgets,
                    "sync_timestamp": datetime.utcnow().isoformat()
                },
                timestamp=datetime.utcnow()
            )
            
            await self.websocket_manager.send_to_device(user_id, device_id, sync_response)
            break
    
    async def handle_expense_sync(self, event_data: Dict[str, Any], user_id: str, device_id: str):
        """处理支出同步事件"""
        # 检查是否存在冲突
        conflict = await self.detect_expense_conflict(event_data, user_id)
        
        if conflict:
            # 存储冲突并通知用户
            self.websocket_manager.pending_conflicts[conflict.conflict_id] = conflict
            
            conflict_event = SyncEvent(
                event_id=str(uuid4()),
                event_type=SyncEventType.CONFLICT_DETECTED,
                user_id=user_id,
                device_id=device_id,
                data=asdict(conflict),
                timestamp=datetime.utcnow()
            )
            
            await self.websocket_manager.send_to_device(user_id, device_id, conflict_event)
        else:
            # 无冲突，广播到其他设备
            sync_event = SyncEvent(
                event_id=str(uuid4()),
                event_type=SyncEventType(event_data["event_type"]),
                user_id=user_id,
                device_id=device_id,
                data=event_data.get("data", {}),
                timestamp=datetime.utcnow()
            )
            
            await self.websocket_manager.broadcast_to_user_devices(
                user_id, sync_event, exclude_device=device_id
            )
    
    async def handle_budget_sync(self, event_data: Dict[str, Any], user_id: str, device_id: str):
        """处理预算同步事件"""
        # 检查是否存在冲突
        conflict = await self.detect_budget_conflict(event_data, user_id)
        
        if conflict:
            # 存储冲突并通知用户
            self.websocket_manager.pending_conflicts[conflict.conflict_id] = conflict
            
            conflict_event = SyncEvent(
                event_id=str(uuid4()),
                event_type=SyncEventType.CONFLICT_DETECTED,
                user_id=user_id,
                device_id=device_id,
                data=asdict(conflict),
                timestamp=datetime.utcnow()
            )
            
            await self.websocket_manager.send_to_device(user_id, device_id, conflict_event)
        else:
            # 无冲突，广播到其他设备
            sync_event = SyncEvent(
                event_id=str(uuid4()),
                event_type=SyncEventType(event_data["event_type"]),
                user_id=user_id,
                device_id=device_id,
                data=event_data.get("data", {}),
                timestamp=datetime.utcnow()
            )
            
            await self.websocket_manager.broadcast_to_user_devices(
                user_id, sync_event, exclude_device=device_id
            )
    
    async def detect_expense_conflict(self, event_data: Dict[str, Any], user_id: str) -> Optional[DataConflict]:
        """检测支出数据冲突"""
        expense_id = event_data.get("data", {}).get("id")
        if not expense_id:
            return None
        
        # 从数据库获取当前版本
        async for db in get_db():
            result = await db.execute(
                select(Expense).where(
                    and_(Expense.id == expense_id, Expense.user_id == user_id)
                )
            )
            current_expense = result.scalar_one_or_none()
            
            if current_expense:
                # 检查时间戳是否冲突
                client_timestamp = datetime.fromisoformat(event_data.get("data", {}).get("updated_at", ""))
                if current_expense.updated_at > client_timestamp:
                    return DataConflict(
                        conflict_id=str(uuid4()),
                        resource_type="expense",
                        resource_id=expense_id,
                        local_version=event_data.get("data", {}),
                        remote_version={
                            "id": str(current_expense.id),
                            "amount": float(current_expense.amount),
                            "category": current_expense.category,
                            "description": current_expense.description,
                            "updated_at": current_expense.updated_at.isoformat()
                        },
                        timestamp=datetime.utcnow()
                    )
            break
        
        return None
    
    async def detect_budget_conflict(self, event_data: Dict[str, Any], user_id: str) -> Optional[DataConflict]:
        """检测预算数据冲突"""
        budget_id = event_data.get("data", {}).get("id")
        if not budget_id:
            return None
        
        # 从数据库获取当前版本
        async for db in get_db():
            result = await db.execute(
                select(Budget).where(
                    and_(Budget.id == budget_id, Budget.user_id == user_id)
                )
            )
            current_budget = result.scalar_one_or_none()
            
            if current_budget:
                # 检查时间戳是否冲突
                client_timestamp = datetime.fromisoformat(event_data.get("data", {}).get("updated_at", ""))
                if current_budget.updated_at > client_timestamp:
                    return DataConflict(
                        conflict_id=str(uuid4()),
                        resource_type="budget",
                        resource_id=budget_id,
                        local_version=event_data.get("data", {}),
                        remote_version={
                            "id": str(current_budget.id),
                            "total_amount": float(current_budget.total_amount),
                            "remaining_amount": float(current_budget.remaining_amount),
                            "category": current_budget.category,
                            "updated_at": current_budget.updated_at.isoformat()
                        },
                        timestamp=datetime.utcnow()
                    )
            break
        
        return None
    
    async def resolve_conflict(self, conflict_id: str, resolution: ConflictResolution) -> bool:
        """解决数据冲突"""
        if conflict_id not in self.websocket_manager.pending_conflicts:
            return False
        
        conflict = self.websocket_manager.pending_conflicts[conflict_id]
        
        # 根据解决策略处理冲突
        if resolution.strategy == ConflictResolutionStrategy.LATEST_WINS:
            # 使用最新版本
            final_data = conflict.remote_version
        elif resolution.strategy == ConflictResolutionStrategy.USER_CHOICE:
            # 使用用户选择的版本
            final_data = resolution.chosen_version
        elif resolution.strategy == ConflictResolutionStrategy.MERGE:
            # 使用合并后的数据
            final_data = resolution.merged_data
        else:
            return False
        
        # 更新数据库
        success = await self.apply_conflict_resolution(conflict, final_data)
        
        if success:
            # 清理冲突记录
            del self.websocket_manager.pending_conflicts[conflict_id]
            
            # 广播解决结果到所有设备
            resolution_event = SyncEvent(
                event_id=str(uuid4()),
                event_type=SyncEventType.SYNC_RESPONSE,
                user_id=conflict.local_version.get("user_id", ""),
                device_id="server",
                data={
                    "conflict_resolved": True,
                    "conflict_id": conflict_id,
                    "final_data": final_data
                },
                timestamp=datetime.utcnow()
            )
            
            user_id = conflict.local_version.get("user_id", "")
            await self.websocket_manager.broadcast_to_user_devices(user_id, resolution_event)
        
        return success
    
    async def apply_conflict_resolution(self, conflict: DataConflict, final_data: Dict[str, Any]) -> bool:
        """应用冲突解决方案到数据库"""
        try:
            async for db in get_db():
                if conflict.resource_type == "expense":
                    # 更新支出记录
                    result = await db.execute(
                        select(Expense).where(Expense.id == conflict.resource_id)
                    )
                    expense = result.scalar_one_or_none()
                    
                    if expense:
                        expense.amount = final_data.get("amount", expense.amount)
                        expense.category = final_data.get("category", expense.category)
                        expense.description = final_data.get("description", expense.description)
                        expense.updated_at = datetime.utcnow()
                        
                        await db.commit()
                
                elif conflict.resource_type == "budget":
                    # 更新预算记录
                    result = await db.execute(
                        select(Budget).where(Budget.id == conflict.resource_id)
                    )
                    budget = result.scalar_one_or_none()
                    
                    if budget:
                        budget.total_amount = final_data.get("total_amount", budget.total_amount)
                        budget.remaining_amount = final_data.get("remaining_amount", budget.remaining_amount)
                        budget.updated_at = datetime.utcnow()
                        
                        await db.commit()
                
                return True
        except Exception as e:
            print(f"Error applying conflict resolution: {e}")
            return False
        
        return False
    
    async def get_updated_expenses(self, db: AsyncSession, user_id: str, last_sync: Optional[str]) -> List[Dict[str, Any]]:
        """获取更新的支出记录"""
        query = select(Expense).where(Expense.user_id == user_id)
        
        if last_sync:
            sync_time = datetime.fromisoformat(last_sync)
            query = query.where(Expense.updated_at > sync_time)
        
        result = await db.execute(query)
        expenses = result.scalars().all()
        
        return [
            {
                "id": str(expense.id),
                "amount": float(expense.amount),
                "category": expense.category,
                "description": expense.description,
                "created_at": expense.created_at.isoformat(),
                "updated_at": expense.updated_at.isoformat()
            }
            for expense in expenses
        ]
    
    async def get_updated_budgets(self, db: AsyncSession, user_id: str, last_sync: Optional[str]) -> List[Dict[str, Any]]:
        """获取更新的预算记录"""
        query = select(Budget).where(Budget.user_id == user_id)
        
        if last_sync:
            sync_time = datetime.fromisoformat(last_sync)
            query = query.where(Budget.updated_at > sync_time)
        
        result = await db.execute(query)
        budgets = result.scalars().all()
        
        return [
            {
                "id": str(budget.id),
                "total_amount": float(budget.total_amount),
                "remaining_amount": float(budget.remaining_amount),
                "category": budget.category,
                "period_start": budget.period_start.isoformat(),
                "period_end": budget.period_end.isoformat(),
                "created_at": budget.created_at.isoformat(),
                "updated_at": budget.updated_at.isoformat()
            }
            for budget in budgets
        ]


# 全局同步服务实例
sync_service = SyncService()