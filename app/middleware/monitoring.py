"""
监控中间件
自动收集HTTP请求指标并记录到监控系统
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """监控中间件"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 记录指标
        try:
            # 获取路由信息
            route = request.scope.get("route")
            endpoint = getattr(route, "path", request.url.path) if route else request.url.path
            
            # 记录HTTP请求指标
            monitoring_service.metrics_collector.record_http_request(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
                duration=process_time
            )
            
            # 添加响应头
            response.headers["X-Process-Time"] = str(process_time)
            
        except Exception as e:
            logger.error(f"记录监控指标失败: {e}")
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        # 记录请求信息
        logger.info(f"请求开始: {request.method} {request.url.path}")
        
        # 处理请求
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"请求完成: {request.method} {request.url.path} "
                f"状态码: {response.status_code} "
                f"耗时: {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"请求失败: {request.method} {request.url.path} "
                f"错误: {str(e)} "
                f"耗时: {process_time:.3f}s"
            )
            raise