"""
用户个性化服务
提供用户个性化设置、主题定制、偏好配置等功能
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class ThemeMode(Enum):
    """主题模式"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class Language(Enum):
    """语言设置"""
    ZH_CN = "zh_CN"
    EN_US = "en_US"
    JA_JP = "ja_JP"
    KO_KR = "ko_KR"


class Currency(Enum):
    """货币类型"""
    CNY = "CNY"
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    KRW = "KRW"


class NotificationType(Enum):
    """通知类型"""
    BUDGET_ALERT = "budget_alert"
    EXPENSE_REMINDER = "expense_reminder"
    WEEKLY_REPORT = "weekly_report"
    MONTHLY_REPORT = "monthly_report"
    GROUP_INVITATION = "group_invitation"
    GROUP_UPDATE = "group_update"
    SYSTEM_UPDATE = "system_update"


@dataclass
class UserPreferences:
    """用户偏好设置"""
    user_id: str
    theme_mode: ThemeMode = ThemeMode.AUTO
    language: Language = Language.ZH_CN
    currency: Currency = Currency.CNY
    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm"
    first_day_of_week: int = 1  # 1=Monday, 0=Sunday
    show_expense_details: bool = True
    show_budget_progress: bool = True
    enable_analytics: bool = True
    enable_notifications: bool = True
    notification_types: List[str] = field(default_factory=list)
    default_category: Optional[str] = None
    default_payment_method: Optional[str] = None
    monthly_budget_limit: Optional[float] = None
    savings_goal: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserTheme:
    """用户主题设置"""
    user_id: str
    primary_color: str = "#6200EE"
    secondary_color: str = "#03DAC6"
    background_color: str = "#FFFFFF"
    text_color: str = "#000000"
    card_color: str = "#FFFFFF"
    icon_color: str = "#6200EE"
    use_custom_theme: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class PersonalizationService:
    """个性化服务"""
    
    def __init__(self):
        self.preferences_store: Dict[str, UserPreferences] = {}
        self.themes_store: Dict[str, UserTheme] = {}
    
    async def get_user_preferences(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户偏好设置
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户偏好设置
        """
        preferences = self.preferences_store.get(user_id)
        if not preferences:
            # 创建默认偏好设置
            preferences = UserPreferences(user_id=user_id)
            self.preferences_store[user_id] = preferences
        
        return self._preferences_to_dict(preferences)
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新用户偏好设置
        
        Args:
            user_id: 用户ID
            preferences: 偏好设置
        
        Returns:
            更新结果
        """
        try:
            current = self.preferences_store.get(user_id)
            if not current:
                current = UserPreferences(user_id=user_id)
                self.preferences_store[user_id] = current
            
            # 更新字段
            if "theme_mode" in preferences:
                current.theme_mode = ThemeMode(preferences["theme_mode"])
            
            if "language" in preferences:
                current.language = Language(preferences["language"])
            
            if "currency" in preferences:
                current.currency = Currency(preferences["currency"])
            
            if "date_format" in preferences:
                current.date_format = preferences["date_format"]
            
            if "time_format" in preferences:
                current.time_format = preferences["time_format"]
            
            if "first_day_of_week" in preferences:
                current.first_day_of_week = preferences["first_day_of_week"]
            
            if "show_expense_details" in preferences:
                current.show_expense_details = preferences["show_expense_details"]
            
            if "show_budget_progress" in preferences:
                current.show_budget_progress = preferences["show_budget_progress"]
            
            if "enable_analytics" in preferences:
                current.enable_analytics = preferences["enable_analytics"]
            
            if "enable_notifications" in preferences:
                current.enable_notifications = preferences["enable_notifications"]
            
            if "notification_types" in preferences:
                current.notification_types = preferences["notification_types"]
            
            if "default_category" in preferences:
                current.default_category = preferences["default_category"]
            
            if "default_payment_method" in preferences:
                current.default_payment_method = preferences["default_payment_method"]
            
            if "monthly_budget_limit" in preferences:
                current.monthly_budget_limit = preferences["monthly_budget_limit"]
            
            if "savings_goal" in preferences:
                current.savings_goal = preferences["savings_goal"]
            
            current.updated_at = datetime.utcnow()
            
            logger.info(f"用户偏好设置已更新: {user_id}")
            
            return {
                "success": True,
                "message": "偏好设置已更新",
                "data": self._preferences_to_dict(current)
            }
            
        except Exception as e:
            logger.error(f"更新用户偏好设置失败: {e}")
            return {
                "success": False,
                "error": f"更新失败: {str(e)}"
            }
    
    async def get_user_theme(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户主题设置
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户主题设置
        """
        theme = self.themes_store.get(user_id)
        if not theme:
            # 创建默认主题
            theme = UserTheme(user_id=user_id)
            self.themes_store[user_id] = theme
        
        return self._theme_to_dict(theme)
    
    async def update_user_theme(
        self,
        user_id: str,
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新用户主题设置
        
        Args:
            user_id: 用户ID
            theme: 主题设置
        
        Returns:
            更新结果
        """
        try:
            current = self.themes_store.get(user_id)
            if not current:
                current = UserTheme(user_id=user_id)
                self.themes_store[user_id] = current
            
            # 更新字段
            if "primary_color" in theme:
                current.primary_color = theme["primary_color"]
            
            if "secondary_color" in theme:
                current.secondary_color = theme["secondary_color"]
            
            if "background_color" in theme:
                current.background_color = theme["background_color"]
            
            if "text_color" in theme:
                current.text_color = theme["text_color"]
            
            if "card_color" in theme:
                current.card_color = theme["card_color"]
            
            if "icon_color" in theme:
                current.icon_color = theme["icon_color"]
            
            if "use_custom_theme" in theme:
                current.use_custom_theme = theme["use_custom_theme"]
            
            current.updated_at = datetime.utcnow()
            
            logger.info(f"用户主题设置已更新: {user_id}")
            
            return {
                "success": True,
                "message": "主题设置已更新",
                "data": self._theme_to_dict(current)
            }
            
        except Exception as e:
            logger.error(f"更新用户主题设置失败: {e}")
            return {
                "success": False,
                "error": f"更新失败: {str(e)}"
            }
    
    async def reset_user_preferences(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        重置用户偏好设置为默认值
        
        Args:
            user_id: 用户ID
        
        Returns:
            重置结果
        """
        try:
            # 创建默认偏好设置
            default_preferences = UserPreferences(user_id=user_id)
            self.preferences_store[user_id] = default_preferences
            
            logger.info(f"用户偏好设置已重置: {user_id}")
            
            return {
                "success": True,
                "message": "偏好设置已重置为默认值",
                "data": self._preferences_to_dict(default_preferences)
            }
            
        except Exception as e:
            logger.error(f"重置用户偏好设置失败: {e}")
            return {
                "success": False,
                "error": f"重置失败: {str(e)}"
            }
    
    async def reset_user_theme(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        重置用户主题设置为默认值
        
        Args:
            user_id: 用户ID
        
        Returns:
            重置结果
        """
        try:
            # 创建默认主题
            default_theme = UserTheme(user_id=user_id)
            self.themes_store[user_id] = default_theme
            
            logger.info(f"用户主题设置已重置: {user_id}")
            
            return {
                "success": True,
                "message": "主题设置已重置为默认值",
                "data": self._theme_to_dict(default_theme)
            }
            
        except Exception as e:
            logger.error(f"重置用户主题设置失败: {e}")
            return {
                "success": False,
                "error": f"重置失败: {str(e)}"
            }
    
    async def get_available_themes(self) -> Dict[str, Any]:
        """
        获取可用的预设主题
        
        Returns:
            预设主题列表
        """
        return {
            "success": True,
            "data": {
                "themes": [
                    {
                        "id": "default",
                        "name": "默认主题",
                        "description": "系统默认主题",
                        "preview": {
                            "primary_color": "#6200EE",
                            "secondary_color": "#03DAC6",
                            "background_color": "#FFFFFF",
                            "text_color": "#000000"
                        }
                    },
                    {
                        "id": "dark",
                        "name": "暗色主题",
                        "description": "适合夜间使用的暗色主题",
                        "preview": {
                            "primary_color": "#BB86FC",
                            "secondary_color": "#03DAC6",
                            "background_color": "#121212",
                            "text_color": "#FFFFFF"
                        }
                    },
                    {
                        "id": "ocean",
                        "name": "海洋主题",
                        "description": "清新的海洋风格主题",
                        "preview": {
                            "primary_color": "#2196F3",
                            "secondary_color": "#00BCD4",
                            "background_color": "#E3F2FD",
                            "text_color": "#0D47A1"
                        }
                    },
                    {
                        "id": "forest",
                        "name": "森林主题",
                        "description": "自然的森林风格主题",
                        "preview": {
                            "primary_color": "#4CAF50",
                            "secondary_color": "#8BC34A",
                            "background_color": "#E8F5E9",
                            "text_color": "#1B5E20"
                        }
                    },
                    {
                        "id": "sunset",
                        "name": "日落主题",
                        "description": "温暖的日落风格主题",
                        "preview": {
                            "primary_color": "#FF5722",
                            "secondary_color": "#FF9800",
                            "background_color": "#FFF3E0",
                            "text_color": "#BF360C"
                        }
                    }
                ]
            }
        }
    
    async def apply_preset_theme(
        self,
        user_id: str,
        theme_id: str
    ) -> Dict[str, Any]:
        """
        应用预设主题
        
        Args:
            user_id: 用户ID
            theme_id: 主题ID
        
        Returns:
            应用结果
        """
        try:
            # 获取预设主题
            themes_result = await self.get_available_themes()
            themes = themes_result["data"]["themes"]
            
            # 查找指定主题
            target_theme = None
            for theme in themes:
                if theme["id"] == theme_id:
                    target_theme = theme
                    break
            
            if not target_theme:
                return {
                    "success": False,
                    "error": "主题不存在"
                }
            
            # 应用主题
            preview = target_theme["preview"]
            result = await self.update_user_theme(
                user_id=user_id,
                theme={
                    "primary_color": preview["primary_color"],
                    "secondary_color": preview["secondary_color"],
                    "background_color": preview["background_color"],
                    "text_color": preview["text_color"],
                    "use_custom_theme": True
                }
            )
            
            if result["success"]:
                result["message"] = f"已应用{target_theme['name']}"
            
            return result
            
        except Exception as e:
            logger.error(f"应用预设主题失败: {e}")
            return {
                "success": False,
                "error": f"应用失败: {str(e)}"
            }
    
    def _preferences_to_dict(
        self,
        preferences: UserPreferences
    ) -> Dict[str, Any]:
        """将偏好设置转换为字典"""
        return {
            "user_id": preferences.user_id,
            "theme_mode": preferences.theme_mode.value,
            "language": preferences.language.value,
            "currency": preferences.currency.value,
            "date_format": preferences.date_format,
            "time_format": preferences.time_format,
            "first_day_of_week": preferences.first_day_of_week,
            "show_expense_details": preferences.show_expense_details,
            "show_budget_progress": preferences.show_budget_progress,
            "enable_analytics": preferences.enable_analytics,
            "enable_notifications": preferences.enable_notifications,
            "notification_types": preferences.notification_types,
            "default_category": preferences.default_category,
            "default_payment_method": preferences.default_payment_method,
            "monthly_budget_limit": preferences.monthly_budget_limit,
            "savings_goal": preferences.savings_goal,
            "created_at": preferences.created_at.isoformat(),
            "updated_at": preferences.updated_at.isoformat()
        }
    
    def _theme_to_dict(
        self,
        theme: UserTheme
    ) -> Dict[str, Any]:
        """将主题设置转换为字典"""
        return {
            "user_id": theme.user_id,
            "primary_color": theme.primary_color,
            "secondary_color": theme.secondary_color,
            "background_color": theme.background_color,
            "text_color": theme.text_color,
            "card_color": theme.card_color,
            "icon_color": theme.icon_color,
            "use_custom_theme": theme.use_custom_theme,
            "created_at": theme.created_at.isoformat(),
            "updated_at": theme.updated_at.isoformat()
        }


# 全局个性化服务实例
personalization_service = PersonalizationService()