"""
认证服务
Requirements: 7.1, 7.2
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import jwt
import random
import logging

from app.models.user import User
from app.core.config import settings
from app.core.redis import cache_manager

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务类"""
    
    @staticmethod
    async def generate_verification_code() -> str:
        """生成6位验证码"""
        return f"{random.randint(100000, 999999)}"
    
    @staticmethod
    async def send_sms_code(phone_number: str, code: str) -> bool:
        """
        发送短信验证码
        Requirements: 7.1, 7.2
        
        TODO: 集成真实的短信服务提供商（阿里云、腾讯云等）
        """
        try:
            # 存储验证码到Redis，5分钟过期
            cache_key = f"sms_code:{phone_number}"
            await cache_manager.set(cache_key, code, ttl=300)
            
            logger.info(f"验证码已发送到 {phone_number}: {code}")
            
            # TODO: 调用短信服务API
            # 示例：
            # sms_client = SMSClient(settings.SMS_ACCESS_KEY, settings.SMS_SECRET_KEY)
            # await sms_client.send_code(phone_number, code)
            
            return True
            
        except Exception as e:
            logger.error(f"发送验证码失败: {e}")
            return False
    
    @staticmethod
    async def verify_sms_code(phone_number: str, code: str) -> bool:
        """
        验证短信验证码
        Requirements: 7.2
        """
        try:
            cache_key = f"sms_code:{phone_number}"
            stored_code = await cache_manager.get(cache_key)
            
            if not stored_code:
                logger.warning(f"验证码不存在或已过期: {phone_number}")
                return False
            
            if stored_code != code:
                logger.warning(f"验证码错误: {phone_number}")
                return False
            
            # 验证成功后删除验证码
            await cache_manager.delete(cache_key)
            return True
            
        except Exception as e:
            logger.error(f"验证码验证失败: {e}")
            return False
    
    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        phone_number: str,
        identity: str = "student"
    ) -> User:
        """
        获取或创建用户
        Requirements: 7.1
        """
        # 查询用户是否存在
        result = await db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # 更新最后活跃时间
            user.last_active = datetime.utcnow()
            await db.commit()
            await db.refresh(user)
            logger.info(f"用户登录: {phone_number}")
        else:
            # 创建新用户
            user = User(
                phone_number=phone_number,
                identity=identity,
                preferences={"theme": "light", "language": "zh-CN"}
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"新用户注册: {phone_number}")
        
        return user
    
    @staticmethod
    def create_access_token(user_id: str, phone_number: str) -> str:
        """
        创建JWT访问令牌
        Requirements: 7.2
        """
        payload = {
            "user_id": user_id,
            "phone_number": phone_number,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return token
    
    @staticmethod
    def verify_access_token(token: str) -> dict:
        """
        验证JWT访问令牌
        Requirements: 7.2
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("令牌已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效的令牌")
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> User:
        """根据ID获取用户"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()