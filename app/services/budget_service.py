"""
预算管理服务
Requirements: 3.1, 3.2, 8.1, 8.2
"""
from typing import Dict, List
from decimal import Decimal
from datetime import datetime, timedelta


class BudgetTemplateService:
    """预算模板服务 - 支持场景和身份模板配置"""
    
    # 身份模板 (Requirements: 3.1, 3.2)
    IDENTITY_TEMPLATES = {
        "student": {
            "dining": Decimal("800.00"),
            "transportation": Decimal("200.00"),
            "entertainment": Decimal("300.00"),
            "shopping": Decimal("400.00"),
            "emergency": Decimal("300.00")
        },
        "office_worker": {
            "dining": Decimal("1500.00"),
            "transportation": Decimal("500.00"),
            "entertainment": Decimal("800.00"),
            "shopping": Decimal("1000.00"),
            "emergency": Decimal("500.00")
        },
        "freelancer": {
            "dining": Decimal("1200.00"),
            "transportation": Decimal("400.00"),
            "entertainment": Decimal("600.00"),
            "shopping": Decimal("800.00"),
            "emergency": Decimal("600.00")
        }
    }
    
    # 场景模板 (Requirements: 3.1, 3.2)
    SCENARIO_TEMPLATES = {
        "期末周": {
            "dining": 0.8,  # 减少20%
            "transportation": 1.0,
            "entertainment": 0.5,  # 减少50%
            "shopping": 0.6,  # 减少40%
            "emergency": 1.2  # 增加20%
        },
        "旅游季": {
            "dining": 1.5,  # 增加50%
            "transportation": 2.0,  # 增加100%
            "entertainment": 1.8,  # 增加80%
            "shopping": 1.3,  # 增加30%
            "emergency": 1.5  # 增加50%
        },
        "节日": {
            "dining": 1.3,
            "transportation": 1.2,
            "entertainment": 1.5,
            "shopping": 1.8,
            "emergency": 1.0
        },
        "日常": {
            "dining": 1.0,
            "transportation": 1.0,
            "entertainment": 1.0,
            "shopping": 1.0,
            "emergency": 1.0
        }
    }
    
    # 学生专属模板 (Requirements: 3.1, 3.2)
    STUDENT_TEMPLATES = {
        "开学季": {
            "dining": 1.0,
            "transportation": 1.0,
            "entertainment": 0.8,  # 减少20%
            "shopping": 1.5,  # 增加50% (文具、被褥等)
            "emergency": 1.2,  # 增加20%
            "education": 2.0,  # 新增教育类别，增加100%
            "stationery": 3.0,  # 新增文具类别
            "bedding": 2.5  # 新增被褥类别
        },
        "考研模式": {
            "dining": 1.1,  # 增加10% (营养补充)
            "transportation": 0.9,  # 减少10%
            "entertainment": 0.1,  # 压缩至10%
            "shopping": 0.7,  # 减少30%
            "emergency": 1.0,
            "education": 1.8,  # 增加80% (考研资料)
            "study_materials": 2.5  # 新增学习资料类别
        },
        "社团经费": {
            "dining": 1.2,  # 增加20% (聚餐活动)
            "transportation": 1.3,  # 增加30% (活动出行)
            "entertainment": 1.5,  # 增加50% (社团活动)
            "shopping": 1.1,  # 增加10%
            "emergency": 1.0,
            "club_activities": 2.0,  # 新增社团活动类别
            "event_materials": 1.8  # 新增活动物料类别
        }
    }
    
    @classmethod
    def get_template_by_identity(cls, identity: str) -> Dict[str, Decimal]:
        """
        根据身份获取预算模板
        Requirements: 3.1, 3.2
        """
        if identity not in cls.IDENTITY_TEMPLATES:
            raise ValueError(f"不支持的身份类型: {identity}")
        
        return cls.IDENTITY_TEMPLATES[identity].copy()
    
    @classmethod
    def apply_scenario_adjustment(
        cls,
        base_budgets: Dict[str, Decimal],
        scenario: str
    ) -> Dict[str, Decimal]:
        """
        应用场景调整到基础预算
        Requirements: 3.1, 3.2
        """
        # 检查是否为学生专属模板
        if scenario in cls.STUDENT_TEMPLATES:
            adjustments = cls.STUDENT_TEMPLATES[scenario]
        elif scenario in cls.SCENARIO_TEMPLATES:
            adjustments = cls.SCENARIO_TEMPLATES[scenario]
        else:
            raise ValueError(f"不支持的场景类型: {scenario}")
        
        adjusted_budgets = {}
        
        for category, base_amount in base_budgets.items():
            multiplier = adjustments.get(category, 1.0)
            adjusted_budgets[category] = base_amount * Decimal(str(multiplier))
        
        # 为学生专属模板添加新类别
        if scenario in cls.STUDENT_TEMPLATES:
            for category, multiplier in adjustments.items():
                if category not in base_budgets:
                    # 为新类别设置基础金额
                    base_amount = cls._get_base_amount_for_new_category(category)
                    adjusted_budgets[category] = base_amount * Decimal(str(multiplier))
        
        return adjusted_budgets
    
    @classmethod
    def _get_base_amount_for_new_category(cls, category: str) -> Decimal:
        """为新类别获取基础金额"""
        category_base_amounts = {
            "education": Decimal("500.00"),
            "stationery": Decimal("200.00"),
            "bedding": Decimal("300.00"),
            "study_materials": Decimal("400.00"),
            "club_activities": Decimal("600.00"),
            "event_materials": Decimal("300.00")
        }
        return category_base_amounts.get(category, Decimal("200.00"))
    
    @classmethod
    def get_recommended_budget(
        cls,
        identity: str,
        scenario: str = "日常"
    ) -> Dict[str, Decimal]:
        """
        获取推荐的预算配置
        Requirements: 3.1, 3.2
        
        Args:
            identity: 用户身份 (student, office_worker, freelancer)
            scenario: 场景 (期末周, 旅游季, 节日, 日常)
        
        Returns:
            各类别的推荐预算金额
        """
        base_budgets = cls.get_template_by_identity(identity)
        return cls.apply_scenario_adjustment(base_budgets, scenario)
    
    @classmethod
    def get_budget_period(cls, period_type: str = "monthly") -> tuple[datetime, datetime]:
        """
        获取预算周期的开始和结束时间
        
        Args:
            period_type: 周期类型 (monthly, weekly, custom)
        
        Returns:
            (period_start, period_end)
        """
        now = datetime.utcnow()
        
        if period_type == "monthly":
            # 当月第一天到最后一天
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 下个月第一天减一天
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            
            period_end = next_month - timedelta(days=1)
            period_end = period_end.replace(hour=23, minute=59, second=59)
        
        elif period_type == "weekly":
            # 本周一到周日
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            period_end = period_start + timedelta(days=6)
            period_end = period_end.replace(hour=23, minute=59, second=59)
        
        else:
            # 默认30天
            period_start = now
            period_end = now + timedelta(days=30)
        
        return period_start, period_end
    
    @classmethod
    def get_available_identities(cls) -> List[str]:
        """获取所有可用的身份类型"""
        return list(cls.IDENTITY_TEMPLATES.keys())
    
    @classmethod
    def get_available_scenarios(cls) -> List[str]:
        """获取所有可用的场景类型"""
        return list(cls.SCENARIO_TEMPLATES.keys()) + list(cls.STUDENT_TEMPLATES.keys())
    
    @classmethod
    def get_student_templates(cls) -> Dict[str, Dict[str, float]]:
        """获取学生专属模板"""
        return cls.STUDENT_TEMPLATES
    
    @classmethod
    def is_student_template(cls, scenario: str) -> bool:
        """检查是否为学生专属模板"""
        return scenario in cls.STUDENT_TEMPLATES
