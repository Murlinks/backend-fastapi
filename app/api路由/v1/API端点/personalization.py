"""
个性化设置API端点
提供用户偏好设置、主题定制等接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.personalization_service import personalization_service
from app.middleware.auth import get_current_user

router = APIRouter()


class PreferencesUpdateRequest(BaseModel):
    """偏好设置更新请求"""
    theme_mode: Optional[str] = Field(None, description="主题模式: light, dark, auto")
    language: Optional[str] = Field(None, description="语言: zh_CN, en_US, ja_JP, ko_KR")
    currency: Optional[str] = Field(None, description="货币: CNY, USD, EUR, JPY, KRW")
    date_format: Optional[str] = Field(None, description="日期格式")
    time_format: Optional[str] = Field(None, description="时间格式")
    first_day_of_week: Optional[int] = Field(None, ge=0, le=6, description="每周第一天: 0=Sunday, 1=Monday")
    show_expense_details: Optional[bool] = Field(None, description="显示支出详情")
    show_budget_progress: Optional[bool] = Field(None, description="显示预算进度")
    enable_analytics: Optional[bool] = Field(None, description="启用分析")
    enable_notifications: Optional[bool] = Field(None, description="启用通知")
    notification_types: Optional[list[str]] = Field(None, description="通知类型列表")
    default_category: Optional[str] = Field(None, description="默认分类")
    default_payment_method: Optional[str] = Field(None, description="默认支付方式")
    monthly_budget_limit: Optional[float] = Field(None, ge=0, description="月度预算限制")
    savings_goal: Optional[float] = Field(None, ge=0, description="储蓄目标")


class ThemeUpdateRequest(BaseModel):
    """主题更新请求"""
    primary_color: Optional[str] = Field(None, description="主色调")
    secondary_color: Optional[str] = Field(None, description="次要色调")
    background_color: Optional[str] = Field(None, description="背景色")
    text_color: Optional[str] = Field(None, description="文字颜色")
    card_color: Optional[str] = Field(None, description="卡片颜色")
    icon_color: Optional[str] = Field(None, description="图标颜色")
    use_custom_theme: Optional[bool] = Field(None, description="使用自定义主题")


@router.get("/preferences")
async def get_preferences(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取用户偏好设置
    
    返回用户的所有偏好设置，包括：
    - 主题模式
    - 语言设置
    - 货币设置
    - 日期时间格式
    - 显示选项
    - 通知设置
    - 默认值设置
    """
    try:
        preferences = await personalization_service.get_user_preferences(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "data": preferences
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取偏好设置失败: {str(e)}"
        )


