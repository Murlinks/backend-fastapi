"""
用户反馈API端点
提供用户反馈提交、查询、状态更新等接口
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.services.feedback_service import feedback_service, FeedbackType, FeedbackStatus
from app.middleware.auth import get_current_user

router = APIRouter()


class FeedbackSubmitRequest(BaseModel):
    """反馈提交请求"""
    feedback_type: str = Field(..., description="反馈类型: bug_report, feature_request, improvement, complaint, compliment, other")
    title: str = Field(..., min_length=1, max_length=200, description="反馈标题")
    description: str = Field(..., min_length=1, max_length=2000, description="反馈描述")
    category: Optional[str] = Field(None, description="反馈分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    screenshots: Optional[List[str]] = Field(None, description="截图URL列表")
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")
    app_version: Optional[str] = Field(None, description="应用版本")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class FeedbackUpdateRequest(BaseModel):
    """反馈更新请求"""
    status: str = Field(..., description="新状态: pending, reviewing, in_progress, resolved, closed")
    resolution: Optional[str] = Field(None, description="解决方案说明")


@router.post("/submit")
async def submit_feedback(
    request: FeedbackSubmitRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    提交用户反馈
    
    用户可以提交各种类型的反馈，包括：
    - bug_report: 错误报告
    - feature_request: 功能请求
    - improvement: 改进建议
    - complaint: 投诉
    - compliment: 表扬
    - other: 其他
    """
    try:
        result = await feedback_service.submit_feedback(
            user_id=current_user["id"],
            feedback_type=request.feedback_type,
            title=request.title,
            description=request.description,
            category=request.category,
            tags=request.tags,
            screenshots=request.screenshots,
            device_info=request.device_info,
            app_version=request.app_version,
            metadata=request.metadata
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "提交反馈失败")
            )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"参数错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交反馈失败: {str(e)}"
        )


@router.get("/{feedback_id}")
async def get_feedback(
    feedback_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取反馈详情
    
    用户只能查看自己提交的反馈
    """
    try:
        feedback = await feedback_service.get_feedback(feedback_id)
        
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="反馈不存在"
            )
        
        # 检查权限
        if feedback["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此反馈"
            )
        
        return {
            "success": True,
            "data": feedback
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取反馈失败: {str(e)}"
        )


@router.get("/")
async def list_feedback(
    feedback_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    列出用户反馈
    
    用户可以查看自己提交的所有反馈，支持按类型、状态、优先级、分类过滤
    """
    try:
        result = await feedback_service.list_feedback(
            user_id=current_user["id"],
            feedback_type=feedback_type,
            status=status,
            priority=priority,
            category=category,
            limit=limit,
            offset=offset
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取反馈列表失败: {str(e)}"
        )


@router.put("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: str,
    request: FeedbackUpdateRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    更新反馈状态
    
    用户可以更新自己提交的反馈状态
    """
    try:
        # 先检查反馈是否存在
        feedback = await feedback_service.get_feedback(feedback_id)
        
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="反馈不存在"
            )
        
        # 检查权限
        if feedback["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此反馈"
            )
        
        result = await feedback_service.update_feedback_status(
            feedback_id=feedback_id,
            status=request.status,
            resolution=request.resolution
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "更新失败")
            )
        
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"参数错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新反馈状态失败: {str(e)}"
        )


@router.get("/statistics/summary")
async def get_feedback_statistics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取反馈统计信息
    
    返回用户反馈的统计信息，包括：
    - 按类型统计
    - 按状态统计
    - 按优先级统计
    - 按分类统计
    - 解决率
    """
    try:
        result = await feedback_service.get_feedback_statistics(days=days)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.get("/statistics/trends")
async def get_feedback_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取反馈趋势
    
    返回反馈趋势数据，包括：
    - 每日反馈数量
    - 按类型的趋势
    """
    try:
        result = await feedback_service.get_feedback_trends(days=days)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取趋势数据失败: {str(e)}"
        )


@router.get("/types")
async def get_feedback_types() -> Dict[str, Any]:
    """
    获取反馈类型列表
    
    返回所有可用的反馈类型及其说明
    """
    return {
        "success": True,
        "data": {
            "types": [
                {
                    "value": "bug_report",
                    "label": "错误报告",
                    "description": "报告应用中的错误或异常"
                },
                {
                    "value": "feature_request",
                    "label": "功能请求",
                    "description": "建议添加新功能"
                },
                {
                    "value": "improvement",
                    "label": "改进建议",
                    "description": "对现有功能提出改进建议"
                },
                {
                    "value": "complaint",
                    "label": "投诉",
                    "description": "表达不满或投诉"
                },
                {
                    "value": "compliment",
                    "label": "表扬",
                    "description": "表扬或感谢"
                },
                {
                    "value": "other",
                    "label": "其他",
                    "description": "其他类型的反馈"
                }
            ]
        }
    }


@router.get("/categories")
async def get_feedback_categories() -> Dict[str, Any]:
    """
    获取反馈分类列表
    
    返回所有可用的反馈分类
    """
    return {
        "success": True,
        "data": {
            "categories": [
                {"value": "ui", "label": "界面设计"},
                {"value": "performance", "label": "性能问题"},
                {"value": "feature", "label": "功能相关"},
                {"value": "bug", "label": "错误报告"},
                {"value": "ai", "label": "AI功能"},
                {"value": "voice", "label": "语音功能"},
                {"value": "sync", "label": "数据同步"},
                {"value": "other", "label": "其他"}
            ]
        }
    }