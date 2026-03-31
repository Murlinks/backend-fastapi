"""API v1 路由配置"""
from fastapi import APIRouter

from app.api路由.v1.API端点 import auth, users, expenses, budgets, groups, ai, sync, payments, integrations, monitoring, feedback, personalization
from app.api路由.v1.voice import router as voice_router

api_router = APIRouter()

api_router.include_router(auth, prefix="/auth", tags=["认证"])
api_router.include_router(users, prefix="/users", tags=["用户管理"])
api_router.include_router(expenses, prefix="/expenses", tags=["支出管理"])
api_router.include_router(budgets, prefix="/budgets", tags=["预算管理"])
api_router.include_router(groups, prefix="/groups", tags=["群组协作"])
api_router.include_router(ai, prefix="/ai", tags=["AI服务"])
api_router.include_router(sync, prefix="/sync", tags=["跨设备同步"])
api_router.include_router(payments, prefix="/payments", tags=["支付集成"])
api_router.include_router(integrations, prefix="/integrations", tags=["第三方集成管理"])
api_router.include_router(monitoring, prefix="/monitoring", tags=["系统监控"])
api_router.include_router(feedback, prefix="/feedback", tags=["用户反馈"])
api_router.include_router(personalization, prefix="/personalization", tags=["个性化设置"])
api_router.include_router(voice_router)

@api_router.get("/")
async def root():
    """API根路径"""
    return {
        "message": "移动端全场景 AI 财务助手 API",
        "version": "1.0.0",
        "docs": "/docs"
    }