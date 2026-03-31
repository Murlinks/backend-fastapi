"""
监控API端点
提供系统监控指标、告警信息、健康状态等接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.services.monitoring_service import monitoring_service
from app.middleware.auth import get_current_user

router = APIRouter()


@router.get("/metrics")
async def get_metrics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取系统指标摘要
    
    返回系统运行的关键指标，包括：
    - 活跃告警数量
    - 最近告警数量
    - 系统性能指标
    - 告警规则状态
    """
    try:
        summary = monitoring_service.get_metrics_summary()
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取指标失败: {str(e)}"
        )


@router.get("/alerts")
async def get_alerts(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取告警信息
    
    Args:
        limit: 返回的告警数量限制
    
    返回告警摘要，包括：
    - 活跃告警总数
    - 按严重级别分组的告警
    - 最近24小时的告警数量
    - 最近告警列表
    """
    try:
        summary = monitoring_service.get_alerts_summary()
        
        # 获取活跃告警详情
        active_alerts = monitoring_service.alert_manager.get_active_alerts()
        
        return {
            "success": True,
            "data": {
                **summary,
                "active_alerts": [
                    {
                        "id": alert.id,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "description": alert.description,
                        "metric_name": alert.metric_name,
                        "current_value": alert.current_value,
                        "threshold": alert.threshold,
                        "timestamp": alert.timestamp.isoformat(),
                        "metadata": alert.metadata
                    }
                    for alert in active_alerts[-limit:]
                ]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取告警失败: {str(e)}"
        )


@router.get("/alerts/history")
async def get_alert_history(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取告警历史
    
    Args:
        limit: 返回的历史记录数量限制
    
    返回历史告警记录
    """
    try:
        history = monitoring_service.alert_manager.get_alert_history(limit)
        
        return {
            "success": True,
            "data": {
                "total": len(history),
                "alerts": [
                    {
                        "id": alert.id,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "description": alert.description,
                        "metric_name": alert.metric_name,
                        "current_value": alert.current_value,
                        "threshold": alert.threshold,
                        "timestamp": alert.timestamp.isoformat(),
                        "metadata": alert.metadata
                    }
                    for alert in history
                ]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取告警历史失败: {str(e)}"
        )


@router.delete("/alerts/{alert_id}")
async def clear_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    清除指定告警
    
    Args:
        alert_id: 告警ID
    """
    try:
        monitoring_service.alert_manager.clear_alert(alert_id)
        
        return {
            "success": True,
            "message": f"告警 {alert_id} 已清除"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除告警失败: {str(e)}"
        )


@router.delete("/alerts")
async def clear_all_alerts(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    清除所有告警
    """
    try:
        monitoring_service.alert_manager.clear_all_alerts()
        
        return {
            "success": True,
            "message": "所有告警已清除"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除告警失败: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点
    
    返回系统健康状态，包括：
    - 整体状态
    - 数据库连接状态
    - Redis连接状态
    - 监控服务状态
    """
    from app.core.database import engine
    from app.core.redis import redis_client
    
    health_status = {
        "status": "healthy",
        "timestamp": None,
        "checks": {}
    }
    
    try:
        from datetime import datetime
        health_status["timestamp"] = datetime.utcnow().isoformat()
        
        # 检查数据库连接
        try:
            await engine.connect()
            health_status["checks"]["database"] = {
                "status": "healthy",
                "message": "数据库连接正常"
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": f"数据库连接失败: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查Redis连接
        try:
            await redis_client.ping()
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "message": "Redis连接正常"
            }
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "message": f"Redis连接失败: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查监控服务
        try:
            monitoring_status = monitoring_service.get_metrics_summary()
            health_status["checks"]["monitoring"] = {
                "status": "healthy",
                "message": "监控服务运行正常",
                "active_alerts": monitoring_status.get("active_alerts", 0)
            }
        except Exception as e:
            health_status["checks"]["monitoring"] = {
                "status": "unhealthy",
                "message": f"监控服务异常: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 如果有任何检查失败，整体状态为degraded
        if any(
            check["status"] == "unhealthy"
            for check in health_status["checks"].values()
        ):
            health_status["status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": None,
            "error": str(e)
        }


@router.get("/performance")
async def get_performance_metrics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取性能指标
    
    返回详细的性能指标，包括：
    - HTTP请求统计
    - 数据库查询性能
    - 缓存命中率
    - AI服务性能
    - 系统资源使用
    """
    try:
        metrics = monitoring_service.metrics_collector
        
        # 收集HTTP请求指标
        http_metrics = {}
        for metric in metrics.http_requests_total.collect():
            for sample in metric.samples:
                key = f"{sample.labels['method']}_{sample.labels['endpoint']}_{sample.labels['status']}"
                http_metrics[key] = sample.value
        
        # 收集缓存指标
        cache_metrics = {}
        for cache_type in ["user_expenses", "budget_summary", "ai_response"]:
            hits = metrics.cache_hits.labels(cache_type=cache_type)._value.get() or 0
            misses = metrics.cache_misses.labels(cache_type=cache_type)._value.get() or 0
            total = hits + misses
            cache_metrics[cache_type] = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": hits / total if total > 0 else 0
            }
        
        # 收集系统指标
        system_metrics = {
            "memory_usage_bytes": metrics.system_memory_usage._value.get(),
            "cpu_usage_percent": metrics.system_cpu_usage._value.get()
        }
        
        return {
            "success": True,
            "data": {
                "http_requests": http_metrics,
                "cache": cache_metrics,
                "system": system_metrics
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能指标失败: {str(e)}"
        )