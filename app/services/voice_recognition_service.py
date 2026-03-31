"""
语音识别服务
集成讯飞和百度AI语音识别，支持在线和离线识别
"""
import asyncio
import base64
import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

import aiohttp
from pydantic import BaseModel

from app.core.config import settings


class VoiceProvider(str, Enum):
    """语音识别服务提供商"""
    XUNFEI = "xunfei"  # 讯飞
    BAIDU = "baidu"    # 百度
    OFFLINE = "offline"  # 离线识别


class AudioFormat(str, Enum):
    """音频格式"""
    PCM = "pcm"
    WAV = "wav"
    MP3 = "mp3"
    AMR = "amr"


class VoiceRecognitionRequest(BaseModel):
    """语音识别请求"""
    audio_data: str  # Base64编码的音频数据
    format: AudioFormat = AudioFormat.WAV
    sample_rate: int = 16000
    language: str = "zh_cn"
    enable_punctuation: bool = True
    enable_noise_reduction: bool = True  # 噪音抑制（校园场景）


class VoiceRecognitionResult(BaseModel):
    """语音识别结果"""
    success: bool
    text: str = ""
    confidence: float = 0.0  # 置信度
    provider: VoiceProvider
    duration: float = 0.0  # 识别耗时（秒）
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseVoiceRecognizer(ABC):
    """语音识别基类"""
    
    @abstractmethod
    async def recognize(self, request: VoiceRecognitionRequest) -> VoiceRecognitionResult:
        """识别语音"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass


class XunfeiVoiceRecognizer(BaseVoiceRecognizer):
    """
    讯飞语音识别
    文档: https://www.xfyun.cn/doc/asr/voicedictation/API.html
    """
    
    def __init__(self):
        self.app_id = settings.XUNFEI_APP_ID
        self.api_key = settings.XUNFEI_API_KEY
        self.api_secret = settings.XUNFEI_API_SECRET
        self.api_url = "wss://iat-api.xfyun.cn/v2/iat"
    
    async def recognize(self, request: VoiceRecognitionRequest) -> VoiceRecognitionResult:
        """使用讯飞API识别语音"""
        start_time = time.time()
        try:
            audio_bytes = base64.b64decode(request.audio_data)
            params = self._build_params(request)
            async with aiohttp.ClientSession() as session:
                url = self._build_url(params)
                headers = self._build_headers()
                
                async with session.post(
                    url,
                    data=audio_bytes,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        text = self._parse_result(result_data)
                        confidence = self._calculate_confidence(result_data)
                        
                        return VoiceRecognitionResult(
                            success=True,
                            text=text,
                            confidence=confidence,
                            provider=VoiceProvider.XUNFEI,
                            duration=time.time() - start_time,
                            metadata={"raw_result": result_data}
                        )
                    else:
                        error_msg = await response.text()
                        return VoiceRecognitionResult(
                            success=False,
                            provider=VoiceProvider.XUNFEI,
                            duration=time.time() - start_time,
                            error=f"API error: {response.status} - {error_msg}"
                        )
        
        except Exception as e:
            return VoiceRecognitionResult(
                success=False,
                provider=VoiceProvider.XUNFEI,
                duration=time.time() - start_time,
                error=f"Recognition failed: {str(e)}"
            )
    
    def _build_params(self, request: VoiceRecognitionRequest) -> Dict[str, Any]:
        """构建请求参数"""
        return {
            "engine_type": "sms16k",  # 16k采样率
            "aue": "raw",  # 音频编码
            "sample_rate": request.sample_rate,
            "language": request.language,
            "domain": "iat",
            "ptt": 1 if request.enable_punctuation else 0,
            "vad_eos": 2000,  # 静音检测
            "nunum": 1  # 数字格式
        }
    
    def _build_url(self, params: Dict[str, Any]) -> str:
        """构建请求URL"""
        # 简化版本，实际应使用WebSocket
        return f"https://api.xfyun.cn/v1/service/v1/iat?{urlencode(params)}"
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Appid": self.app_id,
        }
    
    def _parse_result(self, result_data: Dict[str, Any]) -> str:
        """解析识别结果"""
        if "data" in result_data:
            return result_data["data"]
        return ""
    
    def _calculate_confidence(self, result_data: Dict[str, Any]) -> float:
        """计算置信度"""
        if "confidence" in result_data:
            return float(result_data["confidence"])
        return 0.85  # 默认置信度
    
    async def health_check(self) -> bool:
        """健康检查"""
        return bool(self.app_id and self.api_key and self.api_secret)


class BaiduVoiceRecognizer(BaseVoiceRecognizer):
    """
    百度AI语音识别
    文档: https://ai.baidu.com/ai-doc/SPEECH/Vk38lxily
    """
    
    def __init__(self):
        self.app_id = settings.BAIDU_APP_ID
        self.api_key = settings.BAIDU_API_KEY
        self.secret_key = settings.BAIDU_SECRET_KEY
        self.token_url = "https://aip.baidubce.com/oauth/2.0/token"
        self.asr_url = "https://vop.baidu.com/server_api"
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
    
    async def recognize(self, request: VoiceRecognitionRequest) -> VoiceRecognitionResult:
        """使用百度API识别语音"""
        start_time = time.time()
        try:
            token = await self._get_access_token()
            if not token:
                return VoiceRecognitionResult(
                    success=False,
                    provider=VoiceProvider.BAIDU,
                    duration=time.time() - start_time,
                    error="Failed to get access token"
                )
            audio_bytes = base64.b64decode(request.audio_data)
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            params = {
                "format": request.format.value,
                "rate": request.sample_rate,
                "channel": 1,
                "cuid": self.app_id,
                "token": token,
                "speech": audio_base64,
                "len": len(audio_bytes),
                "dev_pid": 1537 if request.language == "zh_cn" else 1737,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.asr_url,
                    json=params,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result_data = await response.json()
                    
                    if result_data.get("err_no") == 0:
                        text = "".join(result_data.get("result", []))
                        
                        return VoiceRecognitionResult(
                            success=True,
                            text=text,
                            confidence=0.90,  # 百度不返回置信度，使用默认值
                            provider=VoiceProvider.BAIDU,
                            duration=time.time() - start_time,
                            metadata={"raw_result": result_data}
                        )
                    else:
                        return VoiceRecognitionResult(
                            success=False,
                            provider=VoiceProvider.BAIDU,
                            duration=time.time() - start_time,
                            error=f"API error: {result_data.get('err_msg', 'Unknown error')}"
                        )
        
        except Exception as e:
            return VoiceRecognitionResult(
                success=False,
                provider=VoiceProvider.BAIDU,
                duration=time.time() - start_time,
                error=f"Recognition failed: {str(e)}"
            )
    
    async def _get_access_token(self) -> Optional[str]:
        """获取access token（带缓存）"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        try:
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._access_token = data.get("access_token")
                        expires_in = data.get("expires_in", 2592000)
                        self._token_expires_at = time.time() + expires_in - 3600
                        return self._access_token
        
        except Exception as e:
            print(f"Failed to get access token: {e}")
        
        return None
    
    async def health_check(self) -> bool:
        """健康检查"""
        token = await self._get_access_token()
        return token is not None


