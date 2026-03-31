"""
支出管理API端点
Requirements: 2.3, 8.1
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from app.core.database import get_db
from app.models.expense import Expense
from app.repositories.expense_repository import ExpenseRepository

router = APIRouter()


class ExpenseCreate(BaseModel):
    """创建支出请求"""
    user_id: str = Field(..., description="用户ID")
    amount: Decimal = Field(..., gt=0, description="支出金额，必须大于0")
    category: str = Field(..., description="支出类别")
    description: str = Field(..., min_length=1, max_length=500, description="支出描述")
    location: Optional[str] = Field(None, max_length=255, description="支出地点")
    emotion_context: Optional[str] = Field(None, description="情感上下文")
    is_emergency: bool = Field(False, description="是否为紧急支出")
    
    @validator('category')
    def validate_category(cls, v):
        """验证支出类别"""
        valid_categories = ['dining', 'transportation', 'entertainment', 'shopping', 'emergency']
        if v not in valid_categories:
            raise ValueError(f'类别必须是以下之一: {", ".join(valid_categories)}')
        return v
    
    @validator('emotion_context')
    def validate_emotion(cls, v):
        """验证情感上下文"""
        if v is not None:
            valid_emotions = ['happy', 'stressed', 'anxious', 'neutral', 'guilty']
            if v not in valid_emotions:
                raise ValueError(f'情感上下文必须是以下之一: {", ".join(valid_emotions)}')
        return v


class ExpenseUpdate(BaseModel):
    """更新支出请求"""
    amount: Optional[Decimal] = Field(None, gt=0, description="支出金额")
    category: Optional[str] = Field(None, description="支出类别")
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="支出描述")
    location: Optional[str] = Field(None, max_length=255, description="支出地点")
    emotion_context: Optional[str] = Field(None, description="情感上下文")
    is_emergency: Optional[bool] = Field(None, description="是否为紧急支出")
    
    @validator('category')
    def validate_category(cls, v):
        """验证支出类别"""
        if v is not None:
            valid_categories = ['dining', 'transportation', 'entertainment', 'shopping', 'emergency']
            if v not in valid_categories:
                raise ValueError(f'类别必须是以下之一: {", ".join(valid_categories)}')
        return v
    
    @validator('emotion_context')
    def validate_emotion(cls, v):
        """验证情感上下文"""
        if v is not None:
            valid_emotions = ['happy', 'stressed', 'anxious', 'neutral', 'guilty']
            if v not in valid_emotions:
                raise ValueError(f'情感上下文必须是以下之一: {", ".join(valid_emotions)}')
        return v


class ExpenseResponse(BaseModel):
    """支出响应"""
    id: str
    user_id: str
    amount: Decimal
    category: str
    description: str
    location: Optional[str]
    emotion_context: Optional[str]
    is_emergency: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED, summary="创建支出记录")
async def create_expense(
    expense: ExpenseCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的支出记录
    Requirements: 2.3, 8.1
    
    - 验证用户ID和数据格式
    - 检查重复记录（5分钟内相同金额和描述）
    - 自动记录创建时间
    """
    try:
        try:
            uuid.UUID(expense.user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID格式"
            )
        
        repo = ExpenseRepository(db)
        duplicate = await repo.check_duplicate(
            user_id=expense.user_id,
            amount=float(expense.amount),
            description=expense.description,
            time_window_minutes=5
        )
        
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "检测到可能的重复记录",
                    "duplicate_expense": {
                        "id": str(duplicate.id),
                        "amount": float(duplicate.amount),
                        "description": duplicate.description,
                        "created_at": duplicate.created_at.isoformat()
                    },
                    "suggestion": "如果这不是重复记录，请稍后再试或修改描述"
                }
            )
        new_expense = await repo.create(
            user_id=expense.user_id,
            amount=expense.amount,
            category=expense.category,
            description=expense.description,
            location=expense.location,
            emotion_context=expense.emotion_context,
            is_emergency=expense.is_emergency
        )
        
        return ExpenseResponse(
            id=str(new_expense.id),
            user_id=str(new_expense.user_id),
            amount=new_expense.amount,
            category=new_expense.category,
            description=new_expense.description,
            location=new_expense.location,
            emotion_context=new_expense.emotion_context,
            is_emergency=new_expense.is_emergency,
            created_at=new_expense.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建支出记录失败: {str(e)}"
        )


@router.get("/", response_model=List[ExpenseResponse], summary="获取支出列表")
async def get_expenses(
    user_id: str,
    category: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户支出列表
    Requirements: 8.1
    
    - 支持按类别筛选
    - 支持按时间范围筛选
    - 支持分页查询
    """
    try:
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID格式"
            )
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit必须在1-100之间"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="offset必须大于等于0"
            )
        repo = ExpenseRepository(db)
        expenses = await repo.get_by_user(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            skip=offset,
            limit=limit
        )
        
        return [
            ExpenseResponse(
                id=str(exp.id),
                user_id=str(exp.user_id),
                amount=exp.amount,
                category=exp.category,
                description=exp.description,
                location=exp.location,
                emotion_context=exp.emotion_context,
                is_emergency=exp.is_emergency,
                created_at=exp.created_at
            )
            for exp in expenses
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取支出列表失败: {str(e)}"
        )


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="获取支出详情")
async def get_expense(
    expense_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取特定支出详情
    Requirements: 8.1
    """
    try:
        try:
            uuid.UUID(expense_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的支出ID格式"
            )
        repo = ExpenseRepository(db)
        expense = await repo.get_by_id(expense_id)
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="支出记录不存在"
            )
        
        return ExpenseResponse(
            id=str(expense.id),
            user_id=str(expense.user_id),
            amount=expense.amount,
            category=expense.category,
            description=expense.description,
            location=expense.location,
            emotion_context=expense.emotion_context,
            is_emergency=expense.is_emergency,
            created_at=expense.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取支出详情失败: {str(e)}"
        )


@router.put("/{expense_id}", response_model=ExpenseResponse, summary="更新支出记录")
async def update_expense(
    expense_id: str,
    expense_update: ExpenseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新支出记录
    Requirements: 8.1
    """
    try:
        try:
            uuid.UUID(expense_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的支出ID格式"
            )
        repo = ExpenseRepository(db)
        existing_expense = await repo.get_by_id(expense_id)
        if not existing_expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="支出记录不存在"
            )
        update_data = expense_update.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供要更新的字段"
            )
        updated_expense = await repo.update(expense_id, **update_data)
        
        return ExpenseResponse(
            id=str(updated_expense.id),
            user_id=str(updated_expense.user_id),
            amount=updated_expense.amount,
            category=updated_expense.category,
            description=updated_expense.description,
            location=updated_expense.location,
            emotion_context=updated_expense.emotion_context,
            is_emergency=updated_expense.is_emergency,
            created_at=updated_expense.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新支出记录失败: {str(e)}"
        )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除支出记录")
async def delete_expense(
    expense_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除支出记录
    Requirements: 8.1
    """
    try:
        try:
            uuid.UUID(expense_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的支出ID格式"
            )
        repo = ExpenseRepository(db)
        existing_expense = await repo.get_by_id(expense_id)
        if not existing_expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="支出记录不存在"
            )
        success = await repo.delete(expense_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除支出记录失败"
            )
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除支出记录失败: {str(e)}"
        )