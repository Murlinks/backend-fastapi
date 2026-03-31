"""
支出数据访问层
Requirements: 2.3, 8.1
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from datetime import datetime

from app.models.expense import Expense
from app.repositories.base_repository import BaseRepository


class ExpenseRepository(BaseRepository[Expense]):
    """支出Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Expense, db)
    
    async def get_by_user(
        self,
        user_id: str,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Expense]:
        """获取用户的支出记录"""
        query = select(Expense).where(Expense.user_id == user_id)
        
        # 应用过滤条件
        if category:
            query = query.where(Expense.category == category)
        
        if start_date:
            query = query.where(Expense.created_at >= start_date)
        
        if end_date:
            query = query.where(Expense.created_at <= end_date)
        
        # 按创建时间倒序排列
        query = query.order_by(desc(Expense.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_total_by_category(
        self,
        user_id: str,
        category: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """获取指定时间段内某类别的总支出"""
        from sqlalchemy import func
        
        query = select(func.sum(Expense.amount)).where(
            and_(
                Expense.user_id == user_id,
                Expense.category == category,
                Expense.created_at >= start_date,
                Expense.created_at <= end_date
            )
        )
        
        result = await self.db.execute(query)
        total = result.scalar()
        return float(total) if total else 0.0
    
    async def check_duplicate(
        self,
        user_id: str,
        amount: float,
        description: str,
        time_window_minutes: int = 5
    ) -> Optional[Expense]:
        """
        检查是否存在重复的支出记录
        Requirements: 2.3, 2.4
        """
        from datetime import timedelta
        
        time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        query = select(Expense).where(
            and_(
                Expense.user_id == user_id,
                Expense.amount == amount,
                Expense.description == description,
                Expense.created_at >= time_threshold
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()