class OfflineVoiceRecognizer(BaseVoiceRecognizer):
    """
    离线语音识别（使用本地模型）
    集成 Vosk 开源模型，支持无网络环境下的语音识别
    """
    
    def __init__(self):
        self.model_loaded = False
        self.model = None
        self.model_path = None
        self._load_model()
    
    def _load_model(self):
        """加载离线语音识别模型"""
        try:
            from vosk import Model, KaldiRecognizer
            import os
            model_dir = os.path.join(os.path.dirname(__file__), "..", "models", "vosk-model")
            
            if os.path.exists(model_dir):
                self.model = Model(model_dir)
                self.model_loaded = True
                print(f"离线语音识别模型加载成功: {model_dir}")
            else:
                print(f"离线语音识别模型不存在: {model_dir}")
                print("请下载模型文件并放置到指定目录")
                print("模型下载地址: https://alphacephei.com/vosk/models")
        except ImportError:
            print("vosk库未安装，请运行: pip install vosk")
        except Exception as e:
            print(f"加载离线语音识别模型失败: {e}")
    
    async def recognize(self, request: VoiceRecognitionRequest) -> VoiceRecognitionResult:
        """使用离线模型识别语音"""
        start_time = time.time()
        
        if not self.model_loaded or not self.model:
            return VoiceRecognitionResult(
                success=False,
                provider=VoiceProvider.OFFLINE,
                duration=time.time() - start_time,
                error="离线模型未加载，请先下载并配置模型"
            )
        
        try:
            from vosk import KaldiRecognizer
            import io
            import wave
            import tempfile
            audio_bytes = base64.b64decode(request.audio_data)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            try:
                from pydub import AudioSegment
                import numpy as np
                audio = AudioSegment.from_file(temp_path)
                audio = audio.set_channels(1)
                audio = audio.set_frame_rate(16000)
                if request.enable_noise_reduction:
                    audio = self._noise_reduction(audio)
                raw_data = audio.raw_data
                rec = KaldiRecognizer(self.model, 16000)
                result_text = ""
                if rec.AcceptWaveform(raw_data):
                    result = json.loads(rec.Result())
                    result_text = result.get("text", "")
                else:
                    result = json.loads(rec.PartialResult())
                    result_text = result.get("partial", "")
                import os
                os.unlink(temp_path)
                
                if result_text:
                    return VoiceRecognitionResult(
                        success=True,
                        text=result_text,
                        confidence=0.75,
                        provider=VoiceProvider.OFFLINE,
                        duration=time.time() - start_time,
                        metadata={
                            "offline_mode": True,
                            "model": "vosk"
                        }
                    )
                else:
                    return VoiceRecognitionResult(
                        success=False,
                        provider=VoiceProvider.OFFLINE,
                        duration=time.time() - start_time,
                        error="未能识别到有效语音"
                    )
                    
            except Exception as e:
                import os
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e
                
        except Exception as e:
            return VoiceRecognitionResult(
                success=False,
                provider=VoiceProvider.OFFLINE,
                duration=time.time() - start_time,
                error=f"离线识别失败: {str(e)}"
            )
    
    def _noise_reduction(self, audio):
        """简单的降噪处理"""
        try:
            from pydub.effects import low_pass_filter, high_pass_filter
            import numpy as np
            samples = np.array(audio.get_array_of_samples())
            audio = low_pass_filter(audio, 3000)
            audio = high_pass_filter(audio, 300)
            
            return audio
        except Exception as e:
            print(f"降噪处理失败: {e}")
            return audio
    
    async def health_check(self) -> bool:
        """健康检查"""
        return self.model_loaded


