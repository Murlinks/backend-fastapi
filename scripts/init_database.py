#!/usr/bin/env python3
"""
初始化数据库脚本
Requirements: 7.3, 7.5
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.config import settings
from app.core.database import Base

# 导入所有模型
from app.models.user import User
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.group import Group, GroupMember, ExpenseSplit
from app.models.conversation import AIConversation


async def create_database():
    """创建数据库（如果不存在）"""
    # 连接到postgres数据库
    postgres_url = settings.DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
    postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://")
    
    engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    
    async with engine.connect() as conn:
        # 检查数据库是否存在
        db_name = settings.DATABASE_URL.rsplit('/', 1)[1]
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        )
        exists = result.scalar()
        
        if not exists:
            await conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"✓ 数据库 {db_name} 创建成功")
        else:
            print(f"✓ 数据库 {db_name} 已存在")
    
    await engine.dispose()


async def create_tables():
    """创建所有表"""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        # 创建扩展
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
        
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        
        print("\n✓ 所有表创建成功:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")
    
    await engine.dispose()


async def create_indexes():
    """创建优化索引"""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        # 复合索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses(user_id, category)",
            "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_budgets_user_category ON budgets(user_id, category)",
            "CREATE INDEX IF NOT EXISTS idx_budgets_period ON budgets(period_start, period_end)",
            "CREATE INDEX IF NOT EXISTS idx_expenses_description_gin ON expenses USING gin(to_tsvector('english', description))",
        ]
        
        print("\n✓ 创建优化索引:")
        for index_sql in indexes:
            try:
                await conn.execute(text(index_sql))
                index_name = index_sql.split("INDEX IF NOT EXISTS ")[1].split(" ON")[0]
                print(f"  - {index_name}")
            except Exception as e:
                print(f"  ✗ 索引创建失败: {e}")
    
    await engine.dispose()


async def main():
    """主函数"""
    print("=" * 60)
    print("初始化数据库")
    print("=" * 60)
    
    try:
        # 1. 创建数据库
        print("\n1. 创建数据库...")
        await create_database()
        
        # 2. 创建表
        print("\n2. 创建数据表...")
        await create_tables()
        
        # 3. 创建索引
        print("\n3. 创建优化索引...")
        await create_indexes()
        
        print("\n" + "=" * 60)
        print("✓ 数据库初始化完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 数据库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())