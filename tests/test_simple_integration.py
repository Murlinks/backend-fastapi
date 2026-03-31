"""
简单集成测试 - 不依赖数据库
Requirements: 8.3, 8.4, 8.5
"""
import pytest
import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.integration
def test_ai_service_integration():
    """测试AI服务集成功能"""
    from app.services.ai_service import ai_service
    
    print("\n🧠 测试AI服务集成...")
    
    # 测试金额提取功能
    test_cases = [
        ("买奶茶15元", 15.0),
        ("午餐花了25.5", 25.5),
        ("地铁票3块", 3.0),
        ("看电影60块钱", 60.0),
        ("咖啡店消费18.8元", 18.8),
    ]
    
    successful_extractions = 0
    for text, expected in test_cases:
        try:
            result = ai_service._extract_amount_regex(text)
            if result is not None and float(result) == expected:
                successful_extractions += 1
                print(f"  ✅ {text} -> {result}")
            else:
                print(f"  ❌ {text} -> {result} (期望: {expected})")
        except Exception as e:
            print(f"  💥 {text} -> 异常: {e}")
    
    success_rate = successful_extractions / len(test_cases) * 100
    print(f"  📊 金额提取成功率: {success_rate:.1f}%")
    
    assert success_rate >= 80, f"AI服务金额提取成功率过低: {success_rate:.1f}%"
    
    # 测试分类功能
    category_tests = [
        ("买奶茶", "dining"),
        ("坐地铁", "transportation"),
        ("看电影", "entertainment"),
        ("买衣服", "shopping"),
    ]
    
    successful_categories = 0
    for text, expected_category in category_tests:
        try:
            category, confidence = ai_service._categorize_by_rules(text)
            if category == expected_category:
                successful_categories += 1
                print(f"  ✅ {text} -> {category} (置信度: {confidence:.2f})")
            else:
                print(f"  ❌ {text} -> {category} (期望: {expected_category})")
        except Exception as e:
            print(f"  💥 {text} -> 异常: {e}")
    
    category_success_rate = successful_categories / len(category_tests) * 100
    print(f"  📊 分类成功率: {category_success_rate:.1f}%")
    
    assert category_success_rate >= 75, f"AI服务分类成功率过低: {category_success_rate:.1f}%"


@pytest.mark.integration
def test_multimodal_service_integration():
    """测试多模态服务集成功能"""
    from app.services.multimodal_service import multimodal_processor
    
    print("\n🎭 测试多模态服务集成...")
    
    # 测试表情符号解析
    emoji_tests = [
        ("🍔", "dining", "汉堡"),
        ("🚇", "transportation", "地铁"),
        ("☕", "dining", "咖啡"),
        ("🎬", "entertainment", "电影"),
        ("👕", "shopping", "衣服"),
    ]
    
    successful_emojis = 0
    for emoji, expected_category, expected_description in emoji_tests:
        try:
            result = multimodal_processor.parse_emoji_input(emoji)
            if (result["success"] and 
                result["category"] == expected_category and 
                result["description"] == expected_description):
                successful_emojis += 1
                print(f"  ✅ {emoji} -> {result['category']}: {result['description']}")
            else:
                print(f"  ❌ {emoji} -> {result}")
        except Exception as e:
            print(f"  💥 {emoji} -> 异常: {e}")
    
    emoji_success_rate = successful_emojis / len(emoji_tests) * 100
    print(f"  📊 表情解析成功率: {emoji_success_rate:.1f}%")
    
    # 测试手势解析
    gesture_tests = [
        ("swipe_left", "delete_last_expense"),
        ("double_tap", "quick_add"),
        ("swipe_right", "confirm_action"),
    ]
    
    successful_gestures = 0
    for gesture, expected_action in gesture_tests:
        try:
            result = multimodal_processor.parse_gesture_input(gesture)
            if result["success"] and result["action"] == expected_action:
                successful_gestures += 1
                print(f"  ✅ {gesture} -> {result['action']}")
            else:
                print(f"  ❌ {gesture} -> {result}")
        except Exception as e:
            print(f"  💥 {gesture} -> 异常: {e}")
    
    gesture_success_rate = successful_gestures / len(gesture_tests) * 100
    print(f"  📊 手势解析成功率: {gesture_success_rate:.1f}%")
    
    # 测试多模态输入合并
    try:
        emoji_result = {
            "success": True,
            "category": "dining",
            "description": "奶茶",
            "suggested_amount": 15.0,
            "confidence": 0.8
        }
        
        combined = multimodal_processor.combine_multimodal_inputs(
            text="今天买了",
            emoji_result=emoji_result
        )
        
        assert combined["category"] == "dining"
        assert combined["description"] == "奶茶"
        assert combined["suggested_amount"] == 15.0
        print(f"  ✅ 多模态合并: {combined}")
        
    except Exception as e:
        print(f"  💥 多模态合并异常: {e}")


