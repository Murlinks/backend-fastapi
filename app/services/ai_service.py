"""
AI服务 - DeepSeek API集成和自然语言处理
Requirements: 1.2, 2.1, 1.1, 1.3, 1.5, 5.1, 5.2, 5.3, 5.4, 5.5
"""
import re
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """AI服务类 - 集成DeepSeek大模型"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # 支出类别映射
        self.categories = {
            "dining": ["餐饮", "吃饭", "午餐", "晚餐", "早餐", "奶茶", "咖啡", "外卖", "饭店"],
            "transportation": ["交通", "地铁", "公交", "打车", "滴滴", "出租车", "火车", "飞机"],
            "entertainment": ["娱乐", "电影", "游戏", "KTV", "演唱会", "旅游", "景点"],
            "shopping": ["购物", "衣服", "鞋子", "化妆品", "电子产品", "书籍", "日用品"],
            "emergency": ["紧急", "医疗", "药品", "维修", "应急"]
        }
        
        # 导入多模态处理器（延迟导入避免循环依赖）
        self._multimodal_processor = None
        self._emotion_service = None
        self._recommendation_service = None
        self._peer_expression_service = None
    
    @property
    def multimodal_processor(self):
        """延迟加载多模态处理器"""
        if self._multimodal_processor is None:
            from app.services.multimodal_service import multimodal_processor
            self._multimodal_processor = multimodal_processor
        return self._multimodal_processor
    
    @property
    def emotion_service(self):
        """延迟加载情感分析服务"""
        if self._emotion_service is None:
            from app.services.emotion_service import emotion_service
            self._emotion_service = emotion_service
        return self._emotion_service
    
    @property
    def recommendation_service(self):
        """延迟加载建议服务"""
        if self._recommendation_service is None:
            from app.services.recommendation_service import recommendation_service
            self._recommendation_service = recommendation_service
        return self._recommendation_service
    
    @property
    def peer_expression_service(self):
        """延迟加载同龄人化表达服务"""
        if self._peer_expression_service is None:
            from app.services.peer_expression_service import peer_expression_service
            self._peer_expression_service = peer_expression_service
        return self._peer_expression_service
    
    async def extract_expense_info(
        self,
        text: str,
        voice_data: Optional[str] = None,
        emoji: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从多模态输入中提取支出信息
        Requirements: 1.2, 2.1
        
        Args:
            text: 文本输入
            voice_data: 语音数据（Base64编码）
            emoji: 表情符号
        
        Returns:
            包含金额、分类、描述等信息的字典
        """
        try:
            # 如果有语音数据，先转换为文本
            if voice_data and not text:
                voice_result = await self.multimodal_processor.process_voice_input(voice_data)
                if voice_result.get("success") and voice_result.get("text"):
                    text = voice_result["text"]
            
            # 如果有表情符号，解析其含义
            emoji_info = None
            if emoji:
                emoji_result = self.multimodal_processor.parse_emoji_input(emoji)
                if emoji_result.get("success"):
                    emoji_info = emoji_result
                    # 如果表情提供了描述，添加到文本中
                    if emoji_result.get("description"):
                        text = f"{text} {emoji_result['description']}" if text else emoji_result["description"]
            
            # 使用正则表达式快速提取金额
            amount = self._extract_amount_regex(text)
            
            # 如果表情符号提供了建议金额且文本中没有金额
            if amount is None and emoji_info and emoji_info.get("suggested_amount"):
                amount = Decimal(str(emoji_info["suggested_amount"]))
            
            # 使用规则引擎快速分类
            category, confidence = self._categorize_by_rules(text)
            
            # 如果表情符号提供了分类，优先使用
            if emoji_info and emoji_info.get("category"):
                category = emoji_info["category"]
                confidence = max(confidence, emoji_info.get("confidence", 0.8))
            
            # 如果置信度低，使用DeepSeek API进行深度分析
            if confidence < 0.7 or amount is None:
                ai_result = await self._extract_with_deepseek(text)
                if ai_result:
                    amount = ai_result.get("amount") or amount
                    category = ai_result.get("category") or category
                    confidence = ai_result.get("confidence", confidence)
            
            # 判断是否需要澄清
            needs_clarification = False
            clarification_question = None
            
            if amount is None:
                needs_clarification = True
                clarification_question = "请问这笔支出的具体金额是多少？"
            elif confidence < 0.6:
                needs_clarification = True
                clarification_question = f"这笔支出是属于{category}类别吗？"
            
            return {
                "amount": float(amount) if amount else None,
                "category": category,
                "description": text,
                "confidence": confidence,
                "needs_clarification": needs_clarification,
                "clarification_question": clarification_question
            }
            
        except Exception as e:
            logger.error(f"提取支出信息失败: {e}")
            return {
                "amount": None,
                "category": "shopping",
                "description": text or "未知支出",
                "confidence": 0.3,
                "needs_clarification": True,
                "clarification_question": "抱歉，我没有理解您的输入，请问这笔支出的金额和类别是什么？"
            }
    
    def _extract_amount_regex(self, text: str) -> Optional[Decimal]:
        """
        使用正则表达式提取金额
        Requirements: 1.2
        """
        if not text:
            return None
        
        # 匹配各种金额格式
        patterns = [
            r'(\d+\.?\d*)\s*元',  # 15元, 15.5元
            r'(\d+\.?\d*)\s*块',  # 15块
            r'花了?\s*(\d+\.?\d*)',  # 花了15, 花15
            r'(\d+\.?\d*)\s*rmb',  # 15rmb
            r'(\d+\.?\d*)\s*¥',  # 15¥
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = Decimal(match.group(1))
                    if 0 < amount < 1000000:  # 合理范围检查
                        return amount
                except:
                    continue
        
        return None
    
    def _categorize_by_rules(self, text: str) -> Tuple[str, float]:
        """
        使用规则引擎进行分类
        Requirements: 2.1
        """
        if not text:
            return "shopping", 0.3
        
        text_lower = text.lower()
        
        # 计算每个类别的匹配分数
        scores = {}
        for category, keywords in self.categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[category] = score
        
        if not scores:
            return "shopping", 0.3
        
        # 选择得分最高的类别
        best_category = max(scores, key=scores.get)
        max_score = scores[best_category]
        
        # 计算置信度
        confidence = min(0.9, 0.5 + (max_score * 0.2))
        
        return best_category, confidence
    
    async def _extract_with_deepseek(self, text: str) -> Optional[Dict[str, Any]]:
        """
        使用DeepSeek API进行深度分析
        Requirements: 1.2, 2.1
        """
        if not self.api_key:
            logger.warning("DeepSeek API密钥未配置，跳过AI分析")
            return None
        
        try:
            prompt = f"""
请从以下文本中提取支出信息，返回JSON格式：
文本：{text}

返回格式：
{{
    "amount": 金额（数字，如果无法确定则为null）,
    "category": 类别（dining/transportation/entertainment/shopping/emergency之一）,
    "confidence": 置信度（0-1之间的小数）
}}
"""
            
            response = await self.client.post(
                f"{self.api_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的财务助手，擅长从自然语言中提取支出信息。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 解析JSON响应
                parsed = json.loads(content)
                return parsed
            else:
                logger.error(f"DeepSeek API调用失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return None
    
    async def categorize_expense(
        self,
        description: str,
        amount: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        智能分类支出
        Requirements: 2.1, 2.2
        """
        # 先使用规则引擎
        category, confidence = self._categorize_by_rules(description)
        
        # 如果置信度低，使用AI增强
        if confidence < 0.7 and self.api_key:
            ai_result = await self._extract_with_deepseek(description)
            if ai_result and ai_result.get("category"):
                category = ai_result["category"]
                confidence = ai_result.get("confidence", confidence)
        
        # 提供备选分类
        alternatives = []
        if confidence < 0.8:
            all_categories = list(self.categories.keys())
            alternatives = [cat for cat in all_categories if cat != category][:2]
        
        return {
            "category": category,
            "confidence": confidence,
            "alternatives": alternatives,
            "needs_clarification": confidence < 0.6
        }
    
    async def handle_clarification(
        self,
        original_input: str,
        clarification_response: str,
        previous_extraction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理用户的澄清回答
        Requirements: 1.5
        """
        # 合并原始输入和澄清回答
        combined_text = f"{original_input} {clarification_response}"
        
        # 重新提取信息
        result = await self.extract_expense_info(combined_text)
        
        # 如果之前已经有部分信息，保留它们
        if previous_extraction.get("amount") and not result.get("amount"):
            result["amount"] = previous_extraction["amount"]
        
        if previous_extraction.get("category") and result["confidence"] < 0.5:
            result["category"] = previous_extraction["category"]
        
        return result
    
    async def generate_conversation_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成对话响应（使用同龄人化表达）
        Requirements: 1.2
        """
        # 如果有明确的场景和上下文，使用模板生成响应
        if context and context.get("scenario"):
            from app.services.peer_expression_service import ScenarioType
            scenario = context.get("scenario")
            data = context.get("data", {})
            
            # 尝试使用同龄人化模板生成响应
            try:
                scenario_type = ScenarioType(scenario)
                return self.peer_expression_service.generate_response(
                    scenario=scenario_type,
                    data=data,
                    user_preference=context.get("user_preference")
                )
            except (ValueError, AttributeError):
                # 如果场景不匹配，继续使用AI生成
                pass
        
        if not self.api_key:
            # 降级到同龄人化简单响应
            return self.peer_expression_service.generate_response(
                scenario=ScenarioType.RECORD_SUCCESS,
                data={"amount": context.get("amount", ""), "category": context.get("category", "支出")} if context else {}
            ) if context else "okk，已记录 ✓"
        
        try:
            # 使用同龄人化系统提示词
            system_prompt = self.peer_expression_service.get_system_prompt()
            
            # 如果有场景，增强提示词
            if context and context.get("scenario"):
                from app.services.peer_expression_service import ScenarioType
                try:
                    scenario_type = ScenarioType(context.get("scenario"))
                    system_prompt = self.peer_expression_service.enhance_ai_prompt(user_message, scenario_type)
                except ValueError:
                    pass
            
            # 构建对话历史
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 添加历史对话
            for msg in conversation_history[-5:]:  # 只保留最近5条
                messages.append(msg)
            
            # 添加当前消息
            messages.append({"role": "user", "content": user_message})
            
            response = await self.client.post(
                f"{self.api_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.8,  # 稍微提高温度，增加表达多样性
                    "max_tokens": 150
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                return ai_response
            else:
                # API失败时降级到模板响应
                return self.peer_expression_service.generate_response(
                    scenario=ScenarioType.RECORD_SUCCESS,
                    data={"amount": context.get("amount", ""), "category": context.get("category", "支出")} if context else {}
                )
                
        except Exception as e:
            logger.error(f"生成对话响应失败: {e}")
            return "好的，我已经记录了这笔支出。"
    
    async def analyze_emotion(
        self,
        text: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析用户情感状态
        Requirements: 5.1, 5.2
        """
        try:
            return await self.emotion_service.detect_emotion(
                text=text,
                conversation_history=conversation_history,
                context=context
            )
        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            return {
                "emotion": "neutral",
                "confidence": 0.3,
                "stress_level": 0.3,
                "stress_confidence": 0.3,
                "scenario_tags": [],
                "financial_stress_detected": False,
                "emotion_description": "无法分析情感状态",
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_ai_recommendation(
        self,
        emotion_data: Dict[str, Any],
        budget_context: Dict[str, Any],
        expense_context: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成AI建议
        Requirements: 5.3, 5.4, 5.5
        """
        try:
            return await self.recommendation_service.generate_recommendation(
                emotion_data=emotion_data,
                budget_context=budget_context,
                expense_context=expense_context,
                user_profile=user_profile
            )
        except Exception as e:
            logger.error(f"生成AI建议失败: {e}")
            return {
                "recommendation_type": "budget_advice",
                "primary_message": "建议您保持理性消费，根据预算合理安排支出。",
                "detailed_advice": [
                    "记录每笔支出，了解资金流向",
                    "设置月度预算目标",
                    "为紧急情况预留资金"
                ],
                "alternatives": ["寻找更经济的替代方案"],
                "confidence": 0.6,
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def track_emotion_history(
        self,
        user_id: str,
        emotion_data: Dict[str, Any],
        db_session
    ) -> Dict[str, Any]:
        """
        跟踪用户情感历史
        Requirements: 5.1
        """
        try:
            return await self.emotion_service.track_emotion_history(
                user_id=user_id,
                emotion_data=emotion_data,
                db_session=db_session
            )
        except Exception as e:
            logger.error(f"跟踪情感历史失败: {e}")
            return {
                "emotion_recorded": False,
                "error": str(e)
            }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局AI服务实例
ai_service = AIService()
