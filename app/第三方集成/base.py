"""
第三方集成基础类和接口定义
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class IntegrationStatus(str, Enum):
    """集成状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"
    DISABLED = "disabled"


class IntegrationType(str, Enum):
    """集成类型"""
    PAYMENT = "payment"           # 支付服务
    AI_SERVICE = "ai_service"     # AI服务
    SMS = "sms"                   # 短信服务
    BANK = "bank"                 # 银行服务
    ANALYTICS = "analytics"       # 数据分析
    NOTIFICATION = "notification" # 通知服务
    STORAGE = "storage"           # 存储服务
    WEBHOOK = "webhook"           # Webhook服务
    OCR = "ocr"                   # OCR识别
    VOICE = "voice"               # 语音服务


class IntegrationConfig(BaseModel):
    """集成配置"""
    name: str
    type: IntegrationType
    enabled: bool = True
    config: Dict[str, Any] = {}
    credentials: Dict[str, str] = {}
    webhook_url: Optional[str] = None
    rate_limit: Optional[int] = None
    timeout: int = 30
    retry_count: int = 3
    metadata: Dict[str, Any] = {}


class IntegrationResponse(BaseModel):
    """集成响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    metadata: Dict[str, Any] = {}


class WebhookEvent(BaseModel):
    """Webhook事件"""
    event_id: str
    event_type: str
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    signature: Optional[str] = None
    headers: Dict[str, str] = {}


class BaseIntegration(ABC):
    """第三方集成基础类"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = IntegrationStatus.INACTIVE
        self.last_error: Optional[str] = None
        self.last_success: Optional[datetime] = None
        self.last_failure: Optional[datetime] = None
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """集成名称"""
        pass
    
    @property
    @abstractmethod
    def type(self) -> IntegrationType:
        """集成类型"""
        pass
    
    @property
    @abstractmethod
    def required_credentials(self) -> List[str]:
        """必需的凭证字段"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化集成"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> IntegrationResponse:
        """测试连接"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        if not self.config.enabled:
            return False
        
        for field in self.required_credentials:
            if field not in self.config.credentials or not self.config.credentials[field]:
                return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """获取集成状态"""
        return {
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "enabled": self.config.enabled,
            "configured": self.is_configured(),
            "last_error": self.last_error,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "statistics": {
                "total_requests": self.request_count,
                "successful_requests": self.success_count,
                "failed_requests": self.failure_count,
                "success_rate": self.success_count / max(self.request_count, 1) * 100
            }
        }
    
    async def execute_with_retry(self, operation, *args, **kwargs) -> IntegrationResponse:
        """带重试的执行操作"""
        self.request_count += 1
        last_error = None
        
        for attempt in range(self.config.retry_count + 1):
            try:
                start_time = datetime.now()
                result = await operation(*args, **kwargs)
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds()
                
                if isinstance(result, IntegrationResponse):
                    result.response_time = response_time
                    if result.success:
                        self.success_count += 1
                        self.last_success = datetime.now()
                        self.status = IntegrationStatus.ACTIVE
                        return result
                    else:
                        last_error = result.error
                else:
                    # 包装普通返回值
                    self.success_count += 1
                    self.last_success = datetime.now()
                    self.status = IntegrationStatus.ACTIVE
                    return IntegrationResponse(
                        success=True,
                        data=result if isinstance(result, dict) else {"result": result},
                        response_time=response_time
                    )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"{self.name} 集成执行失败 (尝试 {attempt + 1}/{self.config.retry_count + 1}): {e}")
                
                if attempt < self.config.retry_count:
                    # 等待后重试
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # 指数退避
        
        # 所有重试都失败
        self.failure_count += 1
        self.last_failure = datetime.now()
        self.last_error = last_error
        self.status = IntegrationStatus.ERROR
        
        return IntegrationResponse(
            success=False,
            error=f"操作失败，已重试 {self.config.retry_count} 次: {last_error}"
        )
    
    async def handle_webhook(self, event: WebhookEvent) -> IntegrationResponse:
        """处理Webhook事件（可选实现）"""
        return IntegrationResponse(
            success=False,
            error="此集成不支持Webhook事件"
        )
    
    def validate_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """验证Webhook签名（可选实现）"""
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


class PaymentIntegration(BaseIntegration):
    """支付集成基础类"""
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.PAYMENT
    
    @abstractmethod
    async def get_transactions(self, start_date: datetime, end_date: datetime, **kwargs) -> IntegrationResponse:
        """获取交易记录"""
        pass
    
    @abstractmethod
    async def get_balance(self, **kwargs) -> IntegrationResponse:
        """获取账户余额"""
        pass


class AIServiceIntegration(BaseIntegration):
    """AI服务集成基础类"""
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.AI_SERVICE
    
    @abstractmethod
    async def analyze_text(self, text: str, **kwargs) -> IntegrationResponse:
        """分析文本"""
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> IntegrationResponse:
        """生成响应"""
        pass


class SMSIntegration(BaseIntegration):
    """短信服务集成基础类"""
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.SMS
    
    @abstractmethod
    async def send_sms(self, phone_number: str, message: str, **kwargs) -> IntegrationResponse:
        """发送短信"""
        pass
    
    @abstractmethod
    async def send_verification_code(self, phone_number: str, code: str, **kwargs) -> IntegrationResponse:
        """发送验证码"""
        pass


class NotificationIntegration(BaseIntegration):
    """通知服务集成基础类"""
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.NOTIFICATION
    
    @abstractmethod
    async def send_notification(self, user_id: str, title: str, message: str, **kwargs) -> IntegrationResponse:
        """发送通知"""
        pass
    
    @abstractmethod
    async def send_push_notification(self, device_token: str, title: str, message: str, **kwargs) -> IntegrationResponse:
        """发送推送通知"""
        pass


class OCRIntegration(BaseIntegration):
    """OCR识别集成基础类"""
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.OCR
    
    @abstractmethod
    async def recognize_text(self, image_data: bytes, **kwargs) -> IntegrationResponse:
        """识别文本"""
        pass
    
    @abstractmethod
    async def recognize_receipt(self, image_data: bytes, **kwargs) -> IntegrationResponse:
        """识别票据"""
        pass


class VoiceIntegration(BaseIntegration):
    """语音服务集成基础类"""
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.VOICE
    
    @abstractmethod
    async def speech_to_text(self, audio_data: bytes, **kwargs) -> IntegrationResponse:
        """语音转文字"""
        pass
    
    @abstractmethod
    async def text_to_speech(self, text: str, **kwargs) -> IntegrationResponse:
        """文字转语音"""
        pass