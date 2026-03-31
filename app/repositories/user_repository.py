"""
用户数据访问层
Requirements: 7.3
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        """根据手机号获取用户"""
        result = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()
    
    async def update_last_active(self, user_id: str) -> None:
        """更新用户最后活跃时间"""
        from datetime import datetime
        await self.update(user_id, last_active=datetime.utcnow())