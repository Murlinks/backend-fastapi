"""
多模态输入处理服务
Requirements: 1.1, 1.3, 1.5
"""
import base64
import logging
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class GestureType(str, Enum):
    """手势类型"""
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    TAP = "tap"
    LONG_PRESS = "long_press"
    DOUBLE_TAP = "double_tap"


class MultiModalProcessor:
    """多模态输入处理器"""
    
    def __init__(self):
        # 表情符号映射表
        self.emoji_mappings = {
            # 餐饮类
            "🍔": {"category": "dining", "description": "汉堡", "typical_amount": 25.0},
            "🍕": {"category": "dining", "description": "披萨", "typical_amount": 40.0},
            "🍜": {"category": "dining", "description": "面条", "typical_amount": 15.0},
            "🍱": {"category": "dining", "description": "便当", "typical_amount": 20.0},
            "🍛": {"category": "dining", "description": "咖喱饭", "typical_amount": 25.0},
            "🍝": {"category": "dining", "description": "意大利面", "typical_amount": 35.0},
            "🍣": {"category": "dining", "description": "寿司", "typical_amount": 50.0},
            "🍰": {"category": "dining", "description": "蛋糕", "typical_amount": 30.0},
            "☕": {"category": "dining", "description": "咖啡", "typical_amount": 20.0},
            "🧋": {"category": "dining", "description": "奶茶", "typical_amount": 15.0},
            "🍺": {"category": "dining", "description": "啤酒", "typical_amount": 15.0},
            
            # 交通类
            "🚇": {"category": "transportation", "description": "地铁", "typical_amount": 5.0},
            "🚌": {"category": "transportation", "description": "公交", "typical_amount": 2.0},
            "🚗": {"category": "transportation", "description": "打车", "typical_amount": 25.0},
            "🚕": {"category": "transportation", "description": "出租车", "typical_amount": 30.0},
            "🚄": {"category": "transportation", "description": "高铁", "typical_amount": 200.0},
            "✈️": {"category": "transportation", "description": "飞机", "typical_amount": 800.0},
            "🚲": {"category": "transportation", "description": "共享单车", "typical_amount": 2.0},
            "⛽": {"category": "transportation", "description": "加油", "typical_amount": 200.0},
            
            # 娱乐类
            "🎬": {"category": "entertainment", "description": "电影", "typical_amount": 40.0},
            "🎮": {"category": "entertainment", "description": "游戏", "typical_amount": 50.0},
            "🎤": {"category": "entertainment", "description": "KTV", "typical_amount": 80.0},
            "🎪": {"category": "entertainment", "description": "演出", "typical_amount": 150.0},
            "🎨": {"category": "entertainment", "description": "艺术展", "typical_amount": 60.0},
            "🎭": {"category": "entertainment", "description": "戏剧", "typical_amount": 100.0},
            "🎯": {"category": "entertainment", "description": "娱乐活动", "typical_amount": 50.0},
            
            # 购物类
            "🛍️": {"category": "shopping", "description": "购物", "typical_amount": 100.0},
            "👕": {"category": "shopping", "description": "衣服", "typical_amount": 200.0},
            "👗": {"category": "shopping", "description": "裙子", "typical_amount": 250.0},
            "👟": {"category": "shopping", "description": "鞋子", "typical_amount": 300.0},
            "👜": {"category": "shopping", "description": "包包", "typical_amount": 400.0},
            "💄": {"category": "shopping", "description": "化妆品", "typical_amount": 150.0},
            "📱": {"category": "shopping", "description": "手机", "typical_amount": 3000.0},
            "💻": {"category": "shopping", "description": "电脑", "typical_amount": 5000.0},
            "📚": {"category": "shopping", "description": "书籍", "typical_amount": 50.0},
            
            # 医疗/紧急类
            "💊": {"category": "emergency", "description": "药品", "typical_amount": 30.0},
            "🏥": {"category": "emergency", "description": "医院", "typical_amount": 200.0},
            "🚑": {"category": "emergency", "description": "急救", "typical_amount": 500.0},
            "🔧": {"category": "emergency", "description": "维修", "typical_amount": 100.0},
            
            # 情感表情（用于情感分析）
            "😊": {"emotion": "happy", "stress_level": 0.1},
            "😢": {"emotion": "sad", "stress_level": 0.6},
            "😰": {"emotion": "anxious", "stress_level": 0.8},
            "😤": {"emotion": "stressed", "stress_level": 0.9},
            "😔": {"emotion": "guilty", "stress_level": 0.5},
            "😌": {"emotion": "neutral", "stress_level": 0.2},
        }
        
        # 手势操作映射
        self.gesture_actions = {
            GestureType.SWIPE_LEFT: "delete_last_expense",
            GestureType.SWIPE_RIGHT: "confirm_expense",
            GestureType.SWIPE_UP: "show_budget",
            GestureType.SWIPE_DOWN: "show_history",
            GestureType.TAP: "select",
            GestureType.LONG_PRESS: "edit",
            GestureType.DOUBLE_TAP: "quick_add"
        }
    
    def parse_emoji_input(self, emoji: str) -> Dict[str, Any]:
        """
        解析表情符号输入
        Requirements: 1.3
        
        Args:
            emoji: 表情符号字符串
        
        Returns:
            解析结果，包含类别、描述、典型金额等
        """
        if not emoji:
            return {
                "success": False,
                "message": "表情符号为空"
            }
        
        # 查找表情符号映射
        emoji_info = self.emoji_mappings.get(emoji)
        
        if not emoji_info:
            logger.warning(f"未识别的表情符号: {emoji}")
            return {
                "success": False,
                "message": f"抱歉，我还不认识这个表情符号 {emoji}",
                "needs_clarification": True,
                "clarification_question": "请用文字描述一下这笔支出？"
            }
        
        # 区分支出类表情和情感类表情
        if "category" in emoji_info:
            return {
                "success": True,
                "category": emoji_info["category"],
                "description": emoji_info["description"],
                "suggested_amount": emoji_info["typical_amount"],
                "confidence": 0.8,
                "needs_clarification": True,
                "clarification_question": f"这笔{emoji_info['description']}花了多少钱？"
            }
        elif "emotion" in emoji_info:
            return {
                "success": True,
                "type": "emotion",
                "emotion": emoji_info["emotion"],
                "stress_level": emoji_info["stress_level"],
                "message": "我感受到了您的情绪，请继续告诉我支出信息"
            }
        
        return {
            "success": False,
            "message": "无法解析表情符号"
        }
    
    def parse_gesture_input(self, gesture: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        解析手势输入
        Requirements: 1.4
        
        Args:
            gesture: 手势类型
            context: 上下文信息
        
        Returns:
            手势操作结果
        """
        try:
            gesture_type = GestureType(gesture)
        except ValueError:
            logger.warning(f"未识别的手势: {gesture}")
            return {
                "success": False,
                "message": f"未识别的手势: {gesture}"
            }
        
        action = self.gesture_actions.get(gesture_type)
        
        if not action:
            return {
                "success": False,
                "message": "该手势暂不支持"
            }
        
        return {
            "success": True,
            "action": action,
            "gesture_type": gesture_type.value,
            "message": f"执行操作: {action}"
        }
    
    async def process_voice_input(self, voice_data: str) -> Dict[str, Any]:
        """
        处理语音输入
        Requirements: 1.1
        
        Args:
            voice_data: Base64编码的音频数据
        
        Returns:
            语音识别结果
        """
        if not voice_data:
            return {
                "success": False,
                "message": "语音数据为空"
            }
        
        try:
            # 验证Base64格式
            audio_bytes = base64.b64decode(voice_data)
            audio_size = len(audio_bytes)
            
            logger.info(f"接收到语音数据，大小: {audio_size} bytes")
            
            # TODO: 集成真实的语音识别服务
            # 这里应该调用阿里云、腾讯云或其他语音识别API
            # 示例：
            # text = await speech_recognition_service.recognize(audio_bytes)
            
            # 目前返回模拟结果
            return {
                "success": True,
                "text": "",  # 实际应该是识别出的文本
                "confidence": 0.0,
                "message": "语音识别功能待集成，请使用文字输入",
                "needs_text_fallback": True
            }
            
        except Exception as e:
            logger.error(f"处理语音输入失败: {e}")
            return {
                "success": False,
                "message": "语音处理失败，请使用文字输入",
                "error": str(e)
            }
    
    def combine_multimodal_inputs(
        self,
        text: Optional[str] = None,
        voice_result: Optional[Dict[str, Any]] = None,
        emoji_result: Optional[Dict[str, Any]] = None,
        gesture_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        合并多模态输入结果
        Requirements: 1.1, 1.3
        
        Args:
            text: 文本输入
            voice_result: 语音识别结果
            emoji_result: 表情解析结果
            gesture_result: 手势解析结果
        
        Returns:
            合并后的输入信息
        """
        combined = {
            "text": text or "",
            "category": None,
            "description": "",
            "suggested_amount": None,
            "emotion": None,
            "stress_level": 0.0,
            "action": None,
            "confidence": 0.0,
            "needs_clarification": False,
            "clarification_question": None
        }
        
        # 合并语音识别结果
        if voice_result and voice_result.get("success"):
            voice_text = voice_result.get("text", "")
            if voice_text:
                combined["text"] = f"{combined['text']} {voice_text}".strip()
                combined["confidence"] = max(combined["confidence"], voice_result.get("confidence", 0.0))
        
        # 合并表情符号结果
        if emoji_result and emoji_result.get("success"):
            if emoji_result.get("type") == "emotion":
                combined["emotion"] = emoji_result.get("emotion")
                combined["stress_level"] = emoji_result.get("stress_level", 0.0)
            else:
                combined["category"] = emoji_result.get("category")
                combined["description"] = emoji_result.get("description", "")
                combined["suggested_amount"] = emoji_result.get("suggested_amount")
                combined["confidence"] = max(combined["confidence"], emoji_result.get("confidence", 0.0))
                
                if emoji_result.get("needs_clarification"):
                    combined["needs_clarification"] = True
                    combined["clarification_question"] = emoji_result.get("clarification_question")
        
        # 合并手势操作
        if gesture_result and gesture_result.get("success"):
            combined["action"] = gesture_result.get("action")
        
        return combined
    
    def validate_multimodal_input(self, combined_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证多模态输入的完整性
        Requirements: 1.5
        
        Args:
            combined_input: 合并后的输入
        
        Returns:
            验证结果和澄清问题
        """
        validation_result = {
            "is_valid": True,
            "missing_fields": [],
            "clarification_questions": []
        }
        
        # 检查是否有文本或描述
        if not combined_input.get("text") and not combined_input.get("description"):
            validation_result["is_valid"] = False
            validation_result["missing_fields"].append("description")
            validation_result["clarification_questions"].append("请描述一下这笔支出")
        
        # 检查是否有金额信息
        if not combined_input.get("suggested_amount"):
            validation_result["missing_fields"].append("amount")
            validation_result["clarification_questions"].append("这笔支出的金额是多少？")
        
        # 检查是否有分类信息
        if not combined_input.get("category"):
            validation_result["missing_fields"].append("category")
            # 如果有描述，可以尝试自动分类，不一定需要澄清
        
        return validation_result


# 全局多模态处理器实例
multimodal_processor = MultiModalProcessor()
