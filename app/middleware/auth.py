"""
认证中间件
"""
from fastapi import Request, HTTPException, status, Depends, WebSocket, WebSocketException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import logging

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT认证中间件"""
    
    # 不需要认证的路径
    EXCLUDED_PATHS = (
        "/docs",
        "/docs/",
        "/redoc",
        "/redoc/",
        "/openapi.json",
        "/health",
        "/api/v1/auth/send-code",
        "/api/v1/auth/verify-code",
    )
    
    async def dispatch(self, request: Request, call_next):
        """处理请求认证"""
        
        # 检查是否需要认证
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # 获取Authorization头
        authorization = request.headers.get("Authorization")
        if not authorization:
            return self._unauthorized_response("缺少认证令牌")
        
        try:
            # 验证JWT token
            token = authorization.replace("Bearer ", "")
            payload = self._verify_token(token)
            
            # 将用户信息添加到请求上下文
            request.state.user_id = payload.get("user_id")
            request.state.user_phone = payload.get("phone_number")
            
        except jwt.ExpiredSignatureError:
            return self._unauthorized_response("令牌已过期")
        except jwt.InvalidTokenError:
            return self._unauthorized_response("无效的令牌")
        except Exception as e:
            logger.error(f"认证中间件错误: {e}")
            return self._unauthorized_response("认证失败")
        
        return await call_next(request)
    
    def _should_skip_auth(self, path: str) -> bool:
        """检查路径是否需要跳过认证（仅白名单路径，勿使用 /api/v1/ 前缀匹配整树）"""
        return path in self.EXCLUDED_PATHS or path.rstrip("/") in self.EXCLUDED_PATHS
    
    def _verify_token(self, token: str) -> dict:
        """验证JWT token"""
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
    
    def _unauthorized_response(self, message: str) -> Response:
        """返回未授权响应"""
        return Response(
            content=f'{{"detail": "{message}"}}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"Content-Type": "application/json"}
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前认证用户"""
    try:
        # 验证JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )
        
        # 从数据库获取用户信息
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )


async def get_current_user_websocket(websocket: WebSocket) -> User:
    """WebSocket连接的用户认证"""
    try:
        # 从查询参数获取token
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="缺少认证令牌")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="缺少认证令牌")
        
        # 验证JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的令牌")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="无效的令牌")
        
        # 从数据库获取用户信息
        async for db in get_db():
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户不存在")
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="用户不存在")
            
            return user
        
    except jwt.ExpiredSignatureError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="令牌已过期")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="令牌已过期")
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的令牌")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="无效的令牌")