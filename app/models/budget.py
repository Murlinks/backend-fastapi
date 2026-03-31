"""
预算模型
Requirements: 3.1, 3.2, 8.1
"""
from sqlalchemy import Column, String, DateTime, Numeric, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base


class Budget(Base):
    """预算模型"""
    __tablename__ = "budgets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(20), nullable=False, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    remaining_amount = Column(Numeric(10, 2), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    is_flexible = Column(Boolean, default=False)
    flexibility_percentage = Column(Numeric(5, 2), default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('total_amount >= 0', name='check_total_amount_positive'),
        CheckConstraint('remaining_amount >= 0', name='check_remaining_amount_positive'),
        CheckConstraint('period_end > period_start', name='check_valid_period'),
        CheckConstraint('flexibility_percentage >= 0 AND flexibility_percentage <= 100', name='check_flexibility_range'),
    )
    
    def __repr__(self):
        return f"<Budget(id={self.id}, category={self.category}, total={self.total_amount})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "category": self.category,
            "total_amount": float(self.total_amount),
            "remaining_amount": float(self.remaining_amount),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "is_flexible": self.is_flexible,
            "flexibility_percentage": float(self.flexibility_percentage),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }