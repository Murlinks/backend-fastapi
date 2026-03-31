"""
移动端全场景 AI 财务助手APP - FastAPI 主应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis
import importlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    router_module = importlib.import_module('app.api路由.v1.router（路由配置）')
    api_router = router_module.api_router
except ImportError as e:
    print(f"导入路由模块失败: {e}")
    from fastapi import APIRouter
    api_router = APIRouter()

from app.middleware.auth import AuthMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.monitoring import MonitoringMiddleware

from app.models.user import User
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.group import Group, GroupMember, ExpenseSplit
from app.models.conversation import AIConversation
from app.models.payment_authorization import PaymentAuthorization

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在初始化数据库连接...")
    await init_db()
    
    logger.info("正在初始化Redis连接...")
    await init_redis()
    if settings.ENVIRONMENT != "test":
        logger.info("正在初始化监控服务...")
        from app.services.monitoring_service import monitoring_service
        await monitoring_service.start()
    if settings.INTEGRATIONS_ENABLED:
        logger.info("正在初始化第三方集成...")
        from app.integrations import setup_integrations
        await setup_integrations()
    
    logger.info("应用启动完成")
    yield
    logger.info("正在关闭应用...")
    if settings.ENVIRONMENT != "test":
        logger.info("正在停止监控服务...")
        from app.services.monitoring_service import monitoring_service
        await monitoring_service.stop()
    if settings.INTEGRATIONS_ENABLED:
        logger.info("正在清理第三方集成...")
        from app.integrations import cleanup_integrations
        await cleanup_integrations()


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title="移动端全场景 AI 财务助手",
        description="基于DeepSeek大模型的智能财务管理应用",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    _cors = dict(
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.CORS_ALLOW_LAN_REGEX:
        _cors["allow_origin_regex"] = settings.cors_lan_origin_regex
    app.add_middleware(CORSMiddleware, **_cors)
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )
    
    app.add_middleware(AuthMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MonitoringMiddleware)
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {"status": "healthy", "version": "1.0.0"}
    
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )