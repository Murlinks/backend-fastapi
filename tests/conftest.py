"""
Pytest configuration and shared fixtures
"""
import asyncio
import pytest
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from main import create_app


# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/finance_db", "/finance_test_db")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""
    app = create_app()
    
    # Override database dependency
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "phone_number": "+8613800138000",
        "identity": "student",
        "preferences": {
            "currency": "CNY",
            "language": "zh-CN"
        }
    }


@pytest.fixture
def sample_expense_data():
    """Sample expense data for testing."""
    return {
        "amount": 25.50,
        "category": "dining",
        "description": "午餐",
        "location": "学校食堂",
        "is_emergency": False
    }


@pytest.fixture
def sample_budget_data():
    """Sample budget data for testing."""
    return {
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": "2024-01-01T00:00:00",
        "period_end": "2024-01-31T23:59:59",
        "is_flexible": True,
        "flexibility_percentage": 10.0
    }


@pytest.fixture
def sample_group_data():
    """Sample group data for testing."""
    return {
        "name": "宿舍账本",
        "group_type": "dormitory",
        "shared_budget": 5000.00
    }