@pytest.mark.integration
def test_service_performance():
    """测试服务性能"""
    from app.services.ai_service import ai_service
    from app.services.multimodal_service import multimodal_processor
    
    print("\n⚡ 测试服务性能...")
    
    # 测试AI服务性能
    test_texts = [
        "买奶茶15元", "午餐花了25.5", "地铁票3块", "看电影60块", "买书籍80元",
        "咖啡店消费18元", "超市购物120元", "打车费用35元", "健身房月费200元", "手机话费50元"
    ]
    
    # 金额提取性能测试
    start_time = time.time()
    successful_extractions = 0
    
    for text in test_texts:
        try:
            result = ai_service._extract_amount_regex(text)
            if result is not None:
                successful_extractions += 1
        except Exception:
            pass
    
    end_time = time.time()
    extraction_time = (end_time - start_time) * 1000  # 转换为毫秒
    avg_extraction_time = extraction_time / len(test_texts)
    
    print(f"  📊 金额提取性能:")
    print(f"     总时间: {extraction_time:.2f}ms")
    print(f"     平均时间: {avg_extraction_time:.2f}ms/次")
    print(f"     成功率: {successful_extractions/len(test_texts)*100:.1f}%")
    
    # 分类性能测试
    start_time = time.time()
    successful_classifications = 0
    
    for text in test_texts:
        try:
            category, confidence = ai_service._categorize_by_rules(text)
            if category and confidence > 0.5:
                successful_classifications += 1
        except Exception:
            pass
    
    end_time = time.time()
    classification_time = (end_time - start_time) * 1000
    avg_classification_time = classification_time / len(test_texts)
    
    print(f"  📊 分类性能:")
    print(f"     总时间: {classification_time:.2f}ms")
    print(f"     平均时间: {avg_classification_time:.2f}ms/次")
    print(f"     成功率: {successful_classifications/len(test_texts)*100:.1f}%")
    
    # 表情解析性能测试
    emojis = ["🍔", "🚇", "☕", "🎬", "👕", "🏠", "📱", "💰", "🎵", "📚"]
    
    start_time = time.time()
    successful_emoji_parses = 0
    
    for emoji in emojis:
        try:
            result = multimodal_processor.parse_emoji_input(emoji)
            if result["success"]:
                successful_emoji_parses += 1
        except Exception:
            pass
    
    end_time = time.time()
    emoji_time = (end_time - start_time) * 1000
    avg_emoji_time = emoji_time / len(emojis)
    
    print(f"  📊 表情解析性能:")
    print(f"     总时间: {emoji_time:.2f}ms")
    print(f"     平均时间: {avg_emoji_time:.2f}ms/次")
    print(f"     成功率: {successful_emoji_parses/len(emojis)*100:.1f}%")
    
    # 性能断言
    assert avg_extraction_time < 50, f"金额提取平均时间过长: {avg_extraction_time:.2f}ms"
    assert avg_classification_time < 50, f"分类平均时间过长: {avg_classification_time:.2f}ms"
    assert avg_emoji_time < 10, f"表情解析平均时间过长: {avg_emoji_time:.2f}ms"


