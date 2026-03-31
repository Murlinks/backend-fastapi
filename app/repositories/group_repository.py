"""
群组数据访问层
Requirements: 6.1, 6.2, 6.3, 6.4
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.models.group import Group, GroupMember, ExpenseSplit
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class GroupRepository(BaseRepository[Group]):
    """群组Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Group, db)
    
    async def get_user_groups(self, user_id: str) -> List[Group]:
        """获取用户参与的所有群组"""
        result = await self.db.execute(
            select(Group)
            .join(GroupMember)
            .where(GroupMember.user_id == user_id)
            .order_by(Group.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_group_with_members(self, group_id: str) -> Optional[Group]:
        """获取群组及其成员信息"""
        result = await self.db.execute(
            select(Group)
            .options(selectinload(Group.members))
            .where(Group.id == group_id)
        )
        return result.scalar_one_or_none()
    
    async def get_group_member_count(self, group_id: str) -> int:
        """获取群组成员数量"""
        result = await self.db.execute(
            select(func.count(GroupMember.user_id))
            .where(GroupMember.group_id == group_id)
        )
        return result.scalar() or 0


class GroupMemberRepository(BaseRepository[GroupMember]):
    """群组成员Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(GroupMember, db)
    
    async def add_member(
        self, 
        group_id: str, 
        user_id: str, 
        permissions: Dict[str, Any] = None
    ) -> GroupMember:
        """添加群组成员"""
        if permissions is None:
            permissions = {"can_add_expense": True, "can_edit_expense": False}
        
        member = GroupMember(
            group_id=group_id,
            user_id=user_id,
            permissions=permissions
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member
    
    async def get_group_members(self, group_id: str) -> List[GroupMember]:
        """获取群组所有成员"""
        result = await self.db.execute(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.joined_at)
        )
        return result.scalars().all()
    
    async def get_member_permissions(self, group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取成员权限"""
        result = await self.db.execute(
            select(GroupMember.permissions)
            .where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_member_permissions(
        self, 
        group_id: str, 
        user_id: str, 
        permissions: Dict[str, Any]
    ) -> bool:
        """更新成员权限"""
        result = await self.db.execute(
            select(GroupMember)
            .where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if member:
            member.permissions = permissions
            await self.db.commit()
            return True
        return False
    
    async def remove_member(self, group_id: str, user_id: str) -> bool:
        """移除群组成员"""
        result = await self.db.execute(
            select(GroupMember)
            .where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if member:
            await self.db.delete(member)
            await self.db.commit()
            return True
        return False
    
    async def is_member(self, group_id: str, user_id: str) -> bool:
        """检查用户是否为群组成员"""
        result = await self.db.execute(
            select(func.count(GroupMember.user_id))
            .where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id
                )
            )
        )
        return (result.scalar() or 0) > 0


class ExpenseSplitRepository(BaseRepository[ExpenseSplit]):
    """费用分摊Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ExpenseSplit, db)
    
    async def get_group_splits(self, group_id: str) -> List[ExpenseSplit]:
        """获取群组所有费用分摊记录"""
        result = await self.db.execute(
            select(ExpenseSplit)
            .where(ExpenseSplit.group_id == group_id)
            .order_by(ExpenseSplit.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_unsettled_splits(self, group_id: str) -> List[ExpenseSplit]:
        """获取未结算的费用分摊"""
        result = await self.db.execute(
            select(ExpenseSplit)
            .where(
                and_(
                    ExpenseSplit.group_id == group_id,
                    ExpenseSplit.settled == False
                )
            )
            .order_by(ExpenseSplit.created_at.desc())
        )
        return result.scalars().all()
    
    async def settle_split(self, split_id: str) -> bool:
        """标记费用分摊为已结算"""
        result = await self.db.execute(
            select(ExpenseSplit)
            .where(ExpenseSplit.id == split_id)
        )
        split = result.scalar_one_or_none()
        
        if split:
            split.settled = True
            await self.db.commit()
            return True
        return False
    
    async def calculate_group_balances(self, group_id: str) -> Dict[str, float]:
        """计算群组成员间的债务关系"""
        splits = await self.get_unsettled_splits(group_id)
        balances = {}
        
        for split in splits:
            # 付款人应该收到的钱
            payer_id = str(split.payer_id)
            if payer_id not in balances:
                balances[payer_id] = 0.0
            
            # 计算每个人应该支付的金额
            for user_id, amount in split.splits.items():
                if user_id not in balances:
                    balances[user_id] = 0.0
                
                if user_id == payer_id:
                    # 付款人收到其他人应付的钱
                    total_others_owe = sum(
                        float(amt) for uid, amt in split.splits.items() 
                        if uid != payer_id
                    )
                    balances[payer_id] += total_others_owe
                else:
                    # 其他人欠付款人的钱
                    balances[user_id] -= float(amount)
        
        return balances