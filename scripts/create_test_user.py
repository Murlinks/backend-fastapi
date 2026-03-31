#!/usr/bin/env python3
"""
创建测试用户脚本
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.user import User
from app.core.database import Base


async def create_test_users():
    """创建测试用户"""
    # 创建异步引擎
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 创建测试用户
        test_users = [
            User(
                phone_number="13800138000",
                identity="student",
                preferences={"theme": "light", "language": "zh-CN"}
            ),
            User(
                phone_number="13800138001",
                identity="office_worker",
                preferences={"theme": "dark", "language": "zh-CN"}
            ),
            User(
                phone_number="13800138002",
                identity="freelancer",
                preferences={"theme": "light", "language": "en-US"}
            )
        ]
        
        for user in test_users:
            session.add(user)
        
        await session.commit()
        
        print("✓ 测试用户创建成功:")
        for user in test_users:
            print(f"  - {user.phone_number} ({user.identity})")
    
    await engine.dispose()


if __name__ == "__main__":
    print("创建测试用户...")
    asyncio.run(create_test_users())
    print("完成!")