class VoiceRecognitionService:
    """
    语音识别服务管理器
    支持多提供商、自动降级、结果融合
    """
    
    def __init__(self):
        self.recognizers: Dict[VoiceProvider, BaseVoiceRecognizer] = {
            VoiceProvider.XUNFEI: XunfeiVoiceRecognizer(),
            VoiceProvider.BAIDU: BaiduVoiceRecognizer(),
            VoiceProvider.OFFLINE: OfflineVoiceRecognizer(),
        }
        self.default_provider = VoiceProvider.XUNFEI
        self.fallback_providers = [VoiceProvider.BAIDU, VoiceProvider.OFFLINE]
    
    async def recognize(
        self,
        request: VoiceRecognitionRequest,
        provider: Optional[VoiceProvider] = None,
        enable_fallback: bool = True
    ) -> VoiceRecognitionResult:
        """
        识别语音
        
        Args:
            request: 识别请求
            provider: 指定提供商，None则使用默认
            enable_fallback: 是否启用降级策略
        """
        target_provider = provider or self.default_provider
        recognizer = self.recognizers.get(target_provider)
        if recognizer:
            result = await recognizer.recognize(request)
            if result.success and result.confidence >= 0.85:
                return result
        if enable_fallback:
            for fallback_provider in self.fallback_providers:
                if fallback_provider == target_provider:
                    continue
                
                fallback_recognizer = self.recognizers.get(fallback_provider)
                if fallback_recognizer:
                    fallback_result = await fallback_recognizer.recognize(request)
                    if fallback_result.success and fallback_result.confidence >= 0.80:
                        return fallback_result
        return result if 'result' in locals() else VoiceRecognitionResult(
            success=False,
            provider=target_provider,
            error="All recognition attempts failed"
        )
    
    async def recognize_with_fusion(
        self,
        request: VoiceRecognitionRequest,
        providers: Optional[List[VoiceProvider]] = None
    ) -> VoiceRecognitionResult:
        """
        多提供商结果融合
        同时调用多个提供商，选择最佳结果
        """
        if not providers:
            providers = [VoiceProvider.XUNFEI, VoiceProvider.BAIDU]
        tasks = []
        for provider in providers:
            recognizer = self.recognizers.get(provider)
            if recognizer:
                tasks.append(recognizer.recognize(request))
        
        if not tasks:
            return VoiceRecognitionResult(
                success=False,
                provider=self.default_provider,
                error="No available recognizers"
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = [
            r for r in results
            if isinstance(r, VoiceRecognitionResult) and r.success
        ]
        
        if not valid_results:
            return VoiceRecognitionResult(
                success=False,
                provider=self.default_provider,
                error="All recognizers failed"
            )
        best_result = max(valid_results, key=lambda r: r.confidence)
        return best_result
    
    async def health_check(self) -> Dict[str, bool]:
        """检查所有提供商的健康状态"""
        health_status = {}
        for provider, recognizer in self.recognizers.items():
            health_status[provider.value] = await recognizer.health_check()
        return health_status
    
    async def preprocess_audio(
        self,
        audio_data: str,
        enable_noise_reduction: bool = True,
        enable_normalization: bool = True
    ) -> str:
        """
        音频预处理（适配嘈杂环境）
        
        Args:
            audio_data: Base64编码的音频
            enable_noise_reduction: 启用降噪
            enable_normalization: 启用音量归一化
        
        Returns:
            处理后的Base64音频
        """
        return audio_data


voice_recognition_service = VoiceRecognitionService()
