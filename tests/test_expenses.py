"""
测试支出管理API
Requirements: 2.3, 8.1
"""
import pytest
from httpx import AsyncClient
from decimal import Decimal
import uuid


@pytest.mark.asyncio
async def test_create_expense_success(client: AsyncClient):
    """测试成功创建支出记录"""
    user_id = str(uuid.uuid4())
    
    expense_data = {
        "user_id": user_id,
        "amount": 25.50,
        "category": "dining",
        "description": "午餐",
        "location": "学校食堂",
        "emotion_context": "neutral",
        "is_emergency": False
    }
    
    response = await client.post("/api/v1/expenses/", json=expense_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "25.50"
    assert data["category"] == "dining"
    assert data["description"] == "午餐"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_expense_invalid_category(client: AsyncClient):
    """测试创建支出记录时使用无效类别"""
    user_id = str(uuid.uuid4())
    
    expense_data = {
        "user_id": user_id,
        "amount": 25.50,
        "category": "invalid_category",
        "description": "测试",
        "is_emergency": False
    }
    
    response = await client.post("/api/v1/expenses/", json=expense_data)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_expense_negative_amount(client: AsyncClient):
    """测试创建支出记录时使用负数金额"""
    user_id = str(uuid.uuid4())
    
    expense_data = {
        "user_id": user_id,
        "amount": -25.50,
        "category": "dining",
        "description": "测试",
        "is_emergency": False
    }
    
    response = await client.post("/api/v1/expenses/", json=expense_data)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_expenses_list(client: AsyncClient):
    """测试获取支出列表"""
    user_id = str(uuid.uuid4())
    
    # 先创建一条支出记录
    expense_data = {
        "user_id": user_id,
        "amount": 25.50,
        "category": "dining",
        "description": "午餐",
        "is_emergency": False
    }
    
    create_response = await client.post("/api/v1/expenses/", json=expense_data)
    assert create_response.status_code == 201
    
    # 获取支出列表
    response = await client.get(f"/api/v1/expenses/?user_id={user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_expense_by_id(client: AsyncClient):
    """测试根据ID获取支出详情"""
    user_id = str(uuid.uuid4())
    
    # 先创建一条支出记录
    expense_data = {
        "user_id": user_id,
        "amount": 25.50,
        "category": "dining",
        "description": "午餐",
        "is_emergency": False
    }
    
    create_response = await client.post("/api/v1/expenses/", json=expense_data)
    assert create_response.status_code == 201
    expense_id = create_response.json()["id"]
    
    # 获取支出详情
    response = await client.get(f"/api/v1/expenses/{expense_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == expense_id
    assert data["amount"] == "25.50"


@pytest.mark.asyncio
async def test_delete_expense(client: AsyncClient):
    """测试删除支出记录"""
    user_id = str(uuid.uuid4())
    
    # 先创建一条支出记录
    expense_data = {
        "user_id": user_id,
        "amount": 25.50,
        "category": "dining",
        "description": "午餐",
        "is_emergency": False
    }
    
    create_response = await client.post("/api/v1/expenses/", json=expense_data)
    assert create_response.status_code == 201
    expense_id = create_response.json()["id"]
    
    # 删除支出记录
    response = await client.delete(f"/api/v1/expenses/{expense_id}")
    
    assert response.status_code == 204
    
    # 验证记录已删除
    get_response = await client.get(f"/api/v1/expenses/{expense_id}")
    assert get_response.status_code == 404
