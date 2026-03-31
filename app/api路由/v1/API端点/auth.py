"""认证相关API端点"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import re
import logging

from app.core.database import get_db
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


class PhoneLoginRequest(BaseModel):
    """手机号登录请求"""
    phone_number: str = Field(..., description="手机号码", example="13800138000")
    
    @property
    def is_valid_phone(self) -> bool:
        """验证手机号格式"""
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, self.phone_number))


class VerifyCodeRequest(BaseModel):
    """验证码验证请求"""
    phone_number: str = Field(..., description="手机号码", example="13800138000")
    verification_code: str = Field(..., description="验证码", example="123456")
    identity: str = Field(default="student", description="用户身份", example="student")


class AuthResponse(BaseModel):
    """认证响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    phone_number: str
    identity: str


@router.post("/send-code", summary="发送验证码")
async def send_verification_code(
    request: PhoneLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """发送短信验证码，6位数字，有效期5分钟"""
    if not request.is_valid_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号格式不正确"
        )
    
    try:
        code = await AuthService.generate_verification_code()
        success = await AuthService.send_sms_code(request.phone_number, code)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="验证码发送失败，请稍后重试"
            )
        
        logger.info(f"验证码已发送到 {request.phone_number}")
        
        resp = {
            "message": "验证码已发送",
            "phone_number": request.phone_number,
            "expires_in": 300,
        }
        from app.core.config import settings
        if settings.DEBUG:
            resp["code"] = code
        return resp
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送验证码异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器错误"
        )


@router.post("/verify-code", response_model=AuthResponse, summary="验证登录")
async def verify_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """验证验证码并登录/注册，返回JWT"""
    try:
        is_valid = await AuthService.verify_sms_code(
            request.phone_number,
            request.verification_code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码无效或已过期"
            )
        user = await AuthService.get_or_create_user(
            db,
            request.phone_number,
            request.identity
        )
        access_token = AuthService.create_access_token(
            str(user.id),
            user.phone_number
        )
        
        logger.info(f"用户认证成功: {user.phone_number}")
        
        return AuthResponse(
            access_token=access_token,
            user_id=str(user.id),
            phone_number=user.phone_number,
            identity=user.identity
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证登录异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器错误"
        )


@router.post("/refresh", response_model=AuthResponse, summary="刷新令牌")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """刷新访问令牌"""
    try:
        payload = AuthService.verify_access_token(credentials.credentials)
        user = await AuthService.get_user_by_id(db, payload["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        new_token = AuthService.create_access_token(
            str(user.id),
            user.phone_number
        )
        
        return AuthResponse(
            access_token=new_token,
            user_id=str(user.id),
            phone_number=user.phone_number,
            identity=user.identity
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"刷新令牌异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器错误"
        )


@router.post("/logout", summary="退出登录")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """用户退出登录"""
    try:
        logger.info("用户退出登录")
        
        return {"message": "退出登录成功"}
        
    except Exception as e:
        logger.error(f"退出登录异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器错误"
        )