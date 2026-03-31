"""
端到端集成测试
Requirements: 8.3, 8.4, 8.5

测试完整的用户流程：注册 -> 记账 -> 预算管理 -> 协作功能
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import uuid
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_user_journey(client: AsyncClient):
    """测试完整的用户使用流程"""
    # 1. 用户注册
    user_data = {
        "phone_number": "+8613800138001",
        "identity": "student",
        "preferences": {
            "currency": "CNY",
            "language": "zh-CN"
        }
    }
    
    register_response = await client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]
    
    # 2. 创建预算
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
    
    budget_response = await client.post("/api/v1/budgets/", json=budget_data)
    assert budget_response.status_code == 201
    budget_id = budget_response.json()["id"]
    
    # 3. 添加支出记录
    expense_data = {
        "user_id": user_id,
        "amount": 25.50,
        "category": "dining",
        "description": "午餐",
        "location": "学校食堂",
        "emotion_context": "neutral",
        "is_emergency": False
    }
    
    expense_response = await client.post("/api/v1/expenses/", json=expense_data)
    assert expense_response.status_code == 201
    expense_id = expense_response.json()["id"]
    
    # 4. 检查预算剩余
    remaining_response = await client.get(f"/api/v1/budgets/{budget_id}/remaining")
    assert remaining_response.status_code == 200
    remaining_data = remaining_response.json()
    assert float(remaining_data["remaining_amount"]) == 1000.00 - 25.50
    
    # 5. AI分析支出
    ai_response = await client.post(
        "/api/v1/ai/analyze",
        json={"text": "今天买奶茶花了15元"}
    )
    assert ai_response.status_code == 200
    ai_data = ai_response.json()
    assert "amount" in ai_data
    assert "category" in ai_data
    
    # 6. 创建协作群组
    group_data = {
        "name": "宿舍账本",
        "creator_id": user_id,
        "group_type": "dormitory",
        "shared_budget": 5000.00
    }
    
    group_response = await client.post("/api/v1/groups/", json=group_data)
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]
    
    # 7. 添加群组支出
    group_expense_data = {
        "group_id": group_id,
        "payer_id": user_id,
        "amount": 100.00,
        "category": "dining",
        "description": "聚餐",
        "split_type": "equal"
    }
    
    group_expense_response = await client.post(
        f"/api/v1/groups/{group_id}/expenses",
        json=group_expense_data
    )
    assert group_expense_response.status_code == 201
    
    # 8. 验证数据一致性
    user_expenses = await client.get(f"/api/v1/expenses/?user_id={user_id}")
    assert user_expenses.status_code == 200
    assert len(user_expenses.json()) >= 1
    
    user_budgets = await client.get(f"/api/v1/budgets/?user_id={user_id}")
    assert user_budgets.status_code == 200
    assert len(user_budgets.json()) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_user_collaboration(client: AsyncClient):
    """测试多用户协作场景"""
    # 创建两个用户
    user1_data = {
        "phone_number": "+8613800138002",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user2_data = {
        "phone_number": "+8613800138003",
        "identity": "office_worker",
        "preferences": {"currency": "CNY"}
    }
    
    user1_response = await client.post("/api/v1/auth/register", json=user1_data)
    user2_response = await client.post("/api/v1/auth/register", json=user2_data)
    
    assert user1_response.status_code == 201
    assert user2_response.status_code == 201
    
    user1_id = user1_response.json()["id"]
    user2_id = user2_response.json()["id"]
    
    # 用户1创建群组
    group_data = {
        "name": "旅行账本",
        "creator_id": user1_id,
        "group_type": "travel",
        "shared_budget": 10000.00
    }
    
    group_response = await client.post("/api/v1/groups/", json=group_data)
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]
    
    # 邀请用户2加入群组
    invite_response = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": user2_id, "permissions": ["view", "add_expense"]}
    )
    assert invite_response.status_code == 201
    
    # 用户1添加支出
    expense1_data = {
        "group_id": group_id,
        "payer_id": user1_id,
        "amount": 500.00,
        "category": "transportation",
        "description": "机票",
        "split_type": "equal"
    }
    
    expense1_response = await client.post(
        f"/api/v1/groups/{group_id}/expenses",
        json=expense1_data
    )
    assert expense1_response.status_code == 201
    
    # 用户2添加支出
    expense2_data = {
        "group_id": group_id,
        "payer_id": user2_id,
        "amount": 300.00,
        "category": "dining",
        "description": "晚餐",
        "split_type": "equal"
    }
    
    expense2_response = await client.post(
        f"/api/v1/groups/{group_id}/expenses",
        json=expense2_data
    )
    assert expense2_response.status_code == 201
    
    # 检查群组总支出
    group_summary_response = await client.get(f"/api/v1/groups/{group_id}/summary")
    assert group_summary_response.status_code == 200
    summary_data = group_summary_response.json()
    assert float(summary_data["total_expenses"]) == 800.00
    
    # 检查结算情况
    settlement_response = await client.get(f"/api/v1/groups/{group_id}/settlement")
    assert settlement_response.status_code == 200
    settlement_data = settlement_response.json()
    assert "balances" in settlement_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ai_multimodal_integration(client: AsyncClient):
    """测试AI多模态集成功能"""
    # 创建用户
    user_data = {
        "phone_number": "+8613800138004",
        "identity": "freelancer",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 测试文本输入分析
    text_analysis_response = await client.post(
        "/api/v1/ai/analyze",
        json={"text": "今天买咖啡花了28元，心情不错"}
    )
    assert text_analysis_response.status_code == 200
    text_data = text_analysis_response.json()
    assert "amount" in text_data
    assert "category" in text_data
    assert "emotion" in text_data
    
    # 测试表情符号输入
    emoji_response = await client.post(
        "/api/v1/ai/multimodal/emoji",
        json={"emoji": "🍔", "context": "午餐"}
    )
    assert emoji_response.status_code == 200
    emoji_data = emoji_response.json()
    assert emoji_data["category"] == "dining"
    
    # 测试手势输入
    gesture_response = await client.post(
        "/api/v1/ai/multimodal/gesture",
        json={"gesture": "swipe_left", "context": "delete_last"}
    )
    assert gesture_response.status_code == 200
    gesture_data = gesture_response.json()
    assert "action" in gesture_data
    
    # 测试多模态输入合并
    multimodal_response = await client.post(
        "/api/v1/ai/multimodal/combine",
        json={
            "text": "今天买了",
            "emoji": "🍕",
            "amount": 35.0,
            "user_id": user_id
        }
    )
    assert multimodal_response.status_code == 200
    multimodal_data = multimodal_response.json()
    assert "expense_suggestion" in multimodal_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_budget_alert_system(client: AsyncClient):
    """测试预算提醒系统集成"""
    # 创建用户
    user_data = {
        "phone_number": "+8613800138005",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 创建小额预算
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "entertainment",
        "total_amount": 100.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "is_flexible": False,
        "flexibility_percentage": 0.0
    }
    
    budget_response = await client.post("/api/v1/budgets/", json=budget_data)
    assert budget_response.status_code == 201
    budget_id = budget_response.json()["id"]
    
    # 添加接近预算限制的支出
    expense_data = {
        "user_id": user_id,
        "amount": 85.00,
        "category": "entertainment",
        "description": "电影票",
        "is_emergency": False
    }
    
    expense_response = await client.post("/api/v1/expenses/", json=expense_data)
    assert expense_response.status_code == 201
    
    # 检查预算提醒
    alert_response = await client.post(
        "/api/v1/budgets/check-overspending",
        params={
            "user_id": user_id,
            "category": "entertainment",
            "amount": 20.00
        }
    )
    assert alert_response.status_code == 200
    alert_data = alert_response.json()
    assert alert_data["alert_type"] in ["warning", "overspending"]
    
    # 测试预算调剂建议
    reallocation_response = await client.post(
        "/api/v1/budgets/suggest-reallocation",
        json={
            "user_id": user_id,
            "emergency_amount": 50.00,
            "target_category": "entertainment"
        }
    )
    assert reallocation_response.status_code == 200
    reallocation_data = reallocation_response.json()
    assert "suggestions" in reallocation_data


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_operations(client: AsyncClient):
    """测试并发操作的数据一致性"""
    # 创建用户
    user_data = {
        "phone_number": "+8613800138006",
        "identity": "office_worker",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 创建预算
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "dining",
        "total_amount": 2000.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "is_flexible": True,
        "flexibility_percentage": 15.0
    }
    
    budget_response = await client.post("/api/v1/budgets/", json=budget_data)
    assert budget_response.status_code == 201
    budget_id = budget_response.json()["id"]
    
    # 并发添加多个支出记录
    async def add_expense(amount: float, description: str):
        expense_data = {
            "user_id": user_id,
            "amount": amount,
            "category": "dining",
            "description": description,
            "is_emergency": False
        }
        return await client.post("/api/v1/expenses/", json=expense_data)
    
    # 创建10个并发任务
    tasks = [
        add_expense(50.0, f"支出{i}")
        for i in range(10)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # 验证所有请求都成功
    for response in responses:
        assert response.status_code == 201
    
    # 验证预算计算正确
    remaining_response = await client.get(f"/api/v1/budgets/{budget_id}/remaining")
    assert remaining_response.status_code == 200
    remaining_data = remaining_response.json()
    expected_remaining = 2000.00 - (50.0 * 10)
    assert abs(float(remaining_data["remaining_amount"]) - expected_remaining) < 0.01
    
    # 验证支出记录数量正确
    expenses_response = await client.get(f"/api/v1/expenses/?user_id={user_id}")
    assert expenses_response.status_code == 200
    expenses_data = expenses_response.json()
    assert len(expenses_data) == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_integration(client: AsyncClient):
    """测试错误处理集成"""
    # 测试无效用户ID的各种操作
    invalid_user_id = str(uuid.uuid4())
    
    # 1. 获取不存在用户的支出
    expenses_response = await client.get(f"/api/v1/expenses/?user_id={invalid_user_id}")
    assert expenses_response.status_code == 200
    assert expenses_response.json() == []
    
    # 2. 为不存在用户创建预算
    now = datetime.utcnow()
    budget_data = {
        "user_id": invalid_user_id,
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat()
    }
    
    budget_response = await client.post("/api/v1/budgets/", json=budget_data)
    # 应该允许创建（用户可能稍后注册）
    assert budget_response.status_code == 201
    
    # 3. 测试无效数据格式
    invalid_expense_data = {
        "user_id": "invalid-uuid",
        "amount": "not-a-number",
        "category": "invalid_category",
        "description": "",
    }
    
    invalid_expense_response = await client.post("/api/v1/expenses/", json=invalid_expense_data)
    assert invalid_expense_response.status_code == 422
    
    # 4. 测试AI服务错误处理
    ai_response = await client.post(
        "/api/v1/ai/analyze",
        json={"text": ""}  # 空文本
    )
    # 应该返回错误或请求澄清
    assert ai_response.status_code in [200, 400, 422]
    
    # 5. 测试群组权限错误
    group_data = {
        "name": "测试群组",
        "creator_id": invalid_user_id,
        "group_type": "dormitory"
    }
    
    group_response = await client.post("/api/v1/groups/", json=group_data)
    # 应该允许创建但可能有警告
    assert group_response.status_code in [201, 400]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_consistency_across_services(client: AsyncClient):
    """测试跨服务数据一致性"""
    # 创建用户
    user_data = {
        "phone_number": "+8613800138007",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 创建预算
    now = datetime.utcnow()
    budget_data = {
        "user_id": user_id,
        "category": "dining",
        "total_amount": 1000.00,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat()
    }
    
    budget_response = await client.post("/api/v1/budgets/", json=budget_data)
    assert budget_response.status_code == 201
    budget_id = budget_response.json()["id"]
    
    # 通过AI添加支出
    ai_expense_response = await client.post(
        "/api/v1/ai/create-expense",
        json={
            "user_id": user_id,
            "text": "今天午餐花了35元"
        }
    )
    assert ai_expense_response.status_code == 201
    ai_expense_data = ai_expense_response.json()
    
    # 验证支出记录已创建
    expense_id = ai_expense_data["expense_id"]
    expense_response = await client.get(f"/api/v1/expenses/{expense_id}")
    assert expense_response.status_code == 200
    expense_data = expense_response.json()
    assert expense_data["category"] == "dining"
    assert float(expense_data["amount"]) == 35.0
    
    # 验证预算已更新
    remaining_response = await client.get(f"/api/v1/budgets/{budget_id}/remaining")
    assert remaining_response.status_code == 200
    remaining_data = remaining_response.json()
    assert float(remaining_data["remaining_amount"]) == 965.0
    
    # 创建群组并添加相同支出
    group_data = {
        "name": "测试群组",
        "creator_id": user_id,
        "group_type": "dormitory"
    }
    
    group_response = await client.post("/api/v1/groups/", json=group_data)
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]
    
    # 添加群组支出
    group_expense_data = {
        "group_id": group_id,
        "payer_id": user_id,
        "amount": 100.0,
        "category": "dining",
        "description": "聚餐",
        "split_type": "equal"
    }
    
    group_expense_response = await client.post(
        f"/api/v1/groups/{group_id}/expenses",
        json=group_expense_data
    )
    assert group_expense_response.status_code == 201
    
    # 验证个人预算进一步更新
    final_remaining_response = await client.get(f"/api/v1/budgets/{budget_id}/remaining")
    assert final_remaining_response.status_code == 200
    final_remaining_data = final_remaining_response.json()
    assert float(final_remaining_data["remaining_amount"]) == 865.0  # 1000 - 35 - 100
    
    # 验证所有相关数据的一致性
    all_expenses_response = await client.get(f"/api/v1/expenses/?user_id={user_id}")
    assert all_expenses_response.status_code == 200
    all_expenses_data = all_expenses_response.json()
    
    total_personal_expenses = sum(float(exp["amount"]) for exp in all_expenses_data)
    assert total_personal_expenses == 135.0  # 35 + 100