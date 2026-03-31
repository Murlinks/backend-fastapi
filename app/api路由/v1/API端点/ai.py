"""
AI服务API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.core.database import get_db
from app.services.ai_service import ai_service
from app.services.multimodal_service import multimodal_processor
from app.services.financial_prediction_service import (
    financial_prediction_service,
    anomaly_detection_service,
    consumption_pattern_analyzer
)

logger = logging.getLogger(__name__)
router = APIRouter()


class MultiModalInput(BaseModel):
    """多模态输入"""
    text: Optional[str] = None
    voice_data: Optional[str] = None  # Base64编码的音频数据
    emoji: Optional[str] = None
    gesture: Optional[str] = None


class ExpenseExtractionResponse(BaseModel):
    """支出信息提取响应"""
    amount: Optional[float]
    category: Optional[str]
    description: str
    confidence: float
    needs_clarification: bool
    clarification_question: Optional[str] = None


class EmotionAnalysisResponse(BaseModel):
    """情感分析响应"""
    emotion: str
    stress_level: float
    confidence: float
    context_tags: List[str]


class AIRecommendationResponse(BaseModel):
    """AI建议响应"""
    recommendation_type: str
    message: str
    alternatives: List[str]
    confidence: float


@router.post("/extract", response_model=ExpenseExtractionResponse, summary="提取支出信息")
async def extract_expense_info(
    input_data: MultiModalInput,
    db: AsyncSession = Depends(get_db)
):
    """
    从多模态输入中提取支出信息
    Requirements: 1.2, 2.1
    """
    try:
        result = await ai_service.extract_expense_info(
            text=input_data.text,
            voice_data=input_data.voice_data,
            emoji=input_data.emoji
        )
        
        return ExpenseExtractionResponse(**result)
        
    except Exception as e:
        logger.error(f"提取支出信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提取支出信息失败"
        )


@router.post("/categorize", summary="智能分类")
async def categorize_expense(
    description: str,
    amount: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    智能分类支出
    Requirements: 2.1, 2.2
    """
    try:
        result = await ai_service.categorize_expense(
            description=description,
            amount=amount
        )
        
        return result
        
    except Exception as e:
        logger.error(f"智能分类失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="智能分类失败"
        )


