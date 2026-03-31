"""
群组协作API端点
Requirements: 6.1, 6.2, 6.3, 6.4
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.services.group_service import GroupService, ExpenseSplitService

router = APIRouter()


class GroupCreate(BaseModel):
    """创建群组请求"""
    name: str
    group_type: str
    shared_budget: Optional[Decimal] = None


class GroupResponse(BaseModel):
    """群组响应"""
    id: str
    name: str
    creator_id: str
    group_type: str
    shared_budget: Optional[Decimal]
    member_count: int
    created_at: datetime


class ExpenseSplitCreate(BaseModel):
    """费用分摊创建请求"""
    expense_id: str
    payer_id: str
    splits: Dict[str, Decimal]  # user_id -> amount


class SmartSplitCreate(BaseModel):
    """智能费用分摊创建请求"""
    expense_id: str
    payer_id: str
    split_type: str  # equal, exact, percentage, shares
    participants: List[str]
    split_data: Optional[Dict[str, Any]] = None


class ExpenseSplitResponse(BaseModel):
    """费用分摊响应"""
    id: str
    group_id: str
    expense_id: str
    payer_id: str
    splits: Dict[str, Decimal]
    settled: bool
    created_at: datetime


@router.post("/", response_model=GroupResponse, summary="创建群组")
async def create_group(
    group: GroupCreate,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    创建协作群组
    Requirements: 6.1, 6.4
    """
    service = GroupService(db)
    
    created_group = await service.create_group(
        creator_id=current_user_id,
        name=group.name,
        group_type=group.group_type,
        shared_budget=group.shared_budget
    )
    
    return GroupResponse(
        id=str(created_group.id),
        name=created_group.name,
        creator_id=str(created_group.creator_id),
        group_type=created_group.group_type,
        shared_budget=created_group.shared_budget,
        member_count=1,
        created_at=created_group.created_at
    )


