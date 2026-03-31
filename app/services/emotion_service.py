"""
情感分析服务 - 情感检测和分析引擎
Requirements: 5.1, 5.2
"""
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmotionState(str, Enum):
    """情感状态枚举"""
    HAPPY = "happy"
    STRESSED = "stressed"
    ANXIOUS = "anxious"
    NEUTRAL = "neutral"
    GUILTY = "guilty"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"
    RELIEVED = "relieved"


class StressLevel(str, Enum):
    """压力等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmotionAnalysisService:
    """情感分析服务类"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # 情感关键词映射
        self.emotion_keywords = {
            EmotionState.HAPPY: [
                "开心", "高兴", "快乐", "满意", "愉快", "兴奋", "爽", "棒", "好", "赞",
                "😊", "😄", "😃", "🎉", "👍", "💯"
            ],
            EmotionState.STRESSED: [
                "压力", "紧张", "焦虑", "担心", "忙", "累", "疲惫", "烦", "头疼", "崩溃",
                "😰", "😓", "😵", "🤯", "😩"
            ],
            EmotionState.ANXIOUS: [
                "焦虑", "不安", "紧张", "担心", "害怕", "恐慌", "忐忑", "纠结", "犹豫",
                "😟", "😧", "😨", "😰", "🤔"
            ],
            EmotionState.GUILTY: [
                "内疚", "后悔", "愧疚", "不应该", "浪费", "败家", "剁手", "又买了", "控制不住",
                "😔", "😞", "😢", "🤦", "💸"
            ],
            EmotionState.FRUSTRATED: [
                "烦躁", "生气", "愤怒", "郁闷", "不爽", "讨厌", "烦死了", "气死了",
                "😠", "😡", "🤬", "😤", "💢"
            ],
            EmotionState.RELIEVED: [
                "松了口气", "终于", "解脱", "轻松", "放心", "安心", "好多了",
                "😌", "😮‍💨", "🙂", "😊"
            ]
        }
        
        # 财务压力关键词
        self.financial_stress_keywords = [
            "没钱", "穷", "破产", "月光", "透支", "借钱", "欠债", "还款", "分期",
            "预算紧张", "超支", "花太多", "控制不住", "又买了", "剁手", "败家",
            "工资不够", "生活费", "房租", "学费", "医药费", "紧急", "应急"
        ]
        
        # 场景标签映射
        self.scenario_tags = {
            "期末周": ["期末", "考试", "复习", "熬夜", "图书馆", "咖啡", "提神"],
            "工作日": ["上班", "加班", "会议", "项目", "deadline", "工作餐", "通勤"],
            "周末": ["周末", "休息", "放松", "娱乐", "聚会", "约会", "购物"],
            "节假日": ["假期", "旅游", "回家", "聚餐", "礼物", "红包", "过年"],
            "生病": ["感冒", "发烧", "医院", "药", "看病", "身体不适", "休息"],
            "搬家": ["搬家", "租房", "装修", "家具", "押金", "中介费", "水电费"]
        }
    
    async def detect_emotion(
        self,
        text: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检测用户情感状态
        Requirements: 5.1
        
        Args:
            text: 用户输入文本
            conversation_history: 对话历史
            context: 上下文信息
        
        Returns:
            情感分析结果
        """
        try:
            # 1. 基于关键词的快速检测
            keyword_emotion, keyword_confidence = self._detect_emotion_by_keywords(text)
            
            # 2. 检测财务压力
            stress_level, stress_confidence = self._detect_financial_stress(text, context)
            
            # 3. 识别场景标签
            scenario_tags = self._identify_scenario_tags(text, context)
            
            # 4. 如果置信度低，使用AI增强分析
            if keyword_confidence < 0.7 and self.api_key:
                ai_result = await self._analyze_emotion_with_ai(text, conversation_history)
                if ai_result:
                    keyword_emotion = ai_result.get("emotion", keyword_emotion)
                    keyword_confidence = max(keyword_confidence, ai_result.get("confidence", 0.0))
                    stress_level = max(stress_level, ai_result.get("stress_level", stress_level))
            
            # 5. 综合分析结果
            result = {
                "emotion": keyword_emotion,
                "confidence": keyword_confidence,
                "stress_level": stress_level,
                "stress_confidence": stress_confidence,
                "scenario_tags": scenario_tags,
                "financial_stress_detected": stress_level > 0.5,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            # 6. 添加情感描述
            result["emotion_description"] = self._get_emotion_description(
                keyword_emotion, stress_level, scenario_tags
            )
            
            return result
            
        except Exception as e:
            logger.error(f"情感检测失败: {e}")
            return {
                "emotion": EmotionState.NEUTRAL,
                "confidence": 0.3,
                "stress_level": 0.3,
                "stress_confidence": 0.3,
                "scenario_tags": [],
                "financial_stress_detected": False,
                "emotion_description": "无法准确识别情感状态",
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    def _detect_emotion_by_keywords(self, text: str) -> Tuple[str, float]:
        """
        基于关键词检测情感
        Requirements: 5.1
        """
        if not text:
            return EmotionState.NEUTRAL, 0.3
        
        text_lower = text.lower()
        emotion_scores = {}
        
        # 计算每种情感的匹配分数
        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower or keyword in text:  # 支持emoji
                    score += 1
            
            if score > 0:
                emotion_scores[emotion] = score
        
        if not emotion_scores:
            return EmotionState.NEUTRAL, 0.3
        
        # 选择得分最高的情感
        best_emotion = max(emotion_scores, key=emotion_scores.get)
        max_score = emotion_scores[best_emotion]
        
        # 计算置信度
        confidence = min(0.9, 0.4 + (max_score * 0.2))
        
        return best_emotion, confidence
    
    def _detect_financial_stress(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, float]:
        """
        检测财务压力水平
        Requirements: 5.2
        """
        if not text:
            return 0.3, 0.3
        
        text_lower = text.lower()
        stress_score = 0
        
        # 检查财务压力关键词
        for keyword in self.financial_stress_keywords:
            if keyword in text_lower:
                stress_score += 1
        
        # 检查上下文中的预算信息
        if context:
            budget_info = context.get("budget_info", {})
            if budget_info:
                remaining_ratio = budget_info.get("remaining_ratio", 1.0)
                if remaining_ratio < 0.2:  # 预算剩余不足20%
                    stress_score += 2
                elif remaining_ratio < 0.5:  # 预算剩余不足50%
                    stress_score += 1
            
            # 检查是否为紧急支出
            if context.get("is_emergency", False):
                stress_score += 1
        
        # 计算压力水平 (0-1)
        stress_level = min(1.0, stress_score * 0.2)
        confidence = min(0.9, 0.5 + (stress_score * 0.1))
        
        return stress_level, confidence
    
    def _identify_scenario_tags(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        识别场景标签
        Requirements: 5.1
        """
        if not text:
            return []
        
        text_lower = text.lower()
        identified_tags = []
        
        for scenario, keywords in self.scenario_tags.items():
            for keyword in keywords:
                if keyword in text_lower:
                    identified_tags.append(scenario)
                    break
        
        # 从上下文中获取额外标签
        if context and context.get("scenario_tags"):
            identified_tags.extend(context["scenario_tags"])
        
        # 去重并返回
        return list(set(identified_tags))
    
    async def _analyze_emotion_with_ai(
        self,
        text: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用AI进行深度情感分析
        Requirements: 5.1, 5.2
        """
        if not self.api_key:
            return None
        
        try:
            # 构建分析提示
            prompt = f"""
请分析以下文本中的情感状态和财务压力水平，返回JSON格式：

文本：{text}

可选情感状态：happy, stressed, anxious, neutral, guilty, excited, frustrated, relieved

返回格式：
{{
    "emotion": "情感状态",
    "confidence": 置信度（0-1之间的小数）,
    "stress_level": 财务压力水平（0-1之间的小数）,
    "reasoning": "分析理由"
}}
"""
            
            # 添加对话历史上下文
            if conversation_history:
                recent_messages = conversation_history[-3:]  # 最近3条消息
                history_text = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in recent_messages
                ])
                prompt += f"\n\n对话历史：\n{history_text}"
            
            response = await self.client.post(
                f"{self.api_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的情感分析师，擅长从文本中识别用户的情感状态和财务压力。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 300
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 解析JSON响应
                parsed = json.loads(content)
                return parsed
            else:
                logger.error(f"AI情感分析调用失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"AI情感分析异常: {e}")
            return None
    
    def _get_emotion_description(
        self,
        emotion: str,
        stress_level: float,
        scenario_tags: List[str]
    ) -> str:
        """
        生成情感描述
        Requirements: 5.1
        """
        descriptions = {
            EmotionState.HAPPY: "您看起来心情不错",
            EmotionState.STRESSED: "您似乎有些压力",
            EmotionState.ANXIOUS: "您看起来有些焦虑",
            EmotionState.NEUTRAL: "您的情绪比较平静",
            EmotionState.GUILTY: "您对这笔支出似乎有些内疚",
            EmotionState.EXCITED: "您看起来很兴奋",
            EmotionState.FRUSTRATED: "您似乎有些烦躁",
            EmotionState.RELIEVED: "您看起来松了一口气"
        }
        
        base_description = descriptions.get(emotion, "无法准确识别情感状态")
        
        # 添加压力水平描述
        if stress_level > 0.7:
            base_description += "，财务压力较大"
        elif stress_level > 0.4:
            base_description += "，有一定的财务压力"
        
        # 添加场景描述
        if scenario_tags:
            scenario_desc = "、".join(scenario_tags)
            base_description += f"，当前场景：{scenario_desc}"
        
        return base_description
    
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
            from app.models.conversation import AIConversation
            from sqlalchemy import select
            
            # 查找或创建对话记录
            stmt = select(AIConversation).where(AIConversation.user_id == user_id)
            result = await db_session.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                conversation = AIConversation(
                    user_id=user_id,
                    messages=[],
                    emotion_history=[]
                )
                db_session.add(conversation)
            
            # 添加情感记录
            emotion_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "emotion": emotion_data["emotion"],
                "stress_level": emotion_data["stress_level"],
                "scenario_tags": emotion_data["scenario_tags"],
                "confidence": emotion_data["confidence"]
            }
            
            conversation.emotion_history.append(emotion_record)
            
            # 保持历史记录在合理范围内（最近50条）
            if len(conversation.emotion_history) > 50:
                conversation.emotion_history = conversation.emotion_history[-50:]
            
            conversation.updated_at = datetime.utcnow()
            
            await db_session.commit()
            
            # 分析情感趋势
            trend_analysis = self._analyze_emotion_trend(conversation.emotion_history)
            
            return {
                "emotion_recorded": True,
                "trend_analysis": trend_analysis,
                "total_records": len(conversation.emotion_history)
            }
            
        except Exception as e:
            logger.error(f"跟踪情感历史失败: {e}")
            await db_session.rollback()
            return {
                "emotion_recorded": False,
                "error": str(e)
            }
    
    def _analyze_emotion_trend(self, emotion_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析情感趋势
        Requirements: 5.1
        """
        if not emotion_history or len(emotion_history) < 2:
            return {"trend": "insufficient_data"}
        
        recent_records = emotion_history[-10:]  # 最近10条记录
        
        # 计算平均压力水平
        avg_stress = sum(record.get("stress_level", 0) for record in recent_records) / len(recent_records)
        
        # 统计情感分布
        emotion_counts = {}
        for record in recent_records:
            emotion = record.get("emotion", "neutral")
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"
        
        # 分析趋势
        if len(recent_records) >= 5:
            first_half_stress = sum(
                record.get("stress_level", 0) for record in recent_records[:len(recent_records)//2]
            ) / (len(recent_records)//2)
            
            second_half_stress = sum(
                record.get("stress_level", 0) for record in recent_records[len(recent_records)//2:]
            ) / (len(recent_records) - len(recent_records)//2)
            
            if second_half_stress > first_half_stress + 0.2:
                trend = "increasing_stress"
            elif first_half_stress > second_half_stress + 0.2:
                trend = "decreasing_stress"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "avg_stress_level": avg_stress,
            "dominant_emotion": dominant_emotion,
            "emotion_distribution": emotion_counts,
            "analysis_period": f"last_{len(recent_records)}_records"
        }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局情感分析服务实例
emotion_service = EmotionAnalysisService()