@router.post("/emotion", response_model=EmotionAnalysisResponse, summary="情感分析")
async def analyze_emotion(
    conversation_history: List[Dict[str, Any]],
    current_text: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    分析用户情感状态
    Requirements: 5.1, 5.2
    """
    try:
        # 从对话历史中提取最新的用户消息
        if not current_text and conversation_history:
            latest_message = conversation_history[-1]
            current_text = latest_message.get("content", "")
        
        if not current_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要提供文本内容进行情感分析"
            )
        
        # 调用AI服务进行情感分析
        emotion_result = await ai_service.analyze_emotion(
            text=current_text,
            conversation_history=conversation_history,
            context=context
        )
        
        return EmotionAnalysisResponse(
            emotion=emotion_result["emotion"],
            stress_level=emotion_result["stress_level"],
            confidence=emotion_result["confidence"],
            context_tags=emotion_result["scenario_tags"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="情感分析失败"
        )


@router.post("/suggest", response_model=AIRecommendationResponse, summary="获取AI建议")
async def get_ai_suggestion(
    emotion_data: Dict[str, Any],
    budget_context: Dict[str, Any],
    expense_context: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取基于上下文的AI建议
    Requirements: 5.3, 5.4, 5.5
    """
    try:
        # 调用AI服务生成建议
        recommendation = await ai_service.generate_ai_recommendation(
            emotion_data=emotion_data,
            budget_context=budget_context,
            expense_context=expense_context,
            user_profile=user_profile
        )
        
        return AIRecommendationResponse(
            recommendation_type=recommendation["recommendation_type"],
            message=recommendation["primary_message"],
            alternatives=recommendation["alternatives"],
            confidence=recommendation["confidence"]
        )
        
    except Exception as e:
        logger.error(f"获取AI建议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取AI建议失败"
        )


@router.post("/clarify", summary="澄清问题")
async def ask_clarification(
    original_input: str,
    clarification_response: str,
    previous_extraction: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    处理用户的澄清回答
    Requirements: 1.5
    """
    try:
        if previous_extraction is None:
            previous_extraction = {}
        
        result = await ai_service.handle_clarification(
            original_input=original_input,
            clarification_response=clarification_response,
            previous_extraction=previous_extraction
        )
        
        return {
            "message": "感谢澄清，已更新支出信息",
            "updated_expense": result
        }
        
    except Exception as e:
        logger.error(f"处理澄清失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理澄清失败"
        )


class ConversationRequest(BaseModel):
    """对话请求"""
    user_message: str
    conversation_history: List[Dict[str, str]] = []
    context: Optional[Dict[str, Any]] = None


@router.post("/conversation", summary="生成对话响应")
async def generate_conversation_response(
    request: ConversationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    生成AI对话响应
    Requirements: 1.2
    """
    try:
        response = await ai_service.generate_conversation_response(
            user_message=request.user_message,
            conversation_history=request.conversation_history,
            context=request.context
        )
        
        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"生成对话响应失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成对话响应失败"
        )



# ============ 多模态输入处理端点 ============

class VoiceInputRequest(BaseModel):
    """语音输入请求"""
    voice_data: str  # Base64编码的音频数据


@router.post("/voice/process", summary="处理语音输入")
async def process_voice_input(
    request: VoiceInputRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    处理语音输入并转换为文本
    Requirements: 1.1
    """
    try:
        result = await multimodal_processor.process_voice_input(request.voice_data)
        return result
        
    except Exception as e:
        logger.error(f"处理语音输入失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理语音输入失败"
        )


class EmojiInputRequest(BaseModel):
    """表情符号输入请求"""
    emoji: str


@router.post("/emoji/parse", summary="解析表情符号")
async def parse_emoji_input(
    request: EmojiInputRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    解析表情符号输入
    Requirements: 1.3
    """
    try:
        result = multimodal_processor.parse_emoji_input(request.emoji)
        return result
        
    except Exception as e:
        logger.error(f"解析表情符号失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="解析表情符号失败"
        )


class GestureInputRequest(BaseModel):
    """手势输入请求"""
    gesture: str
    context: Optional[Dict[str, Any]] = None


@router.post("/gesture/parse", summary="解析手势输入")
async def parse_gesture_input(
    request: GestureInputRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    解析手势输入
    Requirements: 1.4
    """
    try:
        result = multimodal_processor.parse_gesture_input(
            gesture=request.gesture,
            context=request.context
        )
        return result
        
    except Exception as e:
        logger.error(f"解析手势输入失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="解析手势输入失败"
        )


class MultiModalProcessRequest(BaseModel):
    """完整多模态处理请求"""
    text: Optional[str] = None
    voice_data: Optional[str] = None
    emoji: Optional[str] = None
    gesture: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/multimodal/process", summary="处理完整多模态输入")
async def process_multimodal_input(
    request: MultiModalProcessRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    处理完整的多模态输入（文本+语音+表情+手势）
    Requirements: 1.1, 1.3, 1.5
    """
    try:
        # 处理各个模态
        voice_result = None
        if request.voice_data:
            voice_result = await multimodal_processor.process_voice_input(request.voice_data)
        
        emoji_result = None
        if request.emoji:
            emoji_result = multimodal_processor.parse_emoji_input(request.emoji)
        
        gesture_result = None
        if request.gesture:
            gesture_result = multimodal_processor.parse_gesture_input(
                request.gesture,
                request.context
            )
        
        # 合并多模态输入
        combined = multimodal_processor.combine_multimodal_inputs(
            text=request.text,
            voice_result=voice_result,
            emoji_result=emoji_result,
            gesture_result=gesture_result
        )
        
        # 验证输入完整性
        validation = multimodal_processor.validate_multimodal_input(combined)
        
        # 如果需要澄清，返回澄清问题
        if not validation["is_valid"]:
            return {
                "success": False,
                "needs_clarification": True,
                "clarification_questions": validation["clarification_questions"],
                "partial_data": combined
            }
        
        # 使用AI服务提取完整的支出信息
        expense_info = await ai_service.extract_expense_info(
            text=combined["text"],
            emoji=request.emoji
        )
        
        # 合并情感信息
        if combined.get("emotion"):
            expense_info["emotion"] = combined["emotion"]
            expense_info["stress_level"] = combined["stress_level"]
        
        return {
            "success": True,
            "expense_info": expense_info,
            "action": combined.get("action"),
            "multimodal_data": combined
        }
        
    except Exception as e:
        logger.error(f"处理多模态输入失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理多模态输入失败"
        )

# ============ 情感分析和建议系统端点 ============

class EmotionTrackingRequest(BaseModel):
    """情感跟踪请求"""
    user_id: str
    text: str
    conversation_history: Optional[List[Dict[str, Any]]] = []
    context: Optional[Dict[str, Any]] = None


@router.post("/emotion/track", summary="跟踪用户情感历史")
async def track_user_emotion(
    request: EmotionTrackingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    跟踪用户情感历史
    Requirements: 5.1
    """
    try:
        # 分析当前情感
        emotion_result = await ai_service.analyze_emotion(
            text=request.text,
            conversation_history=request.conversation_history,
            context=request.context
        )
        
        # 保存到情感历史
        tracking_result = await ai_service.track_emotion_history(
            user_id=request.user_id,
            emotion_data=emotion_result,
            db_session=db
        )
        
        return {
            "emotion_analysis": emotion_result,
            "tracking_result": tracking_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"跟踪用户情感失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="跟踪用户情感失败"
        )


class ComprehensiveAnalysisRequest(BaseModel):
    """综合分析请求"""
    user_id: str
    text: str
    conversation_history: Optional[List[Dict[str, Any]]] = []
    budget_context: Dict[str, Any]
    expense_context: Dict[str, Any]
    user_profile: Optional[Dict[str, Any]] = None


@router.post("/comprehensive-analysis", summary="综合情感分析和建议生成")
async def comprehensive_analysis(
    request: ComprehensiveAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    综合情感分析和AI建议生成
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    try:
        # 1. 情感分析
        emotion_result = await ai_service.analyze_emotion(
            text=request.text,
            conversation_history=request.conversation_history,
            context={
                **request.budget_context,
                **request.expense_context,
                **(request.user_profile or {})
            }
        )
        
        # 2. 生成AI建议
        recommendation = await ai_service.generate_ai_recommendation(
            emotion_data=emotion_result,
            budget_context=request.budget_context,
            expense_context=request.expense_context,
            user_profile=request.user_profile
        )
        
        # 3. 跟踪情感历史
        tracking_result = await ai_service.track_emotion_history(
            user_id=request.user_id,
            emotion_data=emotion_result,
            db_session=db
        )
        
        return {
            "emotion_analysis": emotion_result,
            "ai_recommendation": recommendation,
            "emotion_tracking": tracking_result,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"综合分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="综合分析失败"
        )


class FinancialStressAnalysisRequest(BaseModel):
    """财务压力分析请求"""
    user_id: str
    recent_expenses: List[Dict[str, Any]]
    budget_info: Dict[str, Any]
    conversation_history: Optional[List[Dict[str, Any]]] = []


@router.post("/financial-stress", summary="财务压力分析")
async def analyze_financial_stress(
    request: FinancialStressAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    分析用户财务压力状况
    Requirements: 5.2
    """
    try:
        # 构建分析上下文
        context = {
            "budget_info": request.budget_info,
            "recent_expenses": request.recent_expenses,
            "expense_count": len(request.recent_expenses)
        }
        
        # 从对话历史中提取文本
        conversation_text = ""
        if request.conversation_history:
            recent_messages = request.conversation_history[-5:]
            conversation_text = " ".join([
                msg.get("content", "") for msg in recent_messages
                if msg.get("role") == "user"
            ])
        
        # 进行情感分析，重点关注财务压力
        emotion_result = await ai_service.analyze_emotion(
            text=conversation_text,
            conversation_history=request.conversation_history,
            context=context
        )
        
        # 计算财务压力指标
        stress_indicators = {
            "budget_utilization": request.budget_info.get("utilization_ratio", 0),
            "overspending_risk": request.budget_info.get("remaining_ratio", 1.0) < 0.2,
            "emergency_expenses": sum(1 for exp in request.recent_expenses if exp.get("is_emergency", False)),
            "stress_keywords_detected": emotion_result["financial_stress_detected"],
            "overall_stress_level": emotion_result["stress_level"]
        }
        
        # 生成压力缓解建议
        if emotion_result["stress_level"] > 0.6:
            stress_relief_recommendation = await ai_service.generate_ai_recommendation(
                emotion_data=emotion_result,
                budget_context=request.budget_info,
                expense_context={"category": "general", "amount": 0, "is_emergency": False},
                user_profile={"stress_focus": True}
            )
        else:
            stress_relief_recommendation = None
        
        return {
            "stress_analysis": emotion_result,
            "stress_indicators": stress_indicators,
            "stress_relief_recommendation": stress_relief_recommendation,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"财务压力分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="财务压力分析失败"
        )


# ============ 财务预测和分析端点 ============

class MonthlyPredictionRequest(BaseModel):
    """月度支出预测请求"""
    expense_history: List[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]] = None


@router.post("/predict/monthly", summary="预测月度支出")
async def predict_monthly_expense(
    request: MonthlyPredictionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    预测下月支出并提供预算建议
    Requirements: 2.2, 5.3
    """
    try:
        result = await financial_prediction_service.predict_monthly_expense(
            expense_history=request.expense_history,
            user_profile=request.user_profile
        )
        
        return result
        
    except Exception as e:
        logger.error(f"预测月度支出失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="预测月度支出失败"
        )


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求"""
    expense_history: List[Dict[str, Any]]
    new_expense: Optional[Dict[str, Any]] = None


@router.post("/detect/anomalies", summary="检测异常支出")
async def detect_expense_anomalies(
    request: AnomalyDetectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    检测异常支出并生成警告
    Requirements: 5.2
    """
    try:
        result = await anomaly_detection_service.detect_anomalies(
            expense_history=request.expense_history,
            new_expense=request.new_expense
        )
        
        return result
        
    except Exception as e:
        logger.error(f"异常检测失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="异常检测失败"
        )


class ConsumptionPatternRequest(BaseModel):
    """消费模式分析请求"""
    expense_history: List[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]] = None


@router.post("/analyze/pattern", summary="分析消费模式")
async def analyze_consumption_pattern(
    request: ConsumptionPatternRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    分析用户的消费模式并提供优化建议
    Requirements: 2.2, 5.3, 5.4
    """
    try:
        result = await consumption_pattern_analyzer.analyze_consumption_pattern(
            expense_history=request.expense_history,
            user_profile=request.user_profile
        )
        
        return result
        
    except Exception as e:
        logger.error(f"消费模式分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="消费模式分析失败"
        )


class ComprehensiveFinancialAnalysisRequest(BaseModel):
    """综合财务分析请求"""
    user_id: str
    expense_history: List[Dict[str, Any]]
    budget_context: Dict[str, Any]
    user_profile: Optional[Dict[str, Any]] = None


@router.post("/analyze/comprehensive", summary="综合财务分析")
async def comprehensive_financial_analysis(
    request: ComprehensiveFinancialAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    综合财务分析，包括预测、异常检测、消费模式分析
    Requirements: 2.2, 5.2, 5.3, 5.4, 5.5
    """
    try:
        # 并行执行多个分析
        import asyncio
        
        # 1. 财务预测
        prediction_task = financial_prediction_service.predict_monthly_expense(
            expense_history=request.expense_history,
            user_profile=request.user_profile
        )
        
        # 2. 异常检测
        anomaly_task = anomaly_detection_service.detect_anomalies(
            expense_history=request.expense_history
        )
        
        # 3. 消费模式分析
        pattern_task = consumption_pattern_analyzer.analyze_consumption_pattern(
            expense_history=request.expense_history,
            user_profile=request.user_profile
        )
        
        # 等待所有分析完成
        prediction_result, anomaly_result, pattern_result = await asyncio.gather(
            prediction_task,
            anomaly_task,
            pattern_task,
            return_exceptions=True
        )
        
        # 生成综合建议
        comprehensive_suggestions = []
        
        # 从预测结果中提取建议
        if isinstance(prediction_result, dict) and prediction_result.get("success"):
            comprehensive_suggestions.extend(
                prediction_result.get("recommendations", [])
            )
        
        # 从异常检测结果中提取警告
        if isinstance(anomaly_result, dict) and anomaly_result.get("has_anomalies"):
            comprehensive_suggestions.extend(
                anomaly_result.get("warnings", [])
            )
        
        # 从消费模式分析中提取建议
        if isinstance(pattern_result, dict) and pattern_result.get("success"):
            comprehensive_suggestions.extend(
                pattern_result.get("suggestions", [])
            )
        
        # 生成风险等级
        risk_level = "low"
        if isinstance(anomaly_result, dict):
            risk_level = anomaly_result.get("risk_level", "low")
        
        # 根据预测趋势调整风险等级
        if isinstance(prediction_result, dict) and prediction_result.get("success"):
            trend = prediction_result.get("prediction", {}).get("trend", "")
            if trend == "increasing" and risk_level != "high":
                risk_level = "medium"
        
        return {
            "success": True,
            "analysis_date": datetime.utcnow().isoformat(),
            "risk_level": risk_level,
            "prediction_analysis": prediction_result if isinstance(prediction_result, dict) else None,
            "anomaly_analysis": anomaly_result if isinstance(anomaly_result, dict) else None,
            "pattern_analysis": pattern_result if isinstance(pattern_result, dict) else None,
            "comprehensive_suggestions": comprehensive_suggestions,
            "action_items": _generate_action_items(
                risk_level,
                prediction_result if isinstance(prediction_result, dict) else None,
                anomaly_result if isinstance(anomaly_result, dict) else None,
                pattern_result if isinstance(pattern_result, dict) else None
            )
        }
        
    except Exception as e:
        logger.error(f"综合财务分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="综合财务分析失败"
        )


def _generate_action_items(
    risk_level: str,
    prediction_result: Optional[Dict[str, Any]],
    anomaly_result: Optional[Dict[str, Any]],
    pattern_result: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """生成行动项"""
    action_items = []
    
    # 基于风险等级的行动项
    if risk_level == "high":
        action_items.append({
            "priority": "high",
            "category": "risk_management",
            "title": "立即审查财务状况",
            "description": "检测到高风险异常支出，建议立即审查最近的消费记录",
            "deadline": "24小时内"
        })
    elif risk_level == "medium":
        action_items.append({
            "priority": "medium",
            "category": "budget_review",
            "title": "重新评估预算设置",
            "description": "建议根据最近的消费趋势调整预算分配",
            "deadline": "本周内"
        })
    
    # 基于预测结果
    if prediction_result and prediction_result.get("success"):
        trend = prediction_result.get("prediction", {}).get("trend", "")
        if trend == "increasing":
            action_items.append({
                "priority": "medium",
                "category": "budget_control",
                "title": "实施支出控制措施",
                "description": "支出呈上升趋势，建议削减非必要开支",
                "deadline": "本月内"
            })
    
    # 基于异常检测结果
    if anomaly_result and anomaly_result.get("has_anomalies"):
        action_items.append({
            "priority": "high",
            "category": "anomaly_review",
            "title": "审查异常支出",
            "description": f"发现{anomaly_result.get('anomaly_count', 0)}笔异常支出，请逐一确认",
            "deadline": "48小时内"
        })
    
    # 基于消费模式分析
    if pattern_result and pattern_result.get("success"):
        profile = pattern_result.get("profile", {})
        if profile.get("consumption_type") == "irregular":
            action_items.append({
                "priority": "low",
                "category": "habit_building",
                "title": "建立规律消费习惯",
                "description": "建议制定固定的消费计划，提高财务可控性",
                "deadline": "本月内"
            })
    
    return action_items