@router.get("/", response_model=List[GroupResponse], summary="获取群组列表")
async def get_groups(
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户参与的群组列表
    Requirements: 6.1
    """
    service = GroupService(db)
    groups = await service.get_user_groups(current_user_id)
    
    return [
        GroupResponse(
            id=group["id"],
            name=group["name"],
            creator_id=group["creator_id"],
            group_type=group["group_type"],
            shared_budget=group["shared_budget"],
            member_count=group["member_count"],
            created_at=datetime.fromisoformat(group["created_at"])
        )
        for group in groups
    ]


@router.post("/{group_id}/members", summary="邀请成员")
async def invite_member(
    group_id: str,
    user_phone: str,
    permissions: Optional[Dict[str, Any]] = None,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    邀请用户加入群组
    Requirements: 6.4
    """
    service = GroupService(db)
    return await service.invite_member(
        group_id=group_id,
        inviter_id=current_user_id,
        phone_number=user_phone,
        permissions=permissions
    )


@router.post("/{group_id}/expenses", summary="添加群组支出")
async def add_group_expense(
    group_id: str,
    expense: Dict[str, Any],
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    添加群组共同支出
    Requirements: 6.2
    """
    # TODO: 集成支出服务，这里暂时返回模拟响应
    # 实际实现需要调用 ExpenseService 创建支出，然后可选择性创建分摊
    
    return {
        "message": "群组支出添加成功",
        "expense_id": "mock_expense_id",
        "group_id": group_id
    }


@router.post("/{group_id}/split", response_model=ExpenseSplitResponse, summary="费用分摊")
async def split_expense(
    group_id: str,
    split_data: ExpenseSplitCreate,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    分摊群组费用
    Requirements: 6.2, 6.3
    """
    service = ExpenseSplitService(db)
    
    split = await service.create_expense_split(
        group_id=group_id,
        expense_id=split_data.expense_id,
        payer_id=split_data.payer_id,
        splits=split_data.splits,
        user_id=current_user_id
    )
    
    return ExpenseSplitResponse(
        id=str(split.id),
        group_id=str(split.group_id),
        expense_id=str(split.expense_id),
        payer_id=str(split.payer_id),
        splits=split.splits,
        settled=split.settled,
        created_at=split.created_at
    )


@router.get("/{group_id}/balance", summary="获取群组结算信息")
async def get_group_balance(
    group_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    获取群组成员间的债务关系
    Requirements: 6.3
    """
    service = ExpenseSplitService(db)
    return await service.calculate_group_balances(group_id, current_user_id)


@router.get("/{group_id}", summary="获取群组详情")
async def get_group_details(
    group_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    获取群组详细信息
    Requirements: 6.1
    """
    service = GroupService(db)
    return await service.get_group_details(group_id, current_user_id)


@router.put("/{group_id}/members/{user_id}/permissions", summary="更新成员权限")
async def update_member_permissions(
    group_id: str,
    user_id: str,
    permissions: Dict[str, Any],
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    更新群组成员权限
    Requirements: 6.4
    """
    service = GroupService(db)
    success = await service.update_member_permissions(
        group_id=group_id,
        admin_id=current_user_id,
        target_user_id=user_id,
        new_permissions=permissions
    )
    
    return {
        "message": "权限更新成功" if success else "权限更新失败",
        "success": success
    }


@router.delete("/{group_id}/members/{user_id}", summary="移除群组成员")
async def remove_member(
    group_id: str,
    user_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    移除群组成员
    Requirements: 6.4
    """
    service = GroupService(db)
    success = await service.remove_member(
        group_id=group_id,
        admin_id=current_user_id,
        target_user_id=user_id
    )
    
    return {
        "message": "成员移除成功" if success else "成员移除失败",
        "success": success
    }


@router.delete("/{group_id}", summary="删除群组")
async def delete_group(
    group_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    删除群组（仅创建者可删除）
    Requirements: 6.1
    """
    service = GroupService(db)
    success = await service.delete_group(group_id, current_user_id)
    
    return {
        "message": "群组删除成功" if success else "群组删除失败",
        "success": success
    }


@router.get("/{group_id}/splits", summary="获取群组分摊记录")
async def get_group_splits(
    group_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    获取群组费用分摊记录
    Requirements: 6.2, 6.3
    """
    service = ExpenseSplitService(db)
    splits = await service.get_group_splits(group_id, current_user_id)
    
    return [
        ExpenseSplitResponse(
            id=str(split.id),
            group_id=str(split.group_id),
            expense_id=str(split.expense_id),
            payer_id=str(split.payer_id),
            splits=split.splits,
            settled=split.settled,
            created_at=split.created_at
        )
        for split in splits
    ]


@router.put("/splits/{split_id}/settle", summary="标记分摊已结算")
async def settle_split(
    split_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    标记费用分摊为已结算
    Requirements: 6.3
    """
    service = ExpenseSplitService(db)
    success = await service.settle_split(split_id, current_user_id)
    
    return {
        "message": "结算标记成功" if success else "结算标记失败",
        "success": success
    }


@router.post("/{group_id}/smart-split", response_model=ExpenseSplitResponse, summary="智能费用分摊")
async def create_smart_split(
    group_id: str,
    split_data: SmartSplitCreate,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    智能创建费用分摊（支持多种分摊算法）
    Requirements: 6.2, 6.3
    """
    from app.services.group_service import SplitType
    
    service = ExpenseSplitService(db)
    
    split = await service.create_smart_split(
        group_id=group_id,
        expense_id=split_data.expense_id,
        payer_id=split_data.payer_id,
        split_type=SplitType(split_data.split_type),
        participants=split_data.participants,
        split_data=split_data.split_data,
        user_id=current_user_id
    )
    
    return ExpenseSplitResponse(
        id=str(split.id),
        group_id=str(split.group_id),
        expense_id=str(split.expense_id),
        payer_id=str(split.payer_id),
        splits=split.splits,
        settled=split.settled,
        created_at=split.created_at
    )


@router.get("/{group_id}/ledger", summary="获取共享账本")
async def get_shared_ledger(
    group_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    获取群组共享账本信息
    Requirements: 6.2, 6.3
    """
    service = ExpenseSplitService(db)
    return await service.get_shared_ledger(group_id, current_user_id)


@router.post("/{group_id}/batch-settle", summary="批量结算")
async def batch_settle_splits(
    group_id: str,
    current_user_id: str = "mock_user_id",  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """
    批量结算群组所有未结算分摊
    Requirements: 6.3
    """
    service = ExpenseSplitService(db)
    return await service.batch_settle_splits(group_id, current_user_id)