"""
用户管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db

router = APIRouter()


class UserProfile(BaseModel):
    """用户资料"""
    id: str
    phone_number: str
    identity: str
    preferences: Dict[str, Any]
    created_at: datetime
    last_active: datetime


class UpdateProfileRequest(BaseModel):
    """更新用户资料请求"""
    identity: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


@router.get("/profile", response_model=UserProfile, summary="获取用户资料")
async def get_user_profile(
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户资料
    Requirements: 7.3
    """
    # TODO: 从JWT token获取用户ID
    # TODO: 查询用户信息
    
    # 模拟返回
    return UserProfile(
        id="mock_user_id",
        phone_number="13800138000",
        identity="student",
        preferences={"theme": "light", "language": "zh-CN"},
        created_at=datetime.now(),
        last_active=datetime.now()
    )


@router.put("/profile", response_model=UserProfile, summary="更新用户资料")
async def update_user_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户资料
    Requirements: 7.3
    """
    # TODO: 实现用户资料更新逻辑
    
    return UserProfile(
        id="mock_user_id",
        phone_number="13800138000",
        identity=request.identity or "student",
        preferences=request.preferences or {"theme": "light", "language": "zh-CN"},
        created_at=datetime.now(),
        last_active=datetime.now()
    )


@router.delete("/account", summary="删除账户")
async def delete_account(
    db: AsyncSession = Depends(get_db)
):
    """
    删除用户账户
    Requirements: 7.3
    """
    # TODO: 实现账户删除逻辑
    return {"message": "账户删除成功"}