@router.put("/preferences")
async def update_preferences(
    request: PreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    更新用户偏好设置
    
    支持部分更新，只更新提供的字段
    """
    try:
        # 构建更新数据
        update_data = {}
        
        if request.theme_mode is not None:
            update_data["theme_mode"] = request.theme_mode
        
        if request.language is not None:
            update_data["language"] = request.language
        
        if request.currency is not None:
            update_data["currency"] = request.currency
        
        if request.date_format is not None:
            update_data["date_format"] = request.date_format
        
        if request.time_format is not None:
            update_data["time_format"] = request.time_format
        
        if request.first_day_of_week is not None:
            update_data["first_day_of_week"] = request.first_day_of_week
        
        if request.show_expense_details is not None:
            update_data["show_expense_details"] = request.show_expense_details
        
        if request.show_budget_progress is not None:
            update_data["show_budget_progress"] = request.show_budget_progress
        
        if request.enable_analytics is not None:
            update_data["enable_analytics"] = request.enable_analytics
        
        if request.enable_notifications is not None:
            update_data["enable_notifications"] = request.enable_notifications
        
        if request.notification_types is not None:
            update_data["notification_types"] = request.notification_types
        
        if request.default_category is not None:
            update_data["default_category"] = request.default_category
        
        if request.default_payment_method is not None:
            update_data["default_payment_method"] = request.default_payment_method
        
        if request.monthly_budget_limit is not None:
            update_data["monthly_budget_limit"] = request.monthly_budget_limit
        
        if request.savings_goal is not None:
            update_data["savings_goal"] = request.savings_goal
        
        # 如果没有提供任何更新字段
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供任何更新字段"
            )
        
        result = await personalization_service.update_user_preferences(
            user_id=current_user["id"],
            preferences=update_data
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "更新失败")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新偏好设置失败: {str(e)}"
        )


@router.post("/preferences/reset")
async def reset_preferences(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    重置用户偏好设置为默认值
    """
    try:
        result = await personalization_service.reset_user_preferences(
            user_id=current_user["id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "重置失败")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置偏好设置失败: {str(e)}"
        )


@router.get("/theme")
async def get_theme(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取用户主题设置
    
    返回用户当前的主题配置
    """
    try:
        theme = await personalization_service.get_user_theme(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "data": theme
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取主题设置失败: {str(e)}"
        )


@router.put("/theme")
async def update_theme(
    request: ThemeUpdateRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    更新用户主题设置
    
    支持部分更新，只更新提供的颜色字段
    """
    try:
        # 构建更新数据
        update_data = {}
        
        if request.primary_color is not None:
            update_data["primary_color"] = request.primary_color
        
        if request.secondary_color is not None:
            update_data["secondary_color"] = request.secondary_color
        
        if request.background_color is not None:
            update_data["background_color"] = request.background_color
        
        if request.text_color is not None:
            update_data["text_color"] = request.text_color
        
        if request.card_color is not None:
            update_data["card_color"] = request.card_color
        
        if request.icon_color is not None:
            update_data["icon_color"] = request.icon_color
        
        if request.use_custom_theme is not None:
            update_data["use_custom_theme"] = request.use_custom_theme
        
        # 如果没有提供任何更新字段
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供任何更新字段"
            )
        
        result = await personalization_service.update_user_theme(
            user_id=current_user["id"],
            theme=update_data
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "更新失败")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新主题设置失败: {str(e)}"
        )


@router.post("/theme/reset")
async def reset_theme(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    重置用户主题设置为默认值
    """
    try:
        result = await personalization_service.reset_user_theme(
            user_id=current_user["id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "重置失败")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置主题设置失败: {str(e)}"
        )


@router.get("/themes/presets")
async def get_preset_themes() -> Dict[str, Any]:
    """
    获取可用的预设主题
    
    返回所有可用的预设主题列表，包括预览效果
    """
    try:
        result = await personalization_service.get_available_themes()
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预设主题失败: {str(e)}"
        )


@router.post("/themes/presets/{theme_id}/apply")
async def apply_preset_theme(
    theme_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    应用预设主题
    
    将指定的预设主题应用到用户账户
    """
    try:
        result = await personalization_service.apply_preset_theme(
            user_id=current_user["id"],
            theme_id=theme_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "应用主题失败")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"应用预设主题失败: {str(e)}"
        )


@router.get("/options")
async def get_available_options() -> Dict[str, Any]:
    """
    获取可用的选项列表
    
    返回所有可用的选项，包括：
    - 主题模式
    - 语言
    - 货币
    - 日期格式
    - 时间格式
    - 通知类型
    """
    return {
        "success": True,
        "data": {
            "theme_modes": [
                {"value": "light", "label": "浅色模式"},
                {"value": "dark", "label": "深色模式"},
                {"value": "auto", "label": "自动"}
            ],
            "languages": [
                {"value": "zh_CN", "label": "简体中文"},
                {"value": "en_US", "label": "English"},
                {"value": "ja_JP", "label": "日本語"},
                {"value": "ko_KR", "label": "한국어"}
            ],
            "currencies": [
                {"value": "CNY", "label": "人民币 (¥)", "symbol": "¥"},
                {"value": "USD", "label": "美元 ($)", "symbol": "$"},
                {"value": "EUR", "label": "欧元 (€)", "symbol": "€"},
                {"value": "JPY", "label": "日元 (¥)", "symbol": "¥"},
                {"value": "KRW", "label": "韩元 (₩)", "symbol": "₩"}
            ],
            "date_formats": [
                {"value": "YYYY-MM-DD", "label": "2024-01-01", "example": "2024-01-01"},
                {"value": "DD/MM/YYYY", "label": "01/01/2024", "example": "01/01/2024"},
                {"value": "MM/DD/YYYY", "label": "01/01/2024", "example": "01/01/2024"}
            ],
            "time_formats": [
                {"value": "HH:mm", "label": "24小时制", "example": "14:30"},
                {"value": "hh:mm A", "label": "12小时制", "example": "2:30 PM"}
            ],
            "notification_types": [
                {"value": "budget_alert", "label": "预算提醒"},
                {"value": "expense_reminder", "label": "支出提醒"},
                {"value": "weekly_report", "label": "周报"},
                {"value": "monthly_report", "label": "月报"},
                {"value": "group_invitation", "label": "群组邀请"},
                {"value": "group_update", "label": "群组更新"},
                {"value": "system_update", "label": "系统更新"}
            ]
        }
    }