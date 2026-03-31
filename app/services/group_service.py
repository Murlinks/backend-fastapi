"""
群组协作服务
Requirements: 6.1, 6.2, 6.3, 6.4
"""
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.group import Group, GroupMember, ExpenseSplit
from app.models.user import User
from app.models.expense import Expense
from app.repositories.group_repository import (
    GroupRepository, 
    GroupMemberRepository, 
    ExpenseSplitRepository
)
from app.repositories.user_repository import UserRepository
from app.repositories.expense_repository import ExpenseRepository


class SplitType(str, Enum):
    """分摊类型"""
    EQUAL = "equal"  # 平均分摊
    EXACT = "exact"  # 精确金额
    PERCENTAGE = "percentage"  # 按比例
    SHARES = "shares"  # 按份额


class GroupService:
    """群组管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.group_repo = GroupRepository(db)
        self.member_repo = GroupMemberRepository(db)
        self.user_repo = UserRepository(db)
    
    async def create_group(
        self,
        creator_id: str,
        name: str,
        group_type: str,
        shared_budget: Optional[Decimal] = None
    ) -> Group:
        """
        创建协作群组
        Requirements: 6.1, 6.4
        """
        # 验证创建者存在
        creator = await self.user_repo.get_by_id(creator_id)
        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="创建者不存在"
            )
        
        # 验证群组类型
        valid_types = ["dormitory", "team_building", "travel", "family", "friends"]
        if group_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的群组类型，支持的类型: {', '.join(valid_types)}"
            )
        
        # 创建群组
        group = await self.group_repo.create(
            name=name,
            creator_id=creator_id,
            group_type=group_type,
            shared_budget=shared_budget
        )
        
        # 自动将创建者添加为管理员
        await self.member_repo.add_member(
            group_id=str(group.id),
            user_id=creator_id,
            permissions={
                "can_add_expense": True,
                "can_edit_expense": True,
                "can_delete_expense": True,
                "can_invite_member": True,
                "can_remove_member": True,
                "can_edit_group": True,
                "is_admin": True
            }
        )
        
        return group
    
    async def get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户参与的群组列表
        Requirements: 6.1
        """
        groups = await self.group_repo.get_user_groups(user_id)
        result = []
        
        for group in groups:
            member_count = await self.group_repo.get_group_member_count(str(group.id))
            result.append({
                **group.to_dict(),
                "member_count": member_count
            })
        
        return result
    
    async def get_group_details(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取群组详细信息
        Requirements: 6.1
        """
        # 验证用户是否为群组成员
        if not await self.member_repo.is_member(group_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不是该群组成员"
            )
        
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="群组不存在"
            )
        
        members = await self.member_repo.get_group_members(group_id)
        member_count = len(members)
        
        return {
            **group.to_dict(),
            "member_count": member_count,
            "members": [member.to_dict() for member in members]
        }
    
    async def invite_member(
        self,
        group_id: str,
        inviter_id: str,
        phone_number: str,
        permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        邀请用户加入群组
        Requirements: 6.4
        """
        # 验证邀请者权限
        inviter_permissions = await self.member_repo.get_member_permissions(group_id, inviter_id)
        if not inviter_permissions or not inviter_permissions.get("can_invite_member", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有邀请成员的权限"
            )
        
        # 查找被邀请用户
        user = await self.user_repo.get_by_phone(phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 检查用户是否已经是成员
        if await self.member_repo.is_member(group_id, str(user.id)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已经是群组成员"
            )
        
        # 设置默认权限
        if permissions is None:
            permissions = {
                "can_add_expense": True,
                "can_edit_expense": False,
                "can_delete_expense": False,
                "can_invite_member": False,
                "can_remove_member": False,
                "can_edit_group": False,
                "is_admin": False
            }
        
        # 添加成员
        member = await self.member_repo.add_member(
            group_id=group_id,
            user_id=str(user.id),
            permissions=permissions
        )
        
        return {
            "message": "成员邀请成功",
            "group_id": group_id,
            "user_id": str(user.id),
            "phone_number": phone_number,
            "member": member.to_dict()
        }
    
    async def update_member_permissions(
        self,
        group_id: str,
        admin_id: str,
        target_user_id: str,
        new_permissions: Dict[str, Any]
    ) -> bool:
        """
        更新成员权限
        Requirements: 6.4
        """
        # 验证管理员权限
        admin_permissions = await self.member_repo.get_member_permissions(group_id, admin_id)
        if not admin_permissions or not admin_permissions.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有管理权限"
            )
        
        # 验证目标用户是否为成员
        if not await self.member_repo.is_member(group_id, target_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标用户不是群组成员"
            )
        
        # 更新权限
        success = await self.member_repo.update_member_permissions(
            group_id=group_id,
            user_id=target_user_id,
            permissions=new_permissions
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="权限更新失败"
            )
        
        return True
    
    async def remove_member(
        self,
        group_id: str,
        admin_id: str,
        target_user_id: str
    ) -> bool:
        """
        移除群组成员
        Requirements: 6.4
        """
        # 验证管理员权限
        admin_permissions = await self.member_repo.get_member_permissions(group_id, admin_id)
        if not admin_permissions or not admin_permissions.get("can_remove_member", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有移除成员的权限"
            )
        
        # 不能移除自己
        if admin_id == target_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能移除自己"
            )
        
        # 获取群组信息
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="群组不存在"
            )
        
        # 不能移除群组创建者
        if str(group.creator_id) == target_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能移除群组创建者"
            )
        
        # 移除成员
        success = await self.member_repo.remove_member(group_id, target_user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标用户不是群组成员"
            )
        
        return True
    
    async def delete_group(self, group_id: str, user_id: str) -> bool:
        """
        删除群组（仅创建者可删除）
        Requirements: 6.1
        """
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="群组不存在"
            )
        
        # 只有创建者可以删除群组
        if str(group.creator_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有群组创建者可以删除群组"
            )
        
        # 删除群组（级联删除成员和分摊记录）
        success = await self.group_repo.delete(group_id)
        return success


