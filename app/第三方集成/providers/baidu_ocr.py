"""
百度OCR服务集成
"""
import httpx
import base64
from typing import List
import logging

from ..base import OCRIntegration, IntegrationResponse
from ..registry import register_integration

logger = logging.getLogger(__name__)


@register_integration("baidu_ocr")
class BaiduOCRIntegration(OCRIntegration):
    """百度OCR服务集成"""
    
    @property
    def name(self) -> str:
        return "百度OCR"
    
    @property
    def required_credentials(self) -> List[str]:
        return ["api_key", "secret_key"]
    
    async def initialize(self) -> bool:
        """初始化百度OCR服务"""
        try:
            self.client = httpx.AsyncClient(timeout=self.config.timeout)
            
            # 获取access_token
            await self._get_access_token()
            
            # 测试连接
            test_result = await self.test_connection()
            return test_result.success
            
        except Exception as e:
            logger.error(f"百度OCR初始化失败: {e}")
            return False
    
    async def test_connection(self) -> IntegrationResponse:
        """测试连接"""
        try:
            if not hasattr(self, 'access_token'):
                return IntegrationResponse(
                    success=False,
                    error="未获取到access_token"
                )
            
            # 创建一个1x1像素的测试图片
            test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc```bPPP\x00\x02\xac\xac\xac\x00\x05\x1e\x1e\x1e\x00\x02\x15\x00\x00\x00\x00IEND\xaeB`\x82').decode()
            
            response = await self.client.post(
                "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic",
                params={"access_token": self.access_token},
                data={"image": test_image}
            )
            
            if response.status_code == 200:
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
    
    async def recognize_text(self, image_data: bytes, **kwargs) -> IntegrationResponse:
        """识别文本"""
        try:
            # 将图片转换为base64
            image_base64 = base64.b64encode(image_data).decode()
            
            # 选择OCR接口
            ocr_type = kwargs.get("ocr_type", "general_basic")
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{ocr_type}"
            
            response = await self.client.post(
                url,
                params={"access_token": self.access_token},
                data={"image": image_base64}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "words_result" in data:
                    # 提取识别的文字
                    words = [item["words"] for item in data["words_result"]]
                    
                    return IntegrationResponse(
                        success=True,
                        data={
                            "text": "\n".join(words),
                            "words": words,
                            "words_result_num": data.get("words_result_num", 0),
                            "raw_result": data
                        },
                        status_code=response.status_code
                    )
                else:
                    return IntegrationResponse(
                        success=False,
                        error=f"OCR识别失败: {data.get('error_msg', '未知错误')}",
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
                error=f"文字识别异常: {str(e)}"
            )
    
    async def recognize_receipt(self, image_data: bytes, **kwargs) -> IntegrationResponse:
        """识别票据"""
        try:
            # 将图片转换为base64
            image_base64 = base64.b64encode(image_data).decode()
            
            # 使用票据识别接口
            response = await self.client.post(
                "https://aip.baidubce.com/rest/2.0/ocr/v1/receipt",
                params={"access_token": self.access_token},
                data={"image": image_base64}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "words_result" in data:
                    # 提取票据信息
                    receipt_info = {}
                    
                    for item in data["words_result"]:
                        key = item.get("key", "")
                        value = item.get("word", "")
                        
                        if key and value:
                            receipt_info[key] = value
                    
                    # 尝试提取金额信息
                    amount = None
                    for key, value in receipt_info.items():
                        if "金额" in key or "总计" in key or "合计" in key:
                            # 提取数字
                            import re
                            amount_match = re.search(r'(\d+(?:\.\d+)?)', value)
                            if amount_match:
                                amount = float(amount_match.group(1))
                                break
                    
                    return IntegrationResponse(
                        success=True,
                        data={
                            "receipt_info": receipt_info,
                            "amount": amount,
                            "raw_result": data
                        },
                        status_code=response.status_code
                    )
                else:
                    return IntegrationResponse(
                        success=False,
                        error=f"票据识别失败: {data.get('error_msg', '未知错误')}",
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
                error=f"票据识别异常: {str(e)}"
            )
    
    async def _get_access_token(self) -> str:
        """获取百度access_token"""
        try:
            response = await self.client.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.config.credentials["api_key"],
                    "client_secret": self.config.credentials["secret_key"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    return self.access_token
                else:
                    raise Exception(f"获取access_token失败: {data.get('error_description', '未知错误')}")
            else:
                raise Exception(f"HTTP错误: {response.status_code}")
                
        except Exception as e:
            logger.error(f"获取百度access_token失败: {e}")
            raise
    
    async def cleanup(self) -> None:
        """清理资源"""
        if hasattr(self, 'client'):
            await self.client.aclose()