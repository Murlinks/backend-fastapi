"""
AI服务测试
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    
from decimal import Decimal


def test_ai_service_import():
    """测试AI服务可以正常导入"""
    from app.services.ai_service import ai_service
    assert ai_service is not None


def test_multimodal_service_import():
    """测试多模态服务可以正常导入"""
    from app.services.multimodal_service import multimodal_processor
    assert multimodal_processor is not None


def test_emoji_parsing():
    """测试表情符号解析"""
    from app.services.multimodal_service import multimodal_processor
    
    # 测试餐饮类表情
    result = multimodal_processor.parse_emoji_input("🍔")
    assert result["success"] is True
    assert result["category"] == "dining"
    assert result["description"] == "汉堡"
    
    # 测试交通类表情
    result = multimodal_processor.parse_emoji_input("🚇")
    assert result["success"] is True
    assert result["category"] == "transportation"
    assert result["description"] == "地铁"
    
    # 测试未知表情
    result = multimodal_processor.parse_emoji_input("🤔")
    assert result["success"] is False
    assert result["needs_clarification"] is True


def test_gesture_parsing():
    """测试手势解析"""
    from app.services.multimodal_service import multimodal_processor
    
    # 测试有效手势
    result = multimodal_processor.parse_gesture_input("swipe_left")
    assert result["success"] is True
    assert result["action"] == "delete_last_expense"
    
    # 测试无效手势
    result = multimodal_processor.parse_gesture_input("invalid_gesture")
    assert result["success"] is False


def test_amount_extraction():
    """测试金额提取"""
    from app.services.ai_service import ai_service
    
    # 测试各种金额格式
    assert ai_service._extract_amount_regex("买奶茶15元") == Decimal("15")
    assert ai_service._extract_amount_regex("花了25.5") == Decimal("25.5")
    assert ai_service._extract_amount_regex("午餐30块") == Decimal("30")


def test_category_by_rules():
    """测试规则分类"""
    from app.services.ai_service import ai_service
    
    # 测试餐饮分类
    category, confidence = ai_service._categorize_by_rules("买奶茶")
    assert category == "dining"
    assert confidence > 0.5
    
    # 测试交通分类
    category, confidence = ai_service._categorize_by_rules("坐地铁")
    assert category == "transportation"
    assert confidence > 0.5


def test_multimodal_combine():
    """测试多模态输入合并"""
    from app.services.multimodal_service import multimodal_processor
    
    # 模拟表情结果
    emoji_result = {
        "success": True,
        "category": "dining",
        "description": "奶茶",
        "suggested_amount": 15.0,
        "confidence": 0.8
    }
    
    # 合并输入
    combined = multimodal_processor.combine_multimodal_inputs(
        text="今天买了",
        emoji_result=emoji_result
    )
    
    assert combined["category"] == "dining"
    assert combined["description"] == "奶茶"
    assert combined["suggested_amount"] == 15.0


if __name__ == "__main__":
    # 运行基本测试
    test_ai_service_import()
    test_multimodal_service_import()
    test_emoji_parsing()
    test_gesture_parsing()
    test_amount_extraction()
    test_category_by_rules()
    test_multimodal_combine()
    print("所有测试通过！")
