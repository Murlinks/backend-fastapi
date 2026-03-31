"""
预算数据访问层
Requirements: 3.1, 3.2, 8.1, 8.2
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from datetime import datetime
from decimal import Decimal

from app.models.budget import Budget
from app.repositories.base_repository import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    """预算Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Budget, db)
    
    async def get_by_user(
        self,
        user_id: str,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[Budget]:
        """获取用户的预算记录"""
        query = select(Budget).where(Budget.user_id == user_id)
        
        # 应用过滤条件
        if category:
            query = query.where(Budget.category == category)
        
        if active_only:
            now = datetime.utcnow()
            query = query.where(
                and_(
                    Budget.period_start <= now,
                    Budget.period_end >= now
                )
            )
        
        # 按创建时间倒序排列
        query = query.order_by(desc(Budget.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_active_budget(
        self,
        user_id: str,
        category: str
    ) -> Optional[Budget]:
        """获取用户当前活跃的预算"""
        now = datetime.utcnow()
        
        query = select(Budget).where(
            and_(
                Budget.user_id == user_id,
                Budget.category == category,
                Budget.period_start <= now,
                Budget.period_end >= now
            )
        ).order_by(desc(Budget.created_at))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_remaining_amount(
        self,
        budget_id: str,
        amount_spent: Decimal
    ) -> Optional[Budget]:
        """更新预算剩余金额"""
        budget = await self.get_by_id(budget_id)
        if not budget:
            return None
        
        new_remaining = budget.remaining_amount - amount_spent
        return await self.update(budget_id, remaining_amount=new_remaining)
    
    async def check_overspending(
        self,
        user_id: str,
        category: str,
        amount: Decimal
    ) -> tuple[bool, Optional[Budget], Decimal]:
        """
        检查是否会导致超支
        Returns: (is_overspending, budget, percentage_used)
        Requirements: 3.3, 8.2
        """
        budget = await self.get_active_budget(user_id, category)
        
        if not budget:
            return False, None, Decimal("0.0")
        
        new_remaining = budget.remaining_amount - amount
        percentage_used = ((budget.total_amount - new_remaining) / budget.total_amount) * 100
        
        # 考虑灵活性百分比
        max_allowed = budget.total_amount
        if budget.is_flexible:
            max_allowed = budget.total_amount * (1 + budget.flexibility_percentage / 100)
        
        is_overspending = new_remaining < 0 and abs(new_remaining) > (max_allowed - budget.total_amount)
        
        return is_overspending, budget, percentage_used
