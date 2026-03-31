"""
群组和协作模型
Requirements: 6.1, 6.2, 6.3, 6.4
"""
from sqlalchemy import Column, String, DateTime, Numeric, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Group(Base):
    """群组模型"""
    __tablename__ = "groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_type = Column(String(20), nullable=False)
    shared_budget = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    expense_splits = relationship("ExpenseSplit", back_populates="group", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Group(id={self.id}, name={self.name}, type={self.group_type})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "creator_id": str(self.creator_id),
            "group_type": self.group_type,
            "shared_budget": float(self.shared_budget) if self.shared_budget else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class GroupMember(Base):
    """群组成员模型"""
    __tablename__ = "group_members"
    
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    permissions = Column(JSON, default=dict)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    group = relationship("Group", back_populates="members")
    
    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "group_id": str(self.group_id),
            "user_id": str(self.user_id),
            "permissions": self.permissions,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None
        }


class ExpenseSplit(Base):
    """费用分摊模型"""
    __tablename__ = "expense_splits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    payer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    splits = Column(JSON, nullable=False)
    settled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    group = relationship("Group", back_populates="expense_splits")
    
    def __repr__(self):
        return f"<ExpenseSplit(id={self.id}, group_id={self.group_id}, settled={self.settled})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "group_id": str(self.group_id),
            "expense_id": str(self.expense_id),
            "payer_id": str(self.payer_id),
            "splits": self.splits,
            "settled": self.settled,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }