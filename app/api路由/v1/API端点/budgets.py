"""
预算管理API端点
Requirements: 3.1, 3.2, 8.1, 8.2
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal
import uuid

from app.core.database import get_db
from app.models.budget import Budget
from app.repositories.budget_repository import BudgetRepository
from app.services.budget_service import BudgetTemplateService

router = APIRouter()


class BudgetCreate(BaseModel):
    """创建预算请求"""
    user_id: str = Field(..., description="用户ID")
    category: str = Field(..., description="预算类别")
    total_amount: Decimal = Field(..., gt=0, description="总预算金额，必须大于0")
    period_start: datetime = Field(..., description="预算周期开始时间")
    period_end: datetime = Field(..., description="预算周期结束时间")
    is_flexible: bool = Field(False, description="是否允许灵活调整")
    flexibility_percentage: Decimal = Field(Decimal("0.0"), ge=0, le=100, description="灵活性百分比(0-100)")
    
    @validator('category')
    def validate_category(cls, v):
        """验证预算类别"""
        valid_categories = [
            'dining', 'transportation', 'entertainment', 'shopping', 'emergency',
            'education', 'stationery', 'bedding', 'study_materials', 
            'club_activities', 'event_materials'
        ]
        if v not in valid_categories:
            raise ValueError(f'类别必须是以下之一: {", ".join(valid_categories)}')
        return v
    
    @validator('period_end')
    def validate_period(cls, v, values):
        """验证预算周期"""
        if 'period_start' in values and v <= values['period_start']:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class BudgetUpdate(BaseModel):
    """更新预算请求"""
    total_amount: Optional[Decimal] = Field(None, gt=0, description="总预算金额")
    period_end: Optional[datetime] = Field(None, description="预算周期结束时间")
    is_flexible: Optional[bool] = Field(None, description="是否允许灵活调整")
    flexibility_percentage: Optional[Decimal] = Field(None, ge=0, le=100, description="灵活性百分比")


class BudgetResponse(BaseModel):
    """预算响应"""
    id: str
    user_id: str
    category: str
    total_amount: Decimal
    remaining_amount: Decimal
    period_start: datetime
    period_end: datetime
    is_flexible: bool
    flexibility_percentage: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class BudgetAlert(BaseModel):
    """预算提醒"""
    category: str
    alert_type: str  # "warning", "danger", "overspend"
    message: str
    remaining_amount: Decimal
    percentage_used: Decimal


class RemainingBudgetResponse(BaseModel):
    """剩余预算响应"""
    budget_id: str
    category: str
    remaining_amount: Decimal
    percentage_remaining: Decimal
    days_remaining: int


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED, summary="创建预算")
async def create_budget(
    budget: BudgetCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新预算
    Requirements: 3.1, 3.2, 8.1
    
    - 验证用户ID和数据格式
    - 支持场景和身份模板配置
    - 自动设置剩余金额等于总金额
    """
    try:
        try:
            uuid.UUID(budget.user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID格式"
            )
        
        repo = BudgetRepository(db)
        existing_budget = await repo.get_active_budget(
            user_id=budget.user_id,
            category=budget.category
        )
        
        if existing_budget:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"该类别已存在活跃的预算（ID: {existing_budget.id}）"
            )
        new_budget = await repo.create(
            user_id=budget.user_id,
            category=budget.category,
            total_amount=budget.total_amount,
            remaining_amount=budget.total_amount,
            period_start=budget.period_start,
            period_end=budget.period_end,
            is_flexible=budget.is_flexible,
            flexibility_percentage=budget.flexibility_percentage
        )
        
        return BudgetResponse(
            id=str(new_budget.id),
            user_id=str(new_budget.user_id),
            category=new_budget.category,
            total_amount=new_budget.total_amount,
            remaining_amount=new_budget.remaining_amount,
            period_start=new_budget.period_start,
            period_end=new_budget.period_end,
            is_flexible=new_budget.is_flexible,
            flexibility_percentage=new_budget.flexibility_percentage,
            created_at=new_budget.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建预算失败: {str(e)}"
        )


@router.get("/", response_model=List[BudgetResponse], summary="获取预算列表")
async def get_budgets(
    user_id: str,
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户预算列表
    Requirements: 8.1, 8.2
    
    - 支持按类别筛选
    - 支持仅显示活跃预算
    """
    try:
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID格式"
            )
        repo = BudgetRepository(db)
        budgets = await repo.get_by_user(
            user_id=user_id,
            category=category,
            active_only=active_only
        )
        
        return [
            BudgetResponse(
                id=str(b.id),
                user_id=str(b.user_id),
                category=b.category,
                total_amount=b.total_amount,
                remaining_amount=b.remaining_amount,
                period_start=b.period_start,
                period_end=b.period_end,
                is_flexible=b.is_flexible,
                flexibility_percentage=b.flexibility_percentage,
                created_at=b.created_at
            )
            for b in budgets
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预算列表失败: {str(e)}"
        )


@router.get("/{budget_id}/remaining", response_model=RemainingBudgetResponse, summary="获取剩余预算")
async def get_remaining_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取预算剩余金额
    Requirements: 8.1, 8.2
    
    - 计算剩余金额和百分比
    - 计算剩余天数
    """
    try:
        try:
            uuid.UUID(budget_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的预算ID格式"
            )
        repo = BudgetRepository(db)
        budget = await repo.get_by_id(budget_id)
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="预算不存在"
            )
        percentage_remaining = (budget.remaining_amount / budget.total_amount) * 100
        now = datetime.utcnow()
        days_remaining = (budget.period_end - now).days
        if days_remaining < 0:
            days_remaining = 0
        
        return RemainingBudgetResponse(
            budget_id=str(budget.id),
            category=budget.category,
            remaining_amount=budget.remaining_amount,
            percentage_remaining=percentage_remaining,
            days_remaining=days_remaining
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取剩余预算失败: {str(e)}"
        )


@router.post("/check-overspending", response_model=BudgetAlert, summary="检查超支")
async def check_overspending(
    user_id: str,
    category: str,
    amount: Decimal,
    db: AsyncSession = Depends(get_db)
):
    """
    检查是否会导致超支
    Requirements: 3.3, 8.2
    
    - 检查预算剩余情况
    - 提供早期预警
    - 考虑灵活性百分比
    """
    try:
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID格式"
            )
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="金额必须大于0"
            )
        repo = BudgetRepository(db)
        is_overspending, budget, percentage_used = await repo.check_overspending(
            user_id=user_id,
            category=category,
            amount=amount
        )
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到类别 '{category}' 的活跃预算"
            )
        new_remaining = budget.remaining_amount - amount
        if is_overspending:
            alert_type = "overspend"
            message = f"此次支出将超出预算！当前剩余: {budget.remaining_amount}元，支出: {amount}元"
        elif percentage_used >= 90:
            alert_type = "danger"
            message = f"预算即将耗尽！此次支出后将使用{percentage_used:.1f}%的预算"
        elif percentage_used >= 75:
            alert_type = "warning"
            message = f"预算使用较多，此次支出后将使用{percentage_used:.1f}%的预算"
        else:
            alert_type = "info"
            message = f"预算充足，此次支出后将使用{percentage_used:.1f}%的预算"
        
        return BudgetAlert(
            category=category,
            alert_type=alert_type,
            message=message,
            remaining_amount=new_remaining,
            percentage_used=percentage_used
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查超支失败: {str(e)}"
        )


@router.post("/reallocate", summary="预算调剂")
async def reallocate_budget(
    user_id: str,
    from_category: str,
    to_category: str,
    amount: Decimal,
    db: AsyncSession = Depends(get_db)
):
    """
    在预算类别间调剂资金
    Requirements: 3.5
    
    - 从一个类别转移预算到另一个类别
    - 验证源类别有足够的剩余预算
    - 更新两个类别的剩余金额
    """
    try:
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID格式"
            )
        
        # 验证金额
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="调剂金额必须大于0"
            )
        if from_category == to_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="源类别和目标类别不能相同"
            )
        
        repo = BudgetRepository(db)
        from_budget = await repo.get_active_budget(user_id=user_id, category=from_category)
        if not from_budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到类别 '{from_category}' 的活跃预算"
            )
        if from_budget.remaining_amount < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"源类别剩余预算不足。当前剩余: {from_budget.remaining_amount}元，需要: {amount}元"
            )
        to_budget = await repo.get_active_budget(user_id=user_id, category=to_category)
        if not to_budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到类别 '{to_category}' 的活跃预算"
            )
        new_from_remaining = from_budget.remaining_amount - amount
        await repo.update(str(from_budget.id), remaining_amount=new_from_remaining)
        new_to_remaining = to_budget.remaining_amount + amount
        new_to_total = to_budget.total_amount + amount
        await repo.update(
            str(to_budget.id),
            remaining_amount=new_to_remaining,
            total_amount=new_to_total
        )
        
        return {
            "message": "预算调剂成功",
            "from_category": from_category,
            "to_category": to_category,
            "amount": amount,
            "from_remaining": new_from_remaining,
            "to_remaining": new_to_remaining
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预算调剂失败: {str(e)}"
        )



@router.get("/templates/identities", summary="获取身份模板列表")
async def get_identity_templates():
    """
    获取所有可用的身份模板
    Requirements: 3.1, 3.2
    """
    return {
        "identities": BudgetTemplateService.get_available_identities(),
        "scenarios": BudgetTemplateService.get_available_scenarios()
    }


@router.get("/templates/student", summary="获取学生专属模板")
async def get_student_templates():
    """
    获取学生专属预算模板
    Requirements: 3.1, 3.2
    
    返回三种学生专属模板：
    - 开学季：预留文具/被褥预算
    - 考研模式：压缩娱乐预算至10%
    - 社团经费：按活动分批次拨款
    """
    try:
        student_templates = BudgetTemplateService.get_student_templates()
        base_budgets = BudgetTemplateService.get_template_by_identity("student")
        
        result = {}
        for template_name, adjustments in student_templates.items():
            adjusted_budgets = BudgetTemplateService.apply_scenario_adjustment(
                base_budgets, template_name
            )
            
            result[template_name] = {
                "description": _get_template_description(template_name),
                "budgets": {
                    category: float(amount)
                    for category, amount in adjusted_budgets.items()
                },
                "features": _get_template_features(template_name)
            }
        
        return {
            "student_templates": result,
            "base_student_budget": {
                category: float(amount)
                for category, amount in base_budgets.items()
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取学生模板失败: {str(e)}"
        )

def _get_template_description(template_name: str) -> str:
    """获取模板描述"""
    descriptions = {
        "开学季": "为新学期准备，预留文具和被褥等必需品预算，适当减少娱乐支出",
        "考研模式": "专注学习，大幅压缩娱乐预算至10%，增加学习资料和营养补充预算",
        "社团经费": "参与社团活动，增加聚餐、出行和活动物料预算，支持分批次拨款管理"
    }
    return descriptions.get(template_name, "")

def _get_template_features(template_name: str) -> List[str]:
    """获取模板特色功能"""
    features = {
        "开学季": [
            "文具预算单独管理",
            "被褥等生活用品预算",
            "娱乐预算适度控制",
            "应急预算增加20%"
        ],
        "考研模式": [
            "娱乐预算压缩至10%",
            "学习资料预算增加150%",
            "营养补充预算增加10%",
            "专注学习目标导向"
        ],
        "社团经费": [
            "社团活动专项预算",
            "聚餐活动预算增加20%",
            "活动物料预算管理",
            "支持分批次拨款"
        ]
    }
    return features.get(template_name, [])


@router.get("/templates/recommended", summary="获取推荐预算配置")
async def get_recommended_budget(
    identity: str,
    scenario: str = "日常"
):
    """
    根据身份和场景获取推荐的预算配置
    Requirements: 3.1, 3.2
    
    - 支持学生、上班族、自由职业者等身份
    - 支持期末周、旅游季、节日等场景
    - 返回各类别的推荐预算金额
    """
    try:
        recommended_budgets = BudgetTemplateService.get_recommended_budget(
            identity=identity,
            scenario=scenario
        )
        
        period_start, period_end = BudgetTemplateService.get_budget_period("monthly")
        
        return {
            "identity": identity,
            "scenario": scenario,
            "budgets": {
                category: float(amount)
                for category, amount in recommended_budgets.items()
            },
            "suggested_period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            }
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取推荐预算失败: {str(e)}"
        )


@router.post("/templates/student/apply", summary="应用学生专属模板")
async def apply_student_template(
    user_id: str,
    template_name: str,
    period_type: str = "monthly",
    db: AsyncSession = Depends(get_db)
):
    """
    为用户应用学生专属预算模板
    Requirements: 3.1, 3.2
    
    - 自动创建各类别预算
    - 支持月度/周度周期
    - 一键应用模板配置
    """
    try:
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID格式"
            )
        if not BudgetTemplateService.is_student_template(template_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的学生模板: {template_name}"
            )
        recommended_budgets = BudgetTemplateService.get_recommended_budget(
            identity="student",
            scenario=template_name
        )
        period_start, period_end = BudgetTemplateService.get_budget_period(period_type)
        
        repo = BudgetRepository(db)
        created_budgets = []
        for category, amount in recommended_budgets.items():
            existing_budget = await repo.get_active_budget(
                user_id=user_id,
                category=category
            )
            if existing_budget:
                await repo.update(
                    str(existing_budget.id),
                    total_amount=amount,
                    remaining_amount=amount,
                    period_end=period_end
                )
                created_budgets.append({
                    "id": str(existing_budget.id),
                    "category": category,
                    "amount": float(amount),
                    "action": "updated"
                })
            else:
                new_budget = await repo.create(
                    user_id=user_id,
                    category=category,
                    total_amount=amount,
                    remaining_amount=amount,
                    period_start=period_start,
                    period_end=period_end,
                    is_flexible=True,
                    flexibility_percentage=Decimal("15.0")
                )
                created_budgets.append({
                    "id": str(new_budget.id),
                    "category": category,
                    "amount": float(amount),
                    "action": "created"
                })
        
        return {
            "message": f"成功应用学生模板: {template_name}",
            "template_name": template_name,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "budgets": created_budgets,
            "total_budget": float(sum(recommended_budgets.values())),
            "description": _get_template_description(template_name),
            "features": _get_template_features(template_name)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"应用学生模板失败: {str(e)}"
        )
