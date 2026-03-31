"""
AI建议服务 - 上下文感知的智能建议系统
Requirements: 5.3, 5.4, 5.5
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

from app.core.config import settings
from app.services.emotion_service import EmotionState, StressLevel

logger = logging.getLogger(__name__)


class RecommendationType:
    """建议类型"""
    BUDGET_ADVICE = "budget_advice"
    ALTERNATIVE_SUGGESTION = "alternative_suggestion"
    GUILT_RELIEF = "guilt_relief"
    STRESS_RELIEF = "stress_relief"
    EMERGENCY_HELP = "emergency_help"
    SPENDING_CONTROL = "spending_control"


class AIRecommendationService:
    """AI建议服务类"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # 预定义建议模板
        self.recommendation_templates = {
            # 内疚缓解建议
            RecommendationType.GUILT_RELIEF: {
                EmotionState.GUILTY: [
                    "适度的消费是正常的，不要过分自责。重要的是从中学习并调整未来的消费习惯。",
                    "每个人都有冲动消费的时候，关键是要保持理性的消费观念。",
                    "这次的支出可以作为一个提醒，帮助您更好地规划未来的预算。",
                    "偶尔的放松消费是可以理解的，但要确保不影响基本生活需求。"
                ]
            },
            
            # 压力释放建议
            RecommendationType.STRESS_RELIEF: {
                "high_stress": [
                    "财务压力很大时，可以尝试制定详细的预算计划，这样会让您更有控制感。",
                    "建议您寻找一些免费或低成本的减压方式，比如散步、听音乐或与朋友聊天。",
                    "考虑将大额支出分解为小额分期，减轻一次性的财务压力。",
                    "如果压力持续，建议咨询专业的财务规划师或心理咨询师。"
                ],
                "medium_stress": [
                    "适当的财务规划可以帮助缓解压力，建议设置每月的储蓄目标。",
                    "可以尝试记录每日支出，这样能更好地了解资金流向。",
                    "建议为紧急情况预留一些资金，这样会让您更安心。"
                ]
            },
            
            # 预算紧张时的替代方案
            RecommendationType.ALTERNATIVE_SUGGESTION: {
                "dining": [
                    "可以尝试在家做饭，既健康又省钱。",
                    "选择性价比更高的餐厅，或者寻找优惠活动。",
                    "与朋友一起聚餐时可以选择AA制，分摊费用。",
                    "考虑购买食材自己制作，成本会更低。"
                ],
                "entertainment": [
                    "可以选择免费的娱乐活动，如公园散步、免费展览等。",
                    "与朋友在家看电影，成本更低且更温馨。",
                    "寻找学生折扣或团购优惠。",
                    "考虑户外活动，既健康又经济。"
                ],
                "shopping": [
                    "购买前先考虑是否真的需要，避免冲动消费。",
                    "可以等待促销活动或使用优惠券。",
                    "考虑购买二手物品或租赁服务。",
                    "制作购物清单，避免不必要的支出。"
                ],
                "transportation": [
                    "可以选择公共交通工具，比打车更经济。",
                    "考虑步行或骑自行车，既环保又健康。",
                    "与朋友拼车分摊费用。",
                    "提前规划路线，避免绕路增加费用。"
                ]
            }
        }
        
        # 场景化建议
        self.scenario_recommendations = {
            "期末周": {
                "stress_relief": "期末压力大是正常的，适当的咖啡和夜宵支出是可以理解的，但要注意身体健康。",
                "budget_advice": "建议为期末周的额外支出（咖啡、夜宵等）预留专门预算。",
                "alternatives": ["选择图书馆免费的学习环境", "与同学一起学习，分摊咖啡费用"]
            },
            "工作日": {
                "stress_relief": "工作压力大时，适当的工作餐和通勤费用是必要的投资。",
                "budget_advice": "建议将工作相关支出单独分类管理。",
                "alternatives": ["自带午餐", "选择更经济的通勤方式"]
            },
            "周末": {
                "guilt_relief": "周末的放松消费是应该的，适度的娱乐支出有助于身心健康。",
                "alternatives": ["选择免费的户外活动", "与朋友在家聚会"]
            }
        }
    
    async def generate_recommendation(
        self,
        emotion_data: Dict[str, Any],
        budget_context: Dict[str, Any],
        expense_context: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成个性化AI建议
        Requirements: 5.3, 5.4, 5.5
        
        Args:
            emotion_data: 情感分析数据
            budget_context: 预算上下文
            expense_context: 支出上下文
            user_profile: 用户画像
        
        Returns:
            AI建议结果
        """
        try:
            # 1. 分析当前情况
            situation_analysis = self._analyze_situation(
                emotion_data, budget_context, expense_context
            )
            
            # 2. 确定建议类型
            recommendation_type = self._determine_recommendation_type(situation_analysis)
            
            # 3. 生成基础建议
            base_recommendations = self._generate_base_recommendations(
                recommendation_type, situation_analysis
            )
            
            # 4. 如果有AI API，进行个性化增强
            if self.api_key:
                enhanced_recommendations = await self._enhance_with_ai(
                    base_recommendations, situation_analysis, user_profile
                )
            else:
                enhanced_recommendations = base_recommendations
            
            # 5. 添加替代方案
            alternatives = self._generate_alternatives(
                situation_analysis, expense_context
            )
            
            # 6. 计算建议置信度
            confidence = self._calculate_confidence(situation_analysis)
            
            return {
                "recommendation_type": recommendation_type,
                "primary_message": enhanced_recommendations["primary_message"],
                "detailed_advice": enhanced_recommendations["detailed_advice"],
                "alternatives": alternatives,
                "confidence": confidence,
                "situation_analysis": situation_analysis,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成AI建议失败: {e}")
            return self._get_fallback_recommendation(emotion_data, budget_context)
    
    def _analyze_situation(
        self,
        emotion_data: Dict[str, Any],
        budget_context: Dict[str, Any],
        expense_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析当前情况
        Requirements: 5.3
        """
        emotion = emotion_data.get("emotion", EmotionState.NEUTRAL)
        stress_level = emotion_data.get("stress_level", 0.3)
        scenario_tags = emotion_data.get("scenario_tags", [])
        
        # 预算状况分析
        budget_status = "normal"
        remaining_ratio = budget_context.get("remaining_ratio", 1.0)
        if remaining_ratio < 0.1:
            budget_status = "critical"
        elif remaining_ratio < 0.3:
            budget_status = "tight"
        elif remaining_ratio < 0.6:
            budget_status = "moderate"
        
        # 支出分析
        expense_amount = expense_context.get("amount", 0)
        expense_category = expense_context.get("category", "shopping")
        is_emergency = expense_context.get("is_emergency", False)
        
        # 综合情况评估
        needs_guilt_relief = emotion == EmotionState.GUILTY
        needs_stress_relief = stress_level > 0.6 or emotion == EmotionState.STRESSED
        needs_alternatives = budget_status in ["tight", "critical"]
        needs_emergency_help = is_emergency and budget_status == "critical"
        
        return {
            "emotion": emotion,
            "stress_level": stress_level,
            "scenario_tags": scenario_tags,
            "budget_status": budget_status,
            "remaining_ratio": remaining_ratio,
            "expense_amount": expense_amount,
            "expense_category": expense_category,
            "is_emergency": is_emergency,
            "needs_guilt_relief": needs_guilt_relief,
            "needs_stress_relief": needs_stress_relief,
            "needs_alternatives": needs_alternatives,
            "needs_emergency_help": needs_emergency_help
        }
    
    def _determine_recommendation_type(self, situation: Dict[str, Any]) -> str:
        """
        确定建议类型
        Requirements: 5.3, 5.4, 5.5
        """
        if situation["needs_emergency_help"]:
            return RecommendationType.EMERGENCY_HELP
        elif situation["needs_guilt_relief"]:
            return RecommendationType.GUILT_RELIEF
        elif situation["needs_stress_relief"]:
            return RecommendationType.STRESS_RELIEF
        elif situation["needs_alternatives"]:
            return RecommendationType.ALTERNATIVE_SUGGESTION
        elif situation["budget_status"] == "critical":
            return RecommendationType.SPENDING_CONTROL
        else:
            return RecommendationType.BUDGET_ADVICE
    
    def _generate_base_recommendations(
        self,
        recommendation_type: str,
        situation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成基础建议
        Requirements: 5.3, 5.4, 5.5
        """
        emotion = situation["emotion"]
        stress_level = situation["stress_level"]
        scenario_tags = situation["scenario_tags"]
        budget_status = situation["budget_status"]
        
        # 选择合适的建议模板
        if recommendation_type == RecommendationType.GUILT_RELIEF:
            templates = self.recommendation_templates[RecommendationType.GUILT_RELIEF].get(
                emotion, self.recommendation_templates[RecommendationType.GUILT_RELIEF][EmotionState.GUILTY]
            )
            primary_message = templates[0]
            detailed_advice = templates[1:3]
            
        elif recommendation_type == RecommendationType.STRESS_RELIEF:
            stress_key = "high_stress" if stress_level > 0.7 else "medium_stress"
            templates = self.recommendation_templates[RecommendationType.STRESS_RELIEF][stress_key]
            primary_message = templates[0]
            detailed_advice = templates[1:]
            
        elif recommendation_type == RecommendationType.ALTERNATIVE_SUGGESTION:
            category = situation["expense_category"]
            templates = self.recommendation_templates[RecommendationType.ALTERNATIVE_SUGGESTION].get(
                category, self.recommendation_templates[RecommendationType.ALTERNATIVE_SUGGESTION]["shopping"]
            )
            primary_message = f"预算紧张时，{templates[0]}"
            detailed_advice = templates[1:]
            
        elif recommendation_type == RecommendationType.EMERGENCY_HELP:
            primary_message = "紧急支出时预算不足，建议优先处理必要支出，其他支出可以延后。"
            detailed_advice = [
                "考虑向亲友寻求临时帮助",
                "查看是否有其他预算类别可以调剂",
                "评估是否可以分期付款"
            ]
            
        elif recommendation_type == RecommendationType.SPENDING_CONTROL:
            primary_message = "预算已经非常紧张，建议暂停非必要支出。"
            detailed_advice = [
                "重新审视所有计划中的支出",
                "优先保证基本生活需求",
                "考虑增加收入来源"
            ]
            
        else:  # BUDGET_ADVICE
            primary_message = "您的财务状况良好，建议继续保持理性消费。"
            detailed_advice = [
                "可以适当增加储蓄比例",
                "考虑为未来的大额支出做准备",
                "保持当前的消费习惯"
            ]
        
        # 添加场景化建议
        scenario_advice = []
        for tag in scenario_tags:
            if tag in self.scenario_recommendations:
                scenario_rec = self.scenario_recommendations[tag]
                if recommendation_type.replace("_", "_") in scenario_rec:
                    scenario_advice.append(scenario_rec[recommendation_type.replace("_", "_")])
        
        if scenario_advice:
            detailed_advice.extend(scenario_advice)
        
        return {
            "primary_message": primary_message,
            "detailed_advice": detailed_advice[:4]  # 限制建议数量
        }
    
    async def _enhance_with_ai(
        self,
        base_recommendations: Dict[str, Any],
        situation: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用AI增强建议
        Requirements: 5.3, 5.4, 5.5
        """
        try:
            # 构建AI提示
            prompt = self._build_ai_prompt(base_recommendations, situation, user_profile)
            
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
                            "content": "你是一个专业的财务顾问和心理咨询师，擅长根据用户的情感状态和财务情况提供个性化建议。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 400
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_content = result["choices"][0]["message"]["content"]
                
                # 解析AI响应
                enhanced = self._parse_ai_response(ai_content, base_recommendations)
                return enhanced
            else:
                logger.error(f"AI建议增强调用失败: {response.status_code}")
                return base_recommendations
                
        except Exception as e:
            logger.error(f"AI建议增强异常: {e}")
            return base_recommendations
    
    def _build_ai_prompt(
        self,
        base_recommendations: Dict[str, Any],
        situation: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建AI提示
        Requirements: 5.3
        """
        prompt = f"""
请根据以下用户情况，优化和个性化财务建议：

用户情感状态：{situation['emotion']}
压力水平：{situation['stress_level']}
预算状况：{situation['budget_status']}
支出类别：{situation['expense_category']}
支出金额：{situation['expense_amount']}
场景标签：{', '.join(situation['scenario_tags'])}

基础建议：
主要建议：{base_recommendations['primary_message']}
详细建议：{', '.join(base_recommendations['detailed_advice'])}

用户画像：{user_profile.get('identity', '未知') if user_profile else '未知'}

请提供更个性化和温暖的建议，格式如下：
主要建议：[一句话总结]
详细建议：[3-4条具体建议，每条一行]
"""
        
        return prompt
    
    def _parse_ai_response(
        self,
        ai_content: str,
        base_recommendations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解析AI响应
        Requirements: 5.3
        """
        try:
            lines = ai_content.strip().split('\n')
            primary_message = base_recommendations["primary_message"]
            detailed_advice = []
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith("主要建议："):
                    primary_message = line.replace("主要建议：", "").strip()
                    current_section = "primary"
                elif line.startswith("详细建议："):
                    current_section = "detailed"
                elif current_section == "detailed" and line:
                    # 清理格式
                    advice = line.lstrip("- ").lstrip("• ").lstrip("1234567890. ")
                    if advice:
                        detailed_advice.append(advice)
            
            # 如果解析失败，使用基础建议
            if not detailed_advice:
                detailed_advice = base_recommendations["detailed_advice"]
            
            return {
                "primary_message": primary_message,
                "detailed_advice": detailed_advice[:4]  # 限制数量
            }
            
        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            return base_recommendations
    
    def _generate_alternatives(
        self,
        situation: Dict[str, Any],
        expense_context: Dict[str, Any]
    ) -> List[str]:
        """
        生成替代方案
        Requirements: 5.4
        """
        category = situation["expense_category"]
        budget_status = situation["budget_status"]
        
        alternatives = []
        
        # 根据类别提供替代方案
        if category in self.recommendation_templates[RecommendationType.ALTERNATIVE_SUGGESTION]:
            category_alternatives = self.recommendation_templates[RecommendationType.ALTERNATIVE_SUGGESTION][category]
            alternatives.extend(category_alternatives[:3])
        
        # 根据预算状况添加额外建议
        if budget_status == "critical":
            alternatives.extend([
                "考虑延后这笔支出",
                "寻找更便宜的替代选项",
                "与朋友分摊费用"
            ])
        elif budget_status == "tight":
            alternatives.extend([
                "寻找优惠活动或折扣",
                "考虑分期付款"
            ])
        
        # 去重并限制数量
        unique_alternatives = []
        for alt in alternatives:
            if alt not in unique_alternatives:
                unique_alternatives.append(alt)
        
        return unique_alternatives[:5]  # 最多5个替代方案
    
    def _calculate_confidence(self, situation: Dict[str, Any]) -> float:
        """
        计算建议置信度
        Requirements: 5.3
        """
        confidence = 0.7  # 基础置信度
        
        # 根据情感识别置信度调整
        emotion_confidence = situation.get("emotion_confidence", 0.7)
        confidence = (confidence + emotion_confidence) / 2
        
        # 根据预算信息完整性调整
        if situation.get("remaining_ratio") is not None:
            confidence += 0.1
        
        # 根据场景标签调整
        if situation.get("scenario_tags"):
            confidence += 0.1
        
        return min(0.95, confidence)
    
    def _get_fallback_recommendation(
        self,
        emotion_data: Dict[str, Any],
        budget_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取降级建议
        Requirements: 5.3
        """
        return {
            "recommendation_type": RecommendationType.BUDGET_ADVICE,
            "primary_message": "建议您保持理性消费，根据预算合理安排支出。",
            "detailed_advice": [
                "记录每笔支出，了解资金流向",
                "设置月度预算目标",
                "为紧急情况预留资金",
                "定期回顾和调整消费习惯"
            ],
            "alternatives": [
                "寻找更经济的替代方案",
                "与朋友分摊费用",
                "等待促销活动"
            ],
            "confidence": 0.6,
            "situation_analysis": {
                "fallback_mode": True
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局AI建议服务实例
recommendation_service = AIRecommendationService()