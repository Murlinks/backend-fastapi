"""
查询优化服务
提供批量查询、查询优化、性能监控等功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.expense import Expense
from app.models.budget import Budget
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.batch_size = 100  # 批量查询大小
        self.cache_enabled = True  # 是否启用缓存
    
    async def get_user_expenses_optimized(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        优化的用户支出查询
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            category: 分类过滤
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存
        
        Returns:
            (支出列表, 总数)
        """
        # 尝试从缓存获取
        if use_cache and self.cache_enabled:
            cache_key = self._build_expenses_cache_key(
                user_id, limit, offset, category, start_date, end_date
            )
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                return cached_data["expenses"], cached_data["total"]
        
        # 构建查询
        query = select(Expense).where(Expense.user_id == user_id)
        
        # 添加过滤条件
        if category:
            query = query.where(Expense.category == category)
        if start_date:
            query = query.where(Expense.created_at >= start_date)
        if end_date:
            query = query.where(Expense.created_at <= end_date)
        
        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 执行查询
        query = query.order_by(Expense.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        expenses = result.scalars().all()
        
        # 转换为字典列表
        expense_dicts = [self._expense_to_dict(exp) for exp in expenses]
        
        # 缓存结果
        if use_cache and self.cache_enabled:
            cache_data = {
                "expenses": expense_dicts,
                "total": total
            }
            await cache_service.set(cache_key, cache_data, ttl=300)  # 缓存5分钟
        
        return expense_dicts, total
    
    def _build_expenses_cache_key(
        self,
        user_id: str,
        limit: int,
        offset: int,
        category: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> str:
        """构建支出查询的缓存键"""
        key_parts = [
            f"user:{user_id}",
            f"limit:{limit}",
            f"offset:{offset}"
        ]
        
        if category:
            key_parts.append(f"category:{category}")
        if start_date:
            key_parts.append(f"start:{start_date.isoformat()}")
        if end_date:
            key_parts.append(f"end:{end_date.isoformat()}")
        
        return ":".join(key_parts)
    
    async def get_user_budgets_optimized(
        self,
        db: AsyncSession,
        user_id: str,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        优化的用户预算查询
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            use_cache: 是否使用缓存
        
        Returns:
            预算列表
        """
        # 尝试从缓存获取
        if use_cache and self.cache_enabled:
            cache_key = f"user:{user_id}:budgets"
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                return cached_data
        
        # 执行查询
        query = select(Budget).where(Budget.user_id == user_id)
        result = await db.execute(query)
        budgets = result.scalars().all()
        
        # 转换为字典列表
        budget_dicts = [self._budget_to_dict(budget) for budget in budgets]
        
        # 缓存结果
        if use_cache and self.cache_enabled:
            await cache_service.set(cache_key, budget_dicts, ttl=600)  # 缓存10分钟
        
        return budget_dicts
    
    async def get_expense_summary_optimized(
        self,
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        优化的支出摘要查询
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存
        
        Returns:
            支出摘要
        """
        # 尝试从缓存获取
        if use_cache and self.cache_enabled:
            cache_key = f"user:{user_id}:summary:{start_date or 'all'}:{end_date or 'all'}"
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                return cached_data
        
        # 构建查询
        query = select(Expense).where(Expense.user_id == user_id)
        
        if start_date:
            query = query.where(Expense.created_at >= start_date)
        if end_date:
            query = query.where(Expense.created_at <= end_date)
        
        # 执行查询
        result = await db.execute(query)
        expenses = result.scalars().all()
        
        # 计算摘要
        total_amount = sum(exp.amount for exp in expenses)
        category_summary = {}
        
        for exp in expenses:
            if exp.category not in category_summary:
                category_summary[exp.category] = {
                    "count": 0,
                    "total": Decimal(0)
                }
            category_summary[exp.category]["count"] += 1
            category_summary[exp.category]["total"] += exp.amount
        
        # 转换为可序列化的格式
        summary = {
            "total_expenses": len(expenses),
            "total_amount": float(total_amount),
            "average_amount": float(total_amount / len(expenses)) if expenses else 0,
            "category_summary": {
                cat: {
                    "count": data["count"],
                    "total": float(data["total"])
                }
                for cat, data in category_summary.items()
            }
        }
        
        # 缓存结果
        if use_cache and self.cache_enabled:
            await cache_service.set(cache_key, summary, ttl=300)  # 缓存5分钟
        
        return summary
    
    async def batch_get_expenses(
        self,
        db: AsyncSession,
        expense_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取支出记录
        
        Args:
            db: 数据库会话
            expense_ids: 支出ID列表
            use_cache: 是否使用缓存
        
        Returns:
            ID到支出记录的映射
        """
        result = {}
        
        # 分批查询
        for i in range(0, len(expense_ids), self.batch_size):
            batch_ids = expense_ids[i:i + self.batch_size]
            
            # 尝试从缓存获取
            if use_cache and self.cache_enabled:
                cached_batch = await self._get_expenses_from_cache(batch_ids)
                result.update(cached_batch)
                batch_ids = [eid for eid in batch_ids if eid not in cached_batch]
            
            # 查询数据库
            if batch_ids:
                query = select(Expense).where(Expense.id.in_(batch_ids))
                db_result = await db.execute(query)
                expenses = db_result.scalars().all()
                
                for exp in expenses:
                    exp_dict = self._expense_to_dict(exp)
                    result[exp.id] = exp_dict
                    
                    # 缓存结果
                    if use_cache and self.cache_enabled:
                        await cache_service.set(
                            f"expense:{exp.id}",
                            exp_dict,
                            ttl=600
                        )
        
        return result
    
    async def _get_expenses_from_cache(
        self,
        expense_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """从缓存获取支出记录"""
        result = {}
        
        for expense_id in expense_ids:
            cached_data = await cache_service.get(f"expense:{expense_id}")
            if cached_data:
                result[expense_id] = cached_data
        
        return result
    
    async def get_category_stats_optimized(
        self,
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        优化的分类统计查询
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存
        
        Returns:
            分类统计
        """
        # 尝试从缓存获取
        if use_cache and self.cache_enabled:
            cache_key = f"user:{user_id}:category_stats:{start_date or 'all'}:{end_date or 'all'}"
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                return cached_data
        
        # 构建查询
        query = select(
            Expense.category,
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('total'),
            func.avg(Expense.amount).label('average')
        ).where(Expense.user_id == user_id)
        
        if start_date:
            query = query.where(Expense.created_at >= start_date)
        if end_date:
            query = query.where(Expense.created_at <= end_date)
        
        query = query.group_by(Expense.category)
        
        # 执行查询
        result = await db.execute(query)
        rows = result.all()
        
        # 构建统计结果
        stats = {}
        for row in rows:
            stats[row.category] = {
                "count": row.count,
                "total": float(row.total) if row.total else 0,
                "average": float(row.average) if row.average else 0
            }
        
        # 缓存结果
        if use_cache and self.cache_enabled:
            await cache_service.set(cache_key, stats, ttl=300)  # 缓存5分钟
        
        return stats
    
    async def invalidate_user_cache(self, user_id: str):
        """
        使用户相关缓存失效
        
        Args:
            user_id: 用户ID
        """
        await cache_service.invalidate_user_cache(user_id)
    
    def _expense_to_dict(self, expense: Expense) -> Dict[str, Any]:
        """将支出对象转换为字典"""
        return {
            "id": expense.id,
            "user_id": expense.user_id,
            "amount": float(expense.amount),
            "category": expense.category,
            "description": expense.description,
            "created_at": expense.created_at.isoformat() if expense.created_at else None,
            "updated_at": expense.updated_at.isoformat() if expense.updated_at else None
        }
    
    def _budget_to_dict(self, budget: Budget) -> Dict[str, Any]:
        """将预算对象转换为字典"""
        return {
            "id": budget.id,
            "user_id": budget.user_id,
            "category": budget.category,
            "amount": float(budget.amount),
            "period_start": budget.period_start.isoformat() if budget.period_start else None,
            "period_end": budget.period_end.isoformat() if budget.period_end else None
        }


# 全局查询优化器实例
query_optimizer = QueryOptimizer()