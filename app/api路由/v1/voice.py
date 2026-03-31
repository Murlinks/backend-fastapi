"""
语音识别API端点
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.voice_recognition_service import (
    voice_recognition_service,
    VoiceRecognitionRequest,
    VoiceRecognitionResult,
    VoiceProvider,
    AudioFormat
)

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceRecognitionResponse(BaseModel):
    """语音识别响应"""
    success: bool
    text: str
    confidence: float
    provider: str
    duration: float
    error: Optional[str] = None


@router.post("/recognize", response_model=VoiceRecognitionResponse)
async def recognize_voice(
    audio_data: str = Form(..., description="Base64编码的音频数据"),
    format: AudioFormat = Form(AudioFormat.WAV, description="音频格式"),
    sample_rate: int = Form(16000, description="采样率"),
    language: str = Form("zh_cn", description="语言"),
    provider: Optional[VoiceProvider] = Form(None, description="指定识别提供商"),
    enable_fallback: bool = Form(True, description="启用降级策略"),
    enable_noise_reduction: bool = Form(True, description="启用降噪")
):
    """
    语音识别接口
    
    支持多种音频格式和采样率
    自动降级到备用提供商
    适配嘈杂环境（校园场景）
    """
    try:
        # 构建请求
        request = VoiceRecognitionRequest(
            audio_data=audio_data,
            format=format,
            sample_rate=sample_rate,
            language=language,
            enable_noise_reduction=enable_noise_reduction
        )
        
        # 执行识别
        result = await voice_recognition_service.recognize(
            request=request,
            provider=provider,
            enable_fallback=enable_fallback
        )
        
        return VoiceRecognitionResponse(
            success=result.success,
            text=result.text,
            confidence=result.confidence,
            provider=result.provider.value,
            duration=result.duration,
            error=result.error
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recognition failed: {str(e)}")


@router.post("/recognize/file", response_model=VoiceRecognitionResponse)
async def recognize_voice_file(
    file: UploadFile = File(..., description="音频文件"),
    provider: Optional[VoiceProvider] = Form(None, description="指定识别提供商"),
    enable_fallback: bool = Form(True, description="启用降级策略"),
    enable_noise_reduction: bool = Form(True, description="启用降噪")
):
    """
    上传音频文件进行识别
    
    支持 WAV、MP3、AMR 等格式
    """
    try:
        # 读取文件内容
        audio_bytes = await file.read()
        
        # 转换为Base64
        import base64
        audio_data = base64.b64encode(audio_bytes).decode('utf-8')
        
        # 检测音频格式
        format_map = {
            "audio/wav": AudioFormat.WAV,
            "audio/mpeg": AudioFormat.MP3,
            "audio/amr": AudioFormat.AMR,
        }
        audio_format = format_map.get(file.content_type, AudioFormat.WAV)
        
        # 构建请求
        request = VoiceRecognitionRequest(
            audio_data=audio_data,
            format=audio_format,
            sample_rate=16000,
            language="zh_cn",
            enable_noise_reduction=enable_noise_reduction
        )
        
        # 执行识别
        result = await voice_recognition_service.recognize(
            request=request,
            provider=provider,
            enable_fallback=enable_fallback
        )
        
        return VoiceRecognitionResponse(
            success=result.success,
            text=result.text,
            confidence=result.confidence,
            provider=result.provider.value,
            duration=result.duration,
            error=result.error
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recognition failed: {str(e)}")


@router.post("/recognize/fusion", response_model=VoiceRecognitionResponse)
async def recognize_voice_fusion(
    audio_data: str = Form(..., description="Base64编码的音频数据"),
    format: AudioFormat = Form(AudioFormat.WAV, description="音频格式"),
    sample_rate: int = Form(16000, description="采样率"),
    providers: Optional[str] = Form(None, description="提供商列表，逗号分隔")
):
    """
    多提供商结果融合
    
    同时调用多个提供商，选择最佳结果
    提升识别准确率至85%+
    """
    try:
        # 解析提供商列表
        provider_list = None
        if providers:
            provider_list = [VoiceProvider(p.strip()) for p in providers.split(",")]
        
        # 构建请求
        request = VoiceRecognitionRequest(
            audio_data=audio_data,
            format=format,
            sample_rate=sample_rate,
            language="zh_cn",
            enable_noise_reduction=True
        )
        
        # 执行融合识别
        result = await voice_recognition_service.recognize_with_fusion(
            request=request,
            providers=provider_list
        )
        
        return VoiceRecognitionResponse(
            success=result.success,
            text=result.text,
            confidence=result.confidence,
            provider=result.provider.value,
            duration=result.duration,
            error=result.error
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fusion recognition failed: {str(e)}")


@router.get("/health")
async def voice_health_check():
    """
    检查语音识别服务健康状态
    """
    health_status = await voice_recognition_service.health_check()
    
    return {
        "status": "healthy" if any(health_status.values()) else "unhealthy",
        "providers": health_status
    }


@router.get("/providers")
async def list_providers():
    """
    列出所有可用的语音识别提供商
    """
    return {
        "providers": [
            {
                "name": VoiceProvider.XUNFEI.value,
                "display_name": "讯飞语音",
                "description": "科大讯飞语音识别，适合中文场景",
                "accuracy": "90%+",
                "latency": "低"
            },
            {
                "name": VoiceProvider.BAIDU.value,
                "display_name": "百度AI",
                "description": "百度语音识别，支持多种方言",
                "accuracy": "88%+",
                "latency": "中"
            },
            {
                "name": VoiceProvider.OFFLINE.value,
                "display_name": "离线识别",
                "description": "本地模型识别，无需网络",
                "accuracy": "75%+",
                "latency": "低"
            }
        ],
        "default": VoiceProvider.XUNFEI.value,
        "fallback_order": [VoiceProvider.BAIDU.value, VoiceProvider.OFFLINE.value]
    }
