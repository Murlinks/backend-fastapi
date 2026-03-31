"""PostgreSQL 异步数据库配置与连接管理"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData, event
from sqlalchemy.pool import NullPool, QueuePool
import logging
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    poolclass=NullPool,
    echo_pool=settings.DEBUG,
    connect_args={
        "server_settings": {
            "application_name": "finance_assistant",
            "jit": "off",
        },
        "command_timeout": 60,
        "timeout": 10,
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)


class Base(DeclarativeBase):
    """数据库模型基类"""
    metadata = metadata


async def init_db():
    """
    初始化数据库连接与建表。

    说明：开发联调时，PostgreSQL 容器可能在应用启动时尚未完全 ready，
    因此这里做短时间重试，避免应用直接退出。
    """
    last_err: Exception | None = None
    max_attempts = 10  # 约 30 秒
    delay_seconds = 3

    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                if settings.ENVIRONMENT in {"development", "test"} or settings.DEBUG:
                    await conn.run_sync(Base.metadata.create_all)
                    await conn.run_sync(_create_indexes)
                    logger.info("数据库初始化成功（开发/测试：自动建表+索引）")
                else:
                    logger.info("数据库初始化完成（生产：跳过自动建表，使用迁移管理）")
            return
        except Exception as e:
            last_err = e
            logger.warning(f"数据库初始化失败（第 {attempt}/{max_attempts} 次）: {e}")
            await asyncio.sleep(delay_seconds)

    logger.error(f"数据库初始化最终失败: {last_err}")
    raise last_err


def _create_indexes(connection):
    from sqlalchemy import text
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses(user_id, category)",
        "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_budgets_user_category ON budgets(user_id, category)",
        "CREATE INDEX IF NOT EXISTS idx_budgets_period ON budgets(period_start, period_end)",
        "CREATE INDEX IF NOT EXISTS idx_expenses_description_gin ON expenses USING gin(to_tsvector('english', description))",
    ]
    
    for index_sql in indexes:
        try:
            connection.execute(text(index_sql))
            logger.info(f"索引创建成功: {index_sql[:50]}...")
        except Exception as e:
            logger.warning(f"索引创建跳过（可能已存在）: {e}")


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    await engine.dispose()
    logger.info("数据库连接已关闭")