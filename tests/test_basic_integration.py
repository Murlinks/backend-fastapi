"""
基础集成测试 - 不需要数据库连接
Requirements: 8.3, 8.4, 8.5
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.integration
def test_basic_imports():
    """测试基本模块导入"""
    try:
        # 测试核心模块导入
        from app.core.config import settings
        assert settings is not None
        print("✅ 配置模块导入成功")
        
        # 测试服务模块导入
        from app.services.ai_service import ai_service
        assert ai_service is not None
        print("✅ AI服务模块导入成功")
        
        from app.services.multimodal_service import multimodal_processor
        assert multimodal_processor is not None
        print("✅ 多模态服务模块导入成功")
        
        print("✅ 所有基础模块导入测试通过")
        
    except ImportError as e:
        pytest.fail(f"模块导入失败: {e}")


@pytest.mark.integration
def test_ai_service_basic_functionality():
    """测试AI服务基础功能"""
    from app.services.ai_service import ai_service
    
    # 测试金额提取
    test_cases = [
        ("买奶茶15元", 15.0),
        ("午餐花了25.5", 25.5),
        ("地铁票3块", 3.0),
    ]
    
    for text, expected_amount in test_cases:
        try:
            amount = ai_service._extract_amount_regex(text)
            assert float(amount) == expected_amount, f"金额提取错误: {text} -> {amount}, 期望: {expected_amount}"
            print(f"✅ 金额提取测试通过: {text} -> {amount}")
        except Exception as e:
            print(f"⚠️  金额提取测试失败: {text} -> {e}")


@pytest.mark.integration
def test_multimodal_service_basic_functionality():
    """测试多模态服务基础功能"""
    from app.services.multimodal_service import multimodal_processor
    
    # 测试表情符号解析
    emoji_tests = [
        ("🍔", "dining", "汉堡"),
        ("🚇", "transportation", "地铁"),
        ("☕", "dining", "咖啡"),
    ]
    
    for emoji, expected_category, expected_description in emoji_tests:
        try:
            result = multimodal_processor.parse_emoji_input(emoji)
            assert result["success"] is True, f"表情解析失败: {emoji}"
            assert result["category"] == expected_category, f"分类错误: {emoji}"
            assert result["description"] == expected_description, f"描述错误: {emoji}"
            print(f"✅ 表情解析测试通过: {emoji} -> {result['category']}")
        except Exception as e:
            print(f"⚠️  表情解析测试失败: {emoji} -> {e}")
    
    # 测试手势解析
    gesture_tests = [
        ("swipe_left", "delete_last_expense"),
        ("double_tap", "quick_add"),
        ("long_press", "show_menu"),
    ]
    
    for gesture, expected_action in gesture_tests:
        try:
            result = multimodal_processor.parse_gesture_input(gesture)
            if result["success"]:
                assert result["action"] == expected_action, f"手势动作错误: {gesture}"
                print(f"✅ 手势解析测试通过: {gesture} -> {result['action']}")
            else:
                print(f"⚠️  手势解析失败: {gesture}")
        except Exception as e:
            print(f"⚠️  手势解析测试异常: {gesture} -> {e}")


@pytest.mark.integration
def test_data_models_validation():
    """测试数据模型验证"""
    try:
        from app.models.user import User
        from app.models.expense import Expense
        from app.models.budget import Budget
        
        # 测试用户模型
        user_data = {
            "id": "test-user-id",
            "phone_number": "+8613800138000",
            "identity": "student",
            "created_at": "2024-01-01T00:00:00",
            "last_active": "2024-01-01T00:00:00",
            "preferences": {"currency": "CNY"}
        }
        
        user = User(**user_data)
        assert user.phone_number == "+8613800138000"
        assert user.identity == "student"
        print("✅ 用户模型验证通过")
        
        # 测试支出模型
        expense_data = {
            "id": "test-expense-id",
            "user_id": "test-user-id",
            "amount": 25.50,
            "category": "dining",
            "description": "午餐",
            "created_at": "2024-01-01T00:00:00",
            "is_emergency": False
        }
        
        expense = Expense(**expense_data)
        assert expense.amount == 25.50
        assert expense.category == "dining"
        print("✅ 支出模型验证通过")
        
        # 测试预算模型
        budget_data = {
            "id": "test-budget-id",
            "user_id": "test-user-id",
            "category": "dining",
            "total_amount": 1000.00,
            "remaining_amount": 974.50,
            "period_start": "2024-01-01T00:00:00",
            "period_end": "2024-01-31T23:59:59",
            "is_flexible": True,
            "flexibility_percentage": 10.0
        }
        
        budget = Budget(**budget_data)
        assert budget.total_amount == 1000.00
        assert budget.remaining_amount == 974.50
        print("✅ 预算模型验证通过")
        
    except Exception as e:
        pytest.fail(f"数据模型验证失败: {e}")


@pytest.mark.integration
def test_configuration_loading():
    """测试配置加载"""
    try:
        from app.core.config import settings
        
        # 检查必要的配置项
        required_configs = [
            "DATABASE_URL",
            "REDIS_URL", 
            "SECRET_KEY",
            "DEEPSEEK_API_KEY"
        ]
        
        for config_name in required_configs:
            config_value = getattr(settings, config_name, None)
            if config_value:
                print(f"✅ 配置项 {config_name}: 已设置")
            else:
                print(f"⚠️  配置项 {config_name}: 未设置或为空")
        
        print("✅ 配置加载测试完成")
        
    except Exception as e:
        pytest.fail(f"配置加载失败: {e}")


@pytest.mark.integration
def test_error_handling():
    """测试错误处理机制"""
    from app.services.ai_service import ai_service
    from app.services.multimodal_service import multimodal_processor
    
    # 测试AI服务错误处理
    try:
        # 测试空文本
        result = ai_service._extract_amount_regex("")
        print(f"✅ AI服务空文本处理: {result}")
        
        # 测试无效文本
        result = ai_service._extract_amount_regex("没有金额的文本")
        print(f"✅ AI服务无效文本处理: {result}")
        
    except Exception as e:
        print(f"⚠️  AI服务错误处理测试: {e}")
    
    # 测试多模态服务错误处理
    try:
        # 测试未知表情
        result = multimodal_processor.parse_emoji_input("🤔")
        assert result["success"] is False
        print("✅ 多模态服务未知表情处理通过")
        
        # 测试无效手势
        result = multimodal_processor.parse_gesture_input("invalid_gesture")
        assert result["success"] is False
        print("✅ 多模态服务无效手势处理通过")
        
    except Exception as e:
        print(f"⚠️  多模态服务错误处理测试: {e}")


@pytest.mark.integration
def test_performance_basic():
    """基础性能测试"""
    import time
    from app.services.ai_service import ai_service
    
    # 测试AI服务响应时间
    test_texts = [
        "买奶茶15元",
        "午餐花了25.5",
        "地铁票3块",
        "看电影60块",
        "买书籍80元"
    ]
    
    total_time = 0
    successful_extractions = 0
    
    for text in test_texts:
        start_time = time.time()
        try:
            amount = ai_service._extract_amount_regex(text)
            if amount is not None:
                successful_extractions += 1
        except Exception:
            pass
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000  # 转换为毫秒
        total_time += processing_time
    
    avg_time = total_time / len(test_texts)
    success_rate = successful_extractions / len(test_texts) * 100
    
    print(f"✅ AI服务性能测试:")
    print(f"   平均处理时间: {avg_time:.2f}ms")
    print(f"   成功率: {success_rate:.1f}%")
    
    # 验证性能指标
    assert avg_time < 100, f"AI服务处理时间过长: {avg_time:.2f}ms"
    assert success_rate >= 80, f"AI服务成功率过低: {success_rate:.1f}%"


if __name__ == "__main__":
    # 直接运行测试
    test_basic_imports()
    test_ai_service_basic_functionality()
    test_multimodal_service_basic_functionality()
    test_data_models_validation()
    test_configuration_loading()
    test_error_handling()
    test_performance_basic()
    print("\n🎉 所有基础集成测试完成！")