"""
百度语音服务集成
"""
import httpx
import base64
import json
from typing import List, Dict, Any
import logging

from ..base import VoiceIntegration, IntegrationResponse
from ..registry import register_integration

logger = logging.getLogger(__name__)


@register_integration("baidu_voice")
class BaiduVoiceIntegration(VoiceIntegration):
    """百度语音服务集成"""
    
    @property
    def name(self) -> str:
        return "百度语音服务"
    
    @property
    def required_credentials(self) -> List[str]:
        return ["api_key", "secret_key"]
    
    async def initialize(self) -> bool:
        """初始化百度语音服务"""
        try:
            self.client = httpx.AsyncClient(timeout=self.config.timeout)
            
            # 获取访问令牌
            await self._get_access_token()
            
            # 测试连接
            test_result = await self.test_connection()
            return test_result.success
            
        except Exception as e:
            logger.error(f"百度语音服务初始化失败: {e}")
            return False
    
    async def _get_access_token(self) -> str:
        """获取访问令牌"""
        try:
            response = await self.client.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.credentials["api_key"],
                    "client_secret": self.config.credentials["secret_key"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                return self.access_token
            else:
                raise Exception(f"获取访问令牌失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"获取百度语音访问令牌失败: {e}")
            raise
    
    async def test_connection(self) -> IntegrationResponse:
        """测试百度语音连接"""
        try:
            # 测试语音合成接口
            test_text = "测试"
            response = await self.client.post(
                f"https://tsn.baidu.com/text2audio?tex={test_text}&tok={self.access_token}&cuid=test&ctp=1&lan=zh&spd=5&pit=5&vol=5&per=0"
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
                    error=f"API返回错误: {response.status_code}",
                    status_code=response.status_code
                )
                
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"连接测试失败: {str(e)}"
            )
    
    async def speech_to_text(self, audio_data: bytes, **kwargs) -> IntegrationResponse:
        """语音转文字"""
        try:
            # 将音频数据转换为base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 准备请求数据
            request_data = {
                "format": kwargs.get("format", "wav"),
                "rate": kwargs.get("rate", 16000),
                "channel": 1,
                "cuid": kwargs.get("cuid", "default"),
                "token": self.access_token,
                "speech": audio_base64,
                "len": len(audio_data)
            }
            
            response = await self.client.post(
                "https://vop.baidu.com/server_api",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("err_no") == 0:
                    return IntegrationResponse(
                        success=True,
                        data={
                            "text": data["result"][0] if data.get("result") else "",
                            "confidence": 1.0
                        },
                        status_code=response.status_code
                    )
                else:
                    return IntegrationResponse(
                        success=False,
                        error=f"语音识别失败: {data.get('err_msg', '未知错误')}",
                        status_code=response.status_code
                    )
            else:
                return IntegrationResponse(
                    success=False,
                    error=f"API请求失败: {response.status_code}",
                    status_code=response.status_code
                )
                
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"语音转文字失败: {str(e)}"
            )
    
    async def text_to_speech(self, text: str, **kwargs) -> IntegrationResponse:
        """文字转语音"""
        try:
            # 准备请求参数
            params = {
                "tex": text,
                "tok": self.access_token,
                "cuid": kwargs.get("cuid", "default"),
                "ctp": 1,
                "lan": kwargs.get("language", "zh"),
                "spd": kwargs.get("speed", 5),  # 语速 0-15
                "pit": kwargs.get("pitch", 5),  # 音调 0-15
                "vol": kwargs.get("volume", 5), # 音量 0-15
                "per": kwargs.get("person", 0)  # 发音人 0-4
            }
            
            response = await self.client.get(
                "https://tsn.baidu.com/text2audio",
                params=params
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                
                if "audio" in content_type:
                    # 返回音频数据
                    audio_data = response.content
                    return IntegrationResponse(
                        success=True,
                        data={
                            "audio_data": base64.b64encode(audio_data).decode('utf-8'),
                            "content_type": content_type,
                            "size": len(audio_data)
                        },
                        status_code=response.status_code
                    )
                else:
                    # 可能是错误响应
                    try:
                        error_data = response.json()
                        return IntegrationResponse(
                            success=False,
                            error=f"语音合成失败: {error_data.get('err_msg', '未知错误')}",
                            status_code=response.status_code
                        )
                    except:
                        return IntegrationResponse(
                            success=False,
                            error="语音合成失败: 返回格式错误",
                            status_code=response.status_code
                        )
            else:
                return IntegrationResponse(
                    success=False,
                    error=f"API请求失败: {response.status_code}",
                    status_code=response.status_code
                )
                
        except Exception as e:
            return IntegrationResponse(
                success=False,
                error=f"文字转语音失败: {str(e)}"
            )
    
    async def cleanup(self) -> None:
        """清理资源"""
        if hasattr(self, 'client'):
            await self.client.aclose()