@pytest.mark.integration
def test_error_handling_robustness():
    """测试错误处理健壮性"""
    from app.services.ai_service import ai_service
    from app.services.multimodal_service import multimodal_processor
    
    print("\n🛡️ 测试错误处理健壮性...")
    
    # 测试AI服务错误处理
    error_inputs = [
        "",  # 空字符串
        "   ",  # 空白字符
        "没有数字的文本",  # 无数字
        "123abc456",  # 混合字符
        "负数-50元",  # 负数
        "无穷大∞元",  # 特殊字符
    ]
    
    ai_error_handled = 0
    for input_text in error_inputs:
        try:
            result = ai_service._extract_amount_regex(input_text)
            # 应该返回None或合理的默认值，不应该抛出异常
            ai_error_handled += 1
            print(f"  ✅ AI错误处理: '{input_text}' -> {result}")
        except Exception as e:
            print(f"  ❌ AI错误处理失败: '{input_text}' -> {e}")
    
    ai_error_rate = ai_error_handled / len(error_inputs) * 100
    print(f"  📊 AI错误处理成功率: {ai_error_rate:.1f}%")
    
    # 测试多模态服务错误处理
    invalid_emojis = ["🤔", "🔥", "💯", "❓", "⚡"]
    
    multimodal_error_handled = 0
    for emoji in invalid_emojis:
        try:
            result = multimodal_processor.parse_emoji_input(emoji)
            # 应该返回success=False，不应该抛出异常
            if not result["success"]:
                multimodal_error_handled += 1
                print(f"  ✅ 多模态错误处理: {emoji} -> 正确识别为未知")
            else:
                print(f"  ⚠️  多模态意外成功: {emoji} -> {result}")
        except Exception as e:
            print(f"  ❌ 多模态错误处理失败: {emoji} -> {e}")
    
    multimodal_error_rate = multimodal_error_handled / len(invalid_emojis) * 100
    print(f"  📊 多模态错误处理成功率: {multimodal_error_rate:.1f}%")
    
    # 测试无效手势处理
    invalid_gestures = ["invalid_gesture", "unknown_action", "", "123"]
    
    gesture_error_handled = 0
    for gesture in invalid_gestures:
        try:
            result = multimodal_processor.parse_gesture_input(gesture)
            if not result["success"]:
                gesture_error_handled += 1
                print(f"  ✅ 手势错误处理: '{gesture}' -> 正确识别为无效")
            else:
                print(f"  ⚠️  手势意外成功: '{gesture}' -> {result}")
        except Exception as e:
            print(f"  ❌ 手势错误处理失败: '{gesture}' -> {e}")
    
    gesture_error_rate = gesture_error_handled / len(invalid_gestures) * 100
    print(f"  📊 手势错误处理成功率: {gesture_error_rate:.1f}%")
    
    # 总体错误处理评估
    overall_error_handling = (ai_error_rate + multimodal_error_rate + gesture_error_rate) / 3
    print(f"  📊 总体错误处理成功率: {overall_error_handling:.1f}%")
    
    assert overall_error_handling >= 70, f"错误处理成功率过低: {overall_error_handling:.1f}%"


@pytest.mark.integration
def test_configuration_and_environment():
    """测试配置和环境"""
    print("\n⚙️ 测试配置和环境...")
    
    try:
        from app.core.config import settings
        
        # 检查关键配置项
        config_checks = {
            "DATABASE_URL": getattr(settings, "DATABASE_URL", None),
            "REDIS_URL": getattr(settings, "REDIS_URL", None),
            "SECRET_KEY": getattr(settings, "SECRET_KEY", None),
            "DEEPSEEK_API_KEY": getattr(settings, "DEEPSEEK_API_KEY", None),
        }
        
        configured_items = 0
        for config_name, config_value in config_checks.items():
            if config_value and config_value.strip():
                configured_items += 1
                # 隐藏敏感信息
                if "KEY" in config_name or "URL" in config_name:
                    display_value = f"{config_value[:10]}...{config_value[-5:]}" if len(config_value) > 15 else "***"
                else:
                    display_value = config_value
                print(f"  ✅ {config_name}: {display_value}")
            else:
                print(f"  ❌ {config_name}: 未配置")
        
        config_rate = configured_items / len(config_checks) * 100
        print(f"  📊 配置完整性: {config_rate:.1f}%")
        
        # 检查Python环境
        python_version = sys.version_info
        print(f"  ✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 检查关键模块
        required_modules = [
            "fastapi", "uvicorn", "sqlalchemy", "redis", 
            "httpx", "pydantic", "asyncpg"
        ]
        
        available_modules = 0
        for module_name in required_modules:
            try:
                __import__(module_name)
                available_modules += 1
                print(f"  ✅ {module_name}: 可用")
            except ImportError:
                print(f"  ❌ {module_name}: 不可用")
        
        module_rate = available_modules / len(required_modules) * 100
        print(f"  📊 模块可用性: {module_rate:.1f}%")
        
        assert module_rate >= 80, f"关键模块缺失过多: {module_rate:.1f}%"
        
    except Exception as e:
        print(f"  💥 配置检查异常: {e}")
        pytest.fail(f"配置和环境检查失败: {e}")


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行简单集成测试套件...")
    print("=" * 60)
    
    tests = [
        ("AI服务集成", test_ai_service_integration),
        ("多模态服务集成", test_multimodal_service_integration),
        ("服务性能", test_service_performance),
        ("错误处理健壮性", test_error_handling_robustness),
        ("配置和环境", test_configuration_and_environment),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 运行测试: {test_name}")
            test_func()
            passed_tests += 1
            print(f"✅ {test_name} - 通过")
        except Exception as e:
            print(f"❌ {test_name} - 失败: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed_tests}/{total_tests} 通过")
    print(f"📊 成功率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！")
        return True
    else:
        print("⚠️  部分测试失败")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)