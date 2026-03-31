"""
通用Webhook处理器集成
"""
import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..base import BaseIntegration, IntegrationType, IntegrationResponse, WebhookEvent
from ..registry import register_integration

logger = logging.getLogger(__name__)


@register_integration("webhook_handler")
class WebhookHandlerIntegration(BaseIntegration):
    """通用Webhook处理器集成"""
    
    @property
    def name(self) -> str:
        return "Webhook处理器"
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.WEBHOOK
    
    @property
    def required_credentials(self) -> List[str]:
        return ["webhook_secret"]
    
    async def initialize(self) -> bool:
        """初始化Webhook处理器"""
        try:
            self.client = httpx.AsyncClient(timeout=self.config.timeout)
            
            # 初始化事件处理器映射
            self.event_handlers = {
                "payment.completed": self._handle_payment_completed,
                "payment.failed": self._handle_payment_failed,
                "user.registered": self._handle_user_registered,
                "expense.created": self._handle_expense_created,
                "budget.exceeded": self._handle_budget_exceeded,
                "sync.conflict": self._handle_sync_conflict,
                "ai.analysis_completed": self._handle_ai_analysis_completed,
                "notification.sent": self._handle_notification_sent,
                "ocr.completed": self._handle_ocr_completed,
                "voice.transcribed": self._handle_voice_transcribed
            }
            
            logger.info(f"Webhook处理器初始化成功，支持 {len(self.event_handlers)} 种事件类型")
            return True
            
        except Exception as e:
            logger.error(f"Webhook处理器初始化失败: {e}")
            return False
    
    async def test_connection(self) -> IntegrationResponse:
        """测试Webhook处理器连接"""
        try:
            # 创建测试事件
            test_event = WebhookEvent(
                event_id="test_" + str(int(datetime.now().timestamp())),
                event_type="test.connection",
                source="webhook_handler",
                timestamp=datetime.now(),
                data={"message": "测试连接"}
            )
            
            # 处理测试事件
            result = await self.handle_webhook(test_event)
            
            return IntegrationResponse(
                success=True,
                data={
                    "status": "connected",
                    "supported_events": list(self.event_handlers.keys()),
                    "test_result": result.data
                }
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"连接测试失败: {str(e)}"
            )
    
    async def handle_webhook(self, event: WebhookEvent) -> IntegrationResponse:
        """处理Webhook事件"""
        try:
            logger.info(f"处理Webhook事件: {event.event_type} (ID: {event.event_id})")
            
            # 验证签名（如果提供）
            if event.signature and not self._verify_signature(event):
                return IntegrationResponse(
                    success=False,
                    error="Webhook签名验证失败"
                )
            
            # 查找事件处理器
            handler = self.event_handlers.get(event.event_type)
            
            if handler:
                # 执行事件处理
                result = await handler(event)
                
                # 记录处理结果
                await self._log_webhook_event(event, result)
                
                return result
            else:
                # 未知事件类型，记录但不处理
                logger.warning(f"未知的Webhook事件类型: {event.event_type}")
                
                await self._log_webhook_event(event, IntegrationResponse(
                    success=False,
                    error=f"未支持的事件类型: {event.event_type}"
                ))
                
                return IntegrationResponse(
                    success=False,
                    error=f"未支持的事件类型: {event.event_type}",
                    data={"supported_events": list(self.event_handlers.keys())}
                )
                
        except Exception as e:
            logger.error(f"处理Webhook事件失败: {e}")
            return IntegrationResponse(
                success=False,
                error=f"事件处理失败: {str(e)}"
            )
    
    def _verify_signature(self, event: WebhookEvent) -> bool:
        """验证Webhook签名"""
        try:
            webhook_secret = self.config.credentials["webhook_secret"]
            payload = json.dumps(event.data, sort_keys=True)
            
            return self.validate_webhook_signature(
                payload=payload,
                signature=event.signature,
                secret=webhook_secret
            )
            
        except Exception as e:
            logger.error(f"签名验证失败: {e}")
            return False
    
    async def _log_webhook_event(self, event: WebhookEvent, result: IntegrationResponse):
        """记录Webhook事件"""
        log_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "success": result.success,
            "error": result.error,
            "processing_time": result.response_time
        }
        
        # 这里可以将日志保存到数据库或文件
        logger.info(f"Webhook事件处理记录: {json.dumps(log_data, ensure_ascii=False)}")
    
    # 事件处理器方法
    async def _handle_payment_completed(self, event: WebhookEvent) -> IntegrationResponse:
        """处理支付完成事件"""
        try:
            payment_data = event.data
            
            # 处理支付完成逻辑
            # 例如：更新订单状态、发送通知、记录交易等
            
            logger.info(f"支付完成: 订单ID {payment_data.get('order_id')}, 金额 {payment_data.get('amount')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "支付完成事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理支付完成事件失败: {str(e)}"
            )
    
    async def _handle_payment_failed(self, event: WebhookEvent) -> IntegrationResponse:
        """处理支付失败事件"""
        try:
            payment_data = event.data
            
            # 处理支付失败逻辑
            # 例如：更新订单状态、发送失败通知、记录失败原因等
            
            logger.warning(f"支付失败: 订单ID {payment_data.get('order_id')}, 原因 {payment_data.get('error_message')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "支付失败事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理支付失败事件失败: {str(e)}"
            )
    
    async def _handle_user_registered(self, event: WebhookEvent) -> IntegrationResponse:
        """处理用户注册事件"""
        try:
            user_data = event.data
            
            # 处理用户注册逻辑
            # 例如：发送欢迎邮件、初始化用户数据、设置默认配置等
            
            logger.info(f"用户注册: 用户ID {user_data.get('user_id')}, 邮箱 {user_data.get('email')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "用户注册事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理用户注册事件失败: {str(e)}"
            )
    
    async def _handle_expense_created(self, event: WebhookEvent) -> IntegrationResponse:
        """处理支出创建事件"""
        try:
            expense_data = event.data
            
            # 处理支出创建逻辑
            # 例如：检查预算、发送提醒、更新统计等
            
            logger.info(f"支出创建: 用户ID {expense_data.get('user_id')}, 金额 {expense_data.get('amount')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "支出创建事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理支出创建事件失败: {str(e)}"
            )
    
    async def _handle_budget_exceeded(self, event: WebhookEvent) -> IntegrationResponse:
        """处理预算超支事件"""
        try:
            budget_data = event.data
            
            # 处理预算超支逻辑
            # 例如：发送警告通知、记录超支记录、建议调整等
            
            logger.warning(f"预算超支: 用户ID {budget_data.get('user_id')}, 超支金额 {budget_data.get('exceeded_amount')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "预算超支事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理预算超支事件失败: {str(e)}"
            )
    
    async def _handle_sync_conflict(self, event: WebhookEvent) -> IntegrationResponse:
        """处理同步冲突事件"""
        try:
            sync_data = event.data
            
            # 处理同步冲突逻辑
            # 例如：记录冲突、通知用户、自动解决等
            
            logger.warning(f"同步冲突: 用户ID {sync_data.get('user_id')}, 冲突类型 {sync_data.get('conflict_type')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "同步冲突事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理同步冲突事件失败: {str(e)}"
            )
    
    async def _handle_ai_analysis_completed(self, event: WebhookEvent) -> IntegrationResponse:
        """处理AI分析完成事件"""
        try:
            analysis_data = event.data
            
            # 处理AI分析完成逻辑
            # 例如：保存分析结果、发送通知、触发后续操作等
            
            logger.info(f"AI分析完成: 分析ID {analysis_data.get('analysis_id')}, 类型 {analysis_data.get('analysis_type')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "AI分析完成事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理AI分析完成事件失败: {str(e)}"
            )
    
    async def _handle_notification_sent(self, event: WebhookEvent) -> IntegrationResponse:
        """处理通知发送事件"""
        try:
            notification_data = event.data
            
            # 处理通知发送逻辑
            # 例如：记录发送状态、更新统计、处理失败重试等
            
            logger.info(f"通知发送: 通知ID {notification_data.get('notification_id')}, 状态 {notification_data.get('status')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "通知发送事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理通知发送事件失败: {str(e)}"
            )
    
    async def _handle_ocr_completed(self, event: WebhookEvent) -> IntegrationResponse:
        """处理OCR识别完成事件"""
        try:
            ocr_data = event.data
            
            # 处理OCR识别完成逻辑
            # 例如：保存识别结果、创建支出记录、发送通知等
            
            logger.info(f"OCR识别完成: 识别ID {ocr_data.get('ocr_id')}, 类型 {ocr_data.get('document_type')}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "OCR识别完成事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理OCR识别完成事件失败: {str(e)}"
            )
    
    async def _handle_voice_transcribed(self, event: WebhookEvent) -> IntegrationResponse:
        """处理语音转录完成事件"""
        try:
            voice_data = event.data
            
            # 处理语音转录完成逻辑
            # 例如：保存转录结果、分析内容、创建记录等
            
            logger.info(f"语音转录完成: 转录ID {voice_data.get('transcription_id')}, 文本长度 {len(voice_data.get('text', ''))}")
            
            return IntegrationResponse(
                success=True,
                data={"message": "语音转录完成事件处理成功"}
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"处理语音转录完成事件失败: {str(e)}"
            )
    
    async def cleanup(self) -> None:
        """清理资源"""
        if hasattr(self, 'client'):
            await self.client.aclose()