class ExpenseSplitService:
    """费用分摊服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.split_repo = ExpenseSplitRepository(db)
        self.member_repo = GroupMemberRepository(db)
        self.expense_repo = ExpenseRepository(db)
    
    async def create_expense_split(
        self,
        group_id: str,
        expense_id: str,
        payer_id: str,
        splits: Dict[str, Decimal],
        user_id: str
    ) -> ExpenseSplit:
        """
        创建费用分摊
        Requirements: 6.2, 6.3
        """
        # 验证用户权限
        permissions = await self.member_repo.get_member_permissions(group_id, user_id)
        if not permissions or not permissions.get("can_add_expense", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有添加支出的权限"
            )
        
        # 验证付款人是否为群组成员
        if not await self.member_repo.is_member(group_id, payer_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="付款人不是群组成员"
            )
        
        # 验证所有分摊对象都是群组成员
        for split_user_id in splits.keys():
            if not await self.member_repo.is_member(group_id, split_user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"用户 {split_user_id} 不是群组成员"
                )
        
        # 创建分摊记录
        split = await self.split_repo.create(
            group_id=group_id,
            expense_id=expense_id,
            payer_id=payer_id,
            splits=splits
        )
        
        return split
    
    async def calculate_split_amounts(
        self,
        total_amount: Decimal,
        split_type: SplitType,
        participants: List[str],
        split_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Decimal]:
        """
        计算费用分摊金额
        Requirements: 6.2, 6.3
        
        Args:
            total_amount: 总金额
            split_type: 分摊类型
            participants: 参与者用户ID列表
            split_data: 分摊数据（根据类型不同而不同）
        
        Returns:
            用户ID到分摊金额的映射
        """
        if not participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="参与者列表不能为空"
            )
        
        splits = {}
        
        if split_type == SplitType.EQUAL:
            # 平均分摊
            amount_per_person = total_amount / len(participants)
            for user_id in participants:
                splits[user_id] = amount_per_person
        
        elif split_type == SplitType.EXACT:
            # 精确金额分摊
            if not split_data or "amounts" not in split_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="精确分摊需要提供具体金额"
                )
            
            amounts = split_data["amounts"]
            total_specified = sum(Decimal(str(amounts.get(user_id, 0))) for user_id in participants)
            
            if abs(total_specified - total_amount) > Decimal("0.01"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"指定金额总和({total_specified})与总金额({total_amount})不匹配"
                )
            
            for user_id in participants:
                splits[user_id] = Decimal(str(amounts.get(user_id, 0)))
        
        elif split_type == SplitType.PERCENTAGE:
            # 按比例分摊
            if not split_data or "percentages" not in split_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="比例分摊需要提供百分比"
                )
            
            percentages = split_data["percentages"]
            total_percentage = sum(float(percentages.get(user_id, 0)) for user_id in participants)
            
            if abs(total_percentage - 100.0) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"百分比总和({total_percentage}%)必须等于100%"
                )
            
            for user_id in participants:
                percentage = Decimal(str(percentages.get(user_id, 0))) / 100
                splits[user_id] = total_amount * percentage
        
        elif split_type == SplitType.SHARES:
            # 按份额分摊
            if not split_data or "shares" not in split_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="份额分摊需要提供份额数"
                )
            
            shares = split_data["shares"]
            total_shares = sum(int(shares.get(user_id, 0)) for user_id in participants)
            
            if total_shares <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="总份额必须大于0"
                )
            
            for user_id in participants:
                user_shares = int(shares.get(user_id, 0))
                splits[user_id] = total_amount * Decimal(user_shares) / Decimal(total_shares)
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的分摊类型: {split_type}"
            )
        
        return splits
    
    async def create_smart_split(
        self,
        group_id: str,
        expense_id: str,
        payer_id: str,
        split_type: SplitType,
        participants: List[str],
        split_data: Optional[Dict[str, Any]],
        user_id: str
    ) -> ExpenseSplit:
        """
        智能创建费用分摊
        Requirements: 6.2, 6.3
        """
        # 获取支出信息
        expense = await self.expense_repo.get_by_id(expense_id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="支出记录不存在"
            )
        
        # 计算分摊金额
        splits = await self.calculate_split_amounts(
            total_amount=expense.amount,
            split_type=split_type,
            participants=participants,
            split_data=split_data
        )
        
        # 创建分摊记录
        return await self.create_expense_split(
            group_id=group_id,
            expense_id=expense_id,
            payer_id=payer_id,
            splits=splits,
            user_id=user_id
        )
    
    async def get_group_splits(self, group_id: str, user_id: str) -> List[ExpenseSplit]:
        """
        获取群组费用分摊记录
        Requirements: 6.2, 6.3
        """
        # 验证用户是否为群组成员
        if not await self.member_repo.is_member(group_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不是该群组成员"
            )
        
        return await self.split_repo.get_group_splits(group_id)
    
    async def get_shared_ledger(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取共享账本信息
        Requirements: 6.2, 6.3
        """
        # 验证用户是否为群组成员
        if not await self.member_repo.is_member(group_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不是该群组成员"
            )
        
        # 获取所有分摊记录
        splits = await self.split_repo.get_group_splits(group_id)
        
        # 统计信息
        total_expenses = Decimal("0.00")
        settled_expenses = Decimal("0.00")
        unsettled_expenses = Decimal("0.00")
        
        # 按用户统计支出和分摊
        user_stats = {}
        
        for split in splits:
            split_total = sum(Decimal(str(amount)) for amount in split.splits.values())
            total_expenses += split_total
            
            if split.settled:
                settled_expenses += split_total
            else:
                unsettled_expenses += split_total
            
            # 统计付款人支出
            payer_id = str(split.payer_id)
            if payer_id not in user_stats:
                user_stats[payer_id] = {
                    "total_paid": Decimal("0.00"),
                    "total_owed": Decimal("0.00"),
                    "net_balance": Decimal("0.00")
                }
            user_stats[payer_id]["total_paid"] += split_total
            
            # 统计每个人应付金额
            for user_id_str, amount in split.splits.items():
                if user_id_str not in user_stats:
                    user_stats[user_id_str] = {
                        "total_paid": Decimal("0.00"),
                        "total_owed": Decimal("0.00"),
                        "net_balance": Decimal("0.00")
                    }
                user_stats[user_id_str]["total_owed"] += Decimal(str(amount))
        
        # 计算净余额
        for user_id_str in user_stats:
            stats = user_stats[user_id_str]
            stats["net_balance"] = stats["total_paid"] - stats["total_owed"]
        
        return {
            "group_id": group_id,
            "summary": {
                "total_expenses": float(total_expenses),
                "settled_expenses": float(settled_expenses),
                "unsettled_expenses": float(unsettled_expenses),
                "settlement_rate": float(settled_expenses / total_expenses * 100) if total_expenses > 0 else 0
            },
            "user_statistics": {
                user_id: {
                    "total_paid": float(stats["total_paid"]),
                    "total_owed": float(stats["total_owed"]),
                    "net_balance": float(stats["net_balance"])
                }
                for user_id, stats in user_stats.items()
            },
            "recent_splits": [split.to_dict() for split in splits[-10:]]  # 最近10条记录
        }
    
    async def calculate_group_balances(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """
        计算群组结算信息
        Requirements: 6.3
        """
        # 验证用户是否为群组成员
        if not await self.member_repo.is_member(group_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不是该群组成员"
            )
        
        # 计算余额
        balances = await self.split_repo.calculate_group_balances(group_id)
        
        # 计算总支出
        splits = await self.split_repo.get_group_splits(group_id)
        total_expenses = Decimal("0.00")
        
        for split in splits:
            split_total = sum(Decimal(str(amount)) for amount in split.splits.values())
            total_expenses += split_total
        
        return {
            "group_id": group_id,
            "balances": balances,
            "total_expenses": float(total_expenses),
            "settlement_suggestions": self._generate_settlement_suggestions(balances)
        }
    
    def _generate_settlement_suggestions(self, balances: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        生成结算建议
        Requirements: 6.3
        """
        # 分离债权人和债务人
        creditors = {k: v for k, v in balances.items() if v > 0}
        debtors = {k: abs(v) for k, v in balances.items() if v < 0}
        
        suggestions = []
        
        # 简单的结算算法：让债务最多的人先还给债权最多的人
        while creditors and debtors:
            # 找到最大债权人和最大债务人
            max_creditor = max(creditors.items(), key=lambda x: x[1])
            max_debtor = max(debtors.items(), key=lambda x: x[1])
            
            creditor_id, credit_amount = max_creditor
            debtor_id, debt_amount = max_debtor
            
            # 计算转账金额
            transfer_amount = min(credit_amount, debt_amount)
            
            suggestions.append({
                "from_user_id": debtor_id,
                "to_user_id": creditor_id,
                "amount": transfer_amount,
                "description": f"结算群组费用"
            })
            
            # 更新余额
            creditors[creditor_id] -= transfer_amount
            debtors[debtor_id] -= transfer_amount
            
            # 移除已结清的账户
            if creditors[creditor_id] <= 0.01:  # 考虑浮点数精度
                del creditors[creditor_id]
            if debtors[debtor_id] <= 0.01:
                del debtors[debtor_id]
        
        return suggestions
    
    async def settle_split(self, split_id: str, user_id: str) -> bool:
        """
        标记费用分摊为已结算
        Requirements: 6.3
        """
        # 获取分摊记录
        split = await self.split_repo.get_by_id(split_id)
        if not split:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分摊记录不存在"
            )
        
        # 验证用户权限（管理员或付款人可以标记结算）
        permissions = await self.member_repo.get_member_permissions(str(split.group_id), user_id)
        is_payer = str(split.payer_id) == user_id
        is_admin = permissions and permissions.get("is_admin", False)
        
        if not (is_payer or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有付款人或管理员可以标记结算"
            )
        
        return await self.split_repo.settle_split(split_id)
    
    async def batch_settle_splits(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """
        批量结算群组所有未结算分摊
        Requirements: 6.3
        """
        # 验证用户权限
        permissions = await self.member_repo.get_member_permissions(group_id, user_id)
        if not permissions or not permissions.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以批量结算"
            )
        
        # 获取所有未结算分摊
        unsettled_splits = await self.split_repo.get_unsettled_splits(group_id)
        
        settled_count = 0
        for split in unsettled_splits:
            success = await self.split_repo.settle_split(str(split.id))
            if success:
                settled_count += 1
        
        return {
            "message": f"批量结算完成，共结算 {settled_count} 条记录",
            "settled_count": settled_count,
            "total_count": len(unsettled_splits)
        }