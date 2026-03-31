"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import List, Dict, Any
import os


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*"]
    
    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://finance_user:finance_pass@localhost:5432/finance_db"
    )
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # JWT配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # DeepSeek API配置
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL: str = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
    
    # 短信服务配置
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "aliyun")
    SMS_ACCESS_KEY: str = os.getenv("SMS_ACCESS_KEY", "")
    SMS_SECRET_KEY: str = os.getenv("SMS_SECRET_KEY", "")
    
    # 微信支付配置
    WECHAT_APP_ID: str = os.getenv("WECHAT_APP_ID", "")
    WECHAT_APP_SECRET: str = os.getenv("WECHAT_APP_SECRET", "")
    
    # 支付宝配置
    ALIPAY_APP_ID: str = os.getenv("ALIPAY_APP_ID", "")
    ALIPAY_PRIVATE_KEY: str = os.getenv("ALIPAY_PRIVATE_KEY", "")
    
    # 百度OCR配置
    BAIDU_OCR_API_KEY: str = os.getenv("BAIDU_OCR_API_KEY", "")
    BAIDU_OCR_SECRET_KEY: str = os.getenv("BAIDU_OCR_SECRET_KEY", "")
    
    # 百度语音配置
    BAIDU_APP_ID: str = os.getenv("BAIDU_APP_ID", "")
    BAIDU_API_KEY: str = os.getenv("BAIDU_API_KEY", "")
    BAIDU_SECRET_KEY: str = os.getenv("BAIDU_SECRET_KEY", "")
    
    # 讯飞语音配置
    XUNFEI_APP_ID: str = os.getenv("XUNFEI_APP_ID", "")
    XUNFEI_API_KEY: str = os.getenv("XUNFEI_API_KEY", "")
    XUNFEI_API_SECRET: str = os.getenv("XUNFEI_API_SECRET", "")
    
    # Webhook配置
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "webhook-secret-key")
    
    # 集成配置
    INTEGRATIONS_ENABLED: bool = os.getenv("INTEGRATIONS_ENABLED", "True").lower() == "true"
    INTEGRATIONS_AUTO_INIT: bool = os.getenv("INTEGRATIONS_AUTO_INIT", "True").lower() == "true"
    
    def get_integration_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取集成配置"""
        return {
            "deepseek": {
                "name": "deepseek",
                "type": "ai_service",
                "enabled": bool(self.DEEPSEEK_API_KEY),
                "credentials": {
                    "api_key": self.DEEPSEEK_API_KEY,
                    "api_url": self.DEEPSEEK_API_URL
                },
                "config": {
                    "model": "deepseek-chat",
                    "max_tokens": 500,
                    "temperature": 0.7
                }
            },
            "aliyun_sms": {
                "name": "aliyun_sms",
                "type": "sms",
                "enabled": bool(self.SMS_ACCESS_KEY and self.SMS_SECRET_KEY),
                "credentials": {
                    "access_key": self.SMS_ACCESS_KEY,
                    "secret_key": self.SMS_SECRET_KEY
                },
                "config": {
                    "region": "cn-hangzhou",
                    "sign_name": "财务助手"
                }
            },
            "wechat_pay": {
                "name": "wechat_pay",
                "type": "payment",
                "enabled": bool(self.WECHAT_APP_ID and self.WECHAT_APP_SECRET),
                "credentials": {
                    "app_id": self.WECHAT_APP_ID,
                    "app_secret": self.WECHAT_APP_SECRET
                },
                "config": {
                    "sandbox": self.DEBUG
                }
            },
            "alipay": {
                "name": "alipay",
                "type": "payment",
                "enabled": bool(self.ALIPAY_APP_ID and self.ALIPAY_PRIVATE_KEY),
                "credentials": {
                    "app_id": self.ALIPAY_APP_ID,
                    "private_key": self.ALIPAY_PRIVATE_KEY
                },
                "config": {
                    "sandbox": self.DEBUG
                }
            },
            "baidu_ocr": {
                "name": "baidu_ocr",
                "type": "ocr",
                "enabled": bool(self.BAIDU_OCR_API_KEY and self.BAIDU_OCR_SECRET_KEY),
                "credentials": {
                    "api_key": self.BAIDU_OCR_API_KEY,
                    "secret_key": self.BAIDU_OCR_SECRET_KEY
                },
                "config": {
                    "language": "CHN_ENG",
                    "detect_direction": True
                }
            },
            "baidu_voice": {
                "name": "baidu_voice",
                "type": "voice",
                "enabled": bool(self.BAIDU_VOICE_API_KEY and self.BAIDU_VOICE_SECRET_KEY),
                "credentials": {
                    "api_key": self.BAIDU_VOICE_API_KEY,
                    "secret_key": self.BAIDU_VOICE_SECRET_KEY
                },
                "config": {
                    "language": "zh",
                    "format": "wav",
                    "rate": 16000
                }
            },
            "webhook_handler": {
                "name": "webhook_handler",
                "type": "webhook",
                "enabled": True,
                "credentials": {
                    "webhook_secret": self.WEBHOOK_SECRET
                },
                "config": {
                    "max_events_per_minute": 100,
                    "event_retention_days": 30
                }
            }
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()