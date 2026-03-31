"""
阿里云短信服务集成
"""
import httpx
import json
import hmac
import hashlib
import base64
import uuid
from datetime import datetime
from typing import List
import logging

from ..base import SMSIntegration, IntegrationResponse
from ..registry import register_integration

logger = logging.getLogger(__name__)


@register_integration("aliyun_sms")
class AliyunSMSIntegration(SMSIntegration):
    """阿里云短信服务集成"""
    
    @property
    def name(self) -> str:
        return "阿里云短信"
    
    @property
    def required_credentials(self) -> List[str]:
        return ["access_key", "secret_key", "sign_name"]
    
    async def initialize(self) -> bool:
        """初始化阿里云短信服务"""
        try:
            self.client = httpx.AsyncClient(timeout=self.config.timeout)
            self.endpoint = "https://dysmsapi.aliyuncs.com"
            
            # 测试连接
            test_result = await self.test_connection()
            return test_result.success
            
        except Exception as e:
            logger.error(f"阿里云短信初始化失败: {e}")
            return False
    
    async def test_connection(self) -> IntegrationResponse:
        """测试连接"""
        try:
            # 发送一个查询短信模板的请求来测试连接
            params = {
                "Action": "QuerySmsTemplate",
                "Version": "2017-05-25",
                "RegionId": "cn-hangzhou",
                "TemplateCode": "SMS_000000000"  # 使用一个不存在的模板代码进行测试
            }
            
            response = await self._make_request(params)
            
            # 即使模板不存在，只要能正常返回错误信息就说明连接正常
            if response.status_code in [200, 400]:
                return IntegrationResponse(
                    success=True,
                    data={"status": "connected"},
                    status_code=response.status_code
                )
            else:
                return IntegrationResponse(
                    success=False,
                    error=f"连接测试失败: {response.status_code}",
                    status_code=response.status_code
                )
                
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"连接测试异常: {str(e)}"
            )
    
    async def send_sms(self, phone_number: str, message: str, **kwargs) -> IntegrationResponse:
        """发送短信"""
        template_code = kwargs.get("template_code", "SMS_000000000")
        template_param = kwargs.get("template_param", {"message": message})
        
        params = {
            "Action": "SendSms",
            "Version": "2017-05-25",
            "RegionId": "cn-hangzhou",
            "PhoneNumbers": phone_number,
            "SignName": self.config.credentials["sign_name"],
            "TemplateCode": template_code,
            "TemplateParam": json.dumps(template_param)
        }
        
        try:
            response = await self._make_request(params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("Code") == "OK":
                    return IntegrationResponse(
                        success=True,
                        data={
                            "message_id": data.get("BizId"),
                            "request_id": data.get("RequestId")
                        },
                        status_code=response.status_code
                    )
                else:
                    return IntegrationResponse(
                        success=False,
                        error=f"发送失败: {data.get('Message', '未知错误')}",
                        status_code=response.status_code,
                        data=data
                    )
            else:
                return IntegrationResponse(
                    success=False,
                    error=f"HTTP错误: {response.status_code}",
                    status_code=response.status_code
                )
                
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"发送短信异常: {str(e)}"
            )
    
    async def send_verification_code(self, phone_number: str, code: str, **kwargs) -> IntegrationResponse:
        """发送验证码"""
        template_code = kwargs.get("template_code", "SMS_000000000")  # 需要配置实际的验证码模板
        
        return await self.send_sms(
            phone_number=phone_number,
            message=code,
            template_code=template_code,
            template_param={"code": code}
        )
    
    async def _make_request(self, params: dict) -> httpx.Response:
        """发送请求到阿里云API"""
        # 添加公共参数
        params.update({
            "AccessKeyId": self.config.credentials["access_key"],
            "Format": "JSON",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid4()),
            "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        
        # 生成签名
        signature = self._generate_signature(params)
        params["Signature"] = signature
        
        # 发送请求
        response = await self.client.get(self.endpoint, params=params)
        return response
    
    def _generate_signature(self, params: dict) -> str:
        """生成阿里云API签名"""
        # 排序参数
        sorted_params = sorted(params.items())
        
        # 构建查询字符串
        query_string = "&".join([f"{k}={self._percent_encode(str(v))}" for k, v in sorted_params])
        
        # 构建待签名字符串
        string_to_sign = f"GET&{self._percent_encode('/')}&{self._percent_encode(query_string)}"
        
        # 生成签名
        secret_key = self.config.credentials["secret_key"] + "&"
        signature = hmac.new(
            secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _percent_encode(self, value: str) -> str:
        """URL编码"""
        import urllib.parse
        return urllib.parse.quote(value, safe='').replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
    
    async def cleanup(self) -> None:
        """清理资源"""
        if hasattr(self, 'client'):
            await self.client.aclose()