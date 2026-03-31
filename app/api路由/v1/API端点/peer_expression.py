"""
同龄人化表达API端点
提供同龄人化响应生成和风格配置接口
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.peer_expression_service import (
    peer_expression_service, 
    ScenarioType, 
    ExpressionStyle
)
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()


class GenerateResponseRequest(BaseModel):
    """生成响应请求"""
    scenario: str = Field(..., description="场景类型", 
                         example="record_success")
    data: dict = Field(default_factory=dict, description="数据参数",
                      example={"amount": 25.5, "category": "餐饮"})
    style: Optional[str] = Field(None, description="表达风格",
                                example="casual")


class GenerateResponseResponse(BaseModel):
    """生成响应结果"""
    response: str = Field(..., description="生成的响应文本")
    scenario: str = Field(..., description="场景类型")
    style: str = Field(..., description="使用的表达风格")


class StylePreferenceRequest(BaseModel):
    """风格偏好设置请求"""
    preferred_style: str = Field(..., description="偏好的表达风格",
                                example="energetic")
    enable_emoji: bool = Field(default=True, description="是否启用emoji")
    formality_level: str = Field(default="low", description="正式程度",
                                example="low")


class StyleGuideResponse(BaseModel):
    """风格指南响应"""
    available_styles: list = Field(..., description="可用的表达风格")
    style_guide: dict = Field(..., description="风格指南")
    vocabulary_preview: dict = Field(..., description="词汇库预览")


@router.post("/generate", response_model=GenerateResponseResponse)
async def generate_peer_response(
    request: GenerateResponseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    生成同龄人化响应
    
    Args:
        request: 生成请求，包含场景、数据和风格
        current_user: 当前用户
        
    Returns:
        生成的同龄人化响应
        
    Example:
        ```json
        {
            "scenario": "record_success",
            "data": {"amount": 25.5, "category": "餐饮"},
            "style": "casual"
        }
        ```
    """
    try:
        # 验证场景类型
        scenario_type = ScenarioType(request.scenario)
        
        # 验证风格（如果提供）
        style = None
        if request.style:
            style = ExpressionStyle(request.style)
        
        # 获取用户偏好
        user_preference = None
        if current_user and hasattr(current_user, 'preferences'):
            user_preference = current_user.preferences
        
        # 生成响应
        response_text = peer_expression_service.generate_response(
            scenario=scenario_type,
            data=request.data,
            style=style,
            user_preference=user_preference
        )
        
        return GenerateResponseResponse(
            response=response_text,
            scenario=request.scenario,
            style=request.style or "auto"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的场景类型或风格: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成响应失败: {str(e)}"
        )


@router.get("/styles", response_model=list)
async def get_available_styles():
    """
    获取可用的表达风格列表
    
    Returns:
        可用的表达风格列表
    """
    return [
        {"value": style.value, "label": _get_style_label(style)}
        for style in ExpressionStyle
    ]


def _get_style_label(style: ExpressionStyle) -> str:
    """获取风格标签"""
    labels = {
        ExpressionStyle.CASUAL: "随意自然",
        ExpressionStyle.ENERGETIC: "热情活泼",
        ExpressionStyle.GENTLE: "温柔体贴",
        ExpressionStyle.HUMOROUS: "幽默风趣",
        ExpressionStyle.ENCOURAGING: "积极鼓励"
    }
    return labels.get(style, style.value)


@router.get("/scenarios", response_model=list)
async def get_available_scenarios():
    """
    获取可用的场景类型列表
    
    Returns:
        可用的场景类型列表
    """
    return [
        {"value": scenario.value, "label": _get_scenario_label(scenario)}
        for scenario in ScenarioType
    ]


def _get_scenario_label(scenario: ScenarioType) -> str:
    """获取场景标签"""
    labels = {
        ScenarioType.RECORD_SUCCESS: "记账成功",
        ScenarioType.BUDGET_WARNING: "预算预警",
        ScenarioType.BUDGET_EXCEEDED: "预算超支",
        ScenarioType.DAILY_REPORT: "日报",
        ScenarioType.WEEKLY_REPORT: "周报",
        ScenarioType.MONTHLY_REPORT: "月报",
        ScenarioType.SAVING_ACHIEVEMENT: "省钱成就",
        ScenarioType.EXPENSIVE_REMINDER: "大额提醒",
        ScenarioType.CLARIFICATION: "澄清询问",
        ScenarioType.GREETING: "问候",
        ScenarioType.FAREWELL: "告别",
        ScenarioType.ERROR: "错误提示"
    }
    return labels.get(scenario, scenario.value)


@router.get("/style-guide", response_model=StyleGuideResponse)
async def get_style_guide():
    """
    获取同龄人化表达风格指南
    
    Returns:
        风格指南，包含可用风格、词汇库等
    """
    style_guide = peer_expression_service.get_conversation_style_guide()
    vocabulary = peer_expression_service.vocabulary
    
    # 只返回词汇库的部分内容作为预览
    vocabulary_preview = {
        "positive_adjectives": vocabulary["positive_adjectives"][:5],
        "encouraging_words": vocabulary["encouraging_words"][:5],
        "casual_fillers": vocabulary["casual_fillers"][:5],
        "emotional_expressions": vocabulary["emotional_expressions"][:5],
        "internet_slang": vocabulary["internet_slang"][:5]
    }
    
    return StyleGuideResponse(
        available_styles=[
            {"value": style.value, "label": _get_style_label(style)}
            for style in ExpressionStyle
        ],
        style_guide=style_guide,
        vocabulary_preview=vocabulary_preview
    )


@router.post("/preference", response_model=dict)
async def set_style_preference(
    request: StylePreferenceRequest,
    current_user: User = Depends(get_current_user)
):
    """
    设置用户的表达风格偏好
    
    Args:
        request: 风格偏好设置
        current_user: 当前用户
        
    Returns:
        设置结果
    """
    try:
        # 验证风格
        if request.preferred_style:
            ExpressionStyle(request.preferred_style)
        
        # 这里应该保存到用户配置中
        # 实际实现需要连接数据库保存用户偏好
        preference_data = {
            "preferred_style": request.preferred_style,
            "enable_emoji": request.enable_emoji,
            "formality_level": request.formality_level
        }
        
        # TODO: 保存到数据库
        # await save_user_preference(current_user.id, preference_data)
        
        return {
            "success": True,
            "message": "风格偏好设置成功",
            "preference": preference_data
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的风格类型: {str(e)}"
        )


@router.get("/system-prompt")
async def get_system_prompt(
    context: Optional[str] = None
):
    """
    获取同龄人化系统提示词
    
    Args:
        context: 额外上下文
        
    Returns:
        系统提示词
    """
    prompt = peer_expression_service.get_system_prompt(context)
    return {
        "system_prompt": prompt,
        "context": context
    }
