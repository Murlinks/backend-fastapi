"""
测试预算管理API
Requirements: 3.1, 3.2, 8.1, 8.2
"""
import pytest
from httpx import AsyncClient
from decimal import Decimal
from datetime import datetime, timedelta
import uuid


@pytest.mark.asyncio
async def test_create_budget_success(client: AsyncClient):
    """测试成功创建预算"""
    user_id = str(uuid.uuid4())
    
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "is_flexible": True,
        "flexibility_percentage": 10.0
    }
    
    response = await client.post("/api/v1/budgets/", json=budget_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["total_amount"] == "1000.00"
    assert data["remaining_amount"] == "1000.00"  # 初始剩余金额等于总金额
    assert data["category"] == "dining"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_budget_invalid_period(client: AsyncClient):
    """测试创建预算时使用无效的时间周期"""
    user_id = str(uuid.uuid4())
    
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": now.isoformat(),
        "period_end": (now - timedelta(days=1)).isoformat(),  # 结束时间早于开始时间
        "is_flexible": False,
        "flexibility_percentage": 0.0
    }
    
    response = await client.post("/api/v1/budgets/", json=budget_data)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_budgets_list(client: AsyncClient):
    """测试获取预算列表"""
    user_id = str(uuid.uuid4())
    
    # 先创建一条预算记录
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "is_flexible": True,
        "flexibility_percentage": 10.0
    }
    
    create_response = await client.post("/api/v1/budgets/", json=budget_data)
    assert create_response.status_code == 201
    
    # 获取预算列表
    response = await client.get(f"/api/v1/budgets/?user_id={user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_remaining_budget(client: AsyncClient):
    """测试获取剩余预算"""
    user_id = str(uuid.uuid4())
    
    # 先创建一条预算记录
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "is_flexible": True,
        "flexibility_percentage": 10.0
    }
    
    create_response = await client.post("/api/v1/budgets/", json=budget_data)
    assert create_response.status_code == 201
    budget_id = create_response.json()["id"]
    
    # 获取剩余预算
    response = await client.get(f"/api/v1/budgets/{budget_id}/remaining")
    
    assert response.status_code == 200
    data = response.json()
    assert data["budget_id"] == budget_id
    assert "remaining_amount" in data
    assert "percentage_remaining" in data
    assert "days_remaining" in data


@pytest.mark.asyncio
async def test_check_overspending(client: AsyncClient):
    """测试检查超支功能"""
    user_id = str(uuid.uuid4())
    
    # 先创建一条预算记录
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "is_flexible": False,
        "flexibility_percentage": 0.0
    }
    
    create_response = await client.post("/api/v1/budgets/", json=budget_data)
    assert create_response.status_code == 201
    
    # 检查小额支出（不会超支）
    response = await client.post(
        "/api/v1/budgets/check-overspending",
        params={
            "user_id": user_id,
            "category": "dining",
            "amount": 100.00
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "dining"
    assert "alert_type" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_get_budget_templates(client: AsyncClient):
    """测试获取预算模板"""
    response = await client.get("/api/v1/budgets/templates/identities")
    
    assert response.status_code == 200
    data = response.json()
    assert "identities" in data
    assert "scenarios" in data
    assert "student" in data["identities"]
    assert "office_worker" in data["identities"]


@pytest.mark.asyncio
async def test_get_recommended_budget(client: AsyncClient):
    """测试获取推荐预算配置"""
    response = await client.get(
        "/api/v1/budgets/templates/recommended",
        params={
            "identity": "student",
            "scenario": "日常"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["identity"] == "student"
    assert data["scenario"] == "日常"
    assert "budgets" in data
    assert "dining" in data["budgets"]
    assert "transportation" in data["budgets"]
