"""
第三方服务提供商集成实现
"""

# 导入所有集成实现以便自动发现
from .deepseek import DeepSeekIntegration
from .aliyun_sms import AliyunSMSIntegration
from .wechat_pay import WeChatPayIntegration
from .alipay import AlipayIntegration
from .baidu_ocr import BaiduOCRIntegration
from .baidu_voice import BaiduVoiceIntegration
from .webhook_handler import WebhookHandlerIntegration

__all__ = [
    "DeepSeekIntegration",
    "AliyunSMSIntegration", 
    "WeChatPayIntegration",
    "AlipayIntegration",
    "BaiduOCRIntegration",
    "BaiduVoiceIntegration",
    "WebhookHandlerIntegration"
]