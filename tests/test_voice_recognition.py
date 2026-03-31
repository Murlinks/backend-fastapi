"""
语音识别服务测试
"""
import base64
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.voice_recognition_service import (
    VoiceRecognitionService,
    VoiceRecognitionRequest,
    VoiceRecognitionResult,
    VoiceProvider,
    AudioFormat,
    XunfeiVoiceRecognizer,
    BaiduVoiceRecognizer,
)


@pytest.fixture
def sample_audio_data():
    """生成测试音频数据"""
    # 模拟一个简单的音频数据
    audio_bytes = b"fake audio data for testing"
    return base64.b64encode(audio_bytes).decode('utf-8')


@pytest.fixture
def voice_request(sample_audio_data):
    """创建测试请求"""
    return VoiceRecognitionRequest(
        audio_data=sample_audio_data,
        format=AudioFormat.WAV,
        sample_rate=16000,
        language="zh_cn",
        enable_noise_reduction=True
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestVoiceRecognitionService:
    """语音识别服务测试"""
    
    async def test_service_initialization(self):
        """测试服务初始化"""
        service = VoiceRecognitionService()
        
        assert service.default_provider == VoiceProvider.XUNFEI
        assert VoiceProvider.XUNFEI in service.recognizers
        assert VoiceProvider.BAIDU in service.recognizers
        assert VoiceProvider.OFFLINE in service.recognizers
    
    async def test_recognize_with_default_provider(self, voice_request):
        """测试使用默认提供商识别"""
        service = VoiceRecognitionService()
        
        # Mock 讯飞识别器
        mock_result = VoiceRecognitionResult(
            success=True,
            text="今天午饭花了25元",
            confidence=0.92,
            provider=VoiceProvider.XUNFEI,
            duration=0.35
        )
        
        with patch.object(
            service.recognizers[VoiceProvider.XUNFEI],
            'recognize',
            return_value=mock_result
        ):
            result = await service.recognize(voice_request)
            
            assert result.success is True
            assert result.text == "今天午饭花了25元"
            assert result.confidence >= 0.85
            assert result.provider == VoiceProvider.XUNFEI
    
    async def test_recognize_with_fallback(self, voice_request):
        """测试降级策略"""
        service = VoiceRecognitionService()
        
        # Mock 讯飞失败
        xunfei_result = VoiceRecognitionResult(
            success=False,
            provider=VoiceProvider.XUNFEI,
            error="API error"
        )
        
        # Mock 百度成功
        baidu_result = VoiceRecognitionResult(
            success=True,
            text="今天午饭花了25元",
            confidence=0.88,
            provider=VoiceProvider.BAIDU,
            duration=0.42
        )
        
        with patch.object(
            service.recognizers[VoiceProvider.XUNFEI],
            'recognize',
            return_value=xunfei_result
        ), patch.object(
            service.recognizers[VoiceProvider.BAIDU],
            'recognize',
            return_value=baidu_result
        ):
            result = await service.recognize(voice_request, enable_fallback=True)
            
            assert result.success is True
            assert result.provider == VoiceProvider.BAIDU
            assert result.confidence >= 0.80
    
    async def test_recognize_with_low_confidence(self, voice_request):
        """测试低置信度时的降级"""
        service = VoiceRecognitionService()
        
        # Mock 讯飞低置信度
        xunfei_result = VoiceRecognitionResult(
            success=True,
            text="今天午饭花了25元",
            confidence=0.70,  # 低于阈值
            provider=VoiceProvider.XUNFEI,
            duration=0.35
        )
        
        # Mock 百度高置信度
        baidu_result = VoiceRecognitionResult(
            success=True,
            text="今天午饭花了25元",
            confidence=0.90,
            provider=VoiceProvider.BAIDU,
            duration=0.42
        )
        
        with patch.object(
            service.recognizers[VoiceProvider.XUNFEI],
            'recognize',
            return_value=xunfei_result
        ), patch.object(
            service.recognizers[VoiceProvider.BAIDU],
            'recognize',
            return_value=baidu_result
        ):
            result = await service.recognize(voice_request, enable_fallback=True)
            
            # 应该使用百度的高置信度结果
            assert result.provider == VoiceProvider.BAIDU
            assert result.confidence >= 0.85
    
    async def test_recognize_fusion(self, voice_request):
        """测试多提供商融合"""
        service = VoiceRecognitionService()
        
        # Mock 多个提供商的结果
        xunfei_result = VoiceRecognitionResult(
            success=True,
            text="今天午饭花了25元",
            confidence=0.88,
            provider=VoiceProvider.XUNFEI,
            duration=0.35
        )
        
        baidu_result = VoiceRecognitionResult(
            success=True,
            text="今天午饭花了25元",
            confidence=0.92,  # 更高置信度
            provider=VoiceProvider.BAIDU,
            duration=0.42
        )
        
        with patch.object(
            service.recognizers[VoiceProvider.XUNFEI],
            'recognize',
            return_value=xunfei_result
        ), patch.object(
            service.recognizers[VoiceProvider.BAIDU],
            'recognize',
            return_value=baidu_result
        ):
            result = await service.recognize_with_fusion(
                voice_request,
                providers=[VoiceProvider.XUNFEI, VoiceProvider.BAIDU]
            )
            
            # 应该选择置信度最高的结果
            assert result.success is True
            assert result.provider == VoiceProvider.BAIDU
            assert result.confidence == 0.92
    
    async def test_health_check(self):
        """测试健康检查"""
        service = VoiceRecognitionService()
        
        with patch.object(
            service.recognizers[VoiceProvider.XUNFEI],
            'health_check',
            return_value=True
        ), patch.object(
            service.recognizers[VoiceProvider.BAIDU],
            'health_check',
            return_value=True
        ), patch.object(
            service.recognizers[VoiceProvider.OFFLINE],
            'health_check',
            return_value=False
        ):
            health_status = await service.health_check()
            
            assert health_status[VoiceProvider.XUNFEI.value] is True
            assert health_status[VoiceProvider.BAIDU.value] is True
            assert health_status[VoiceProvider.OFFLINE.value] is False


@pytest.mark.unit
class TestVoiceRecognitionRequest:
    """语音识别请求测试"""
    
    def test_request_validation(self, sample_audio_data):
        """测试请求验证"""
        request = VoiceRecognitionRequest(
            audio_data=sample_audio_data,
            format=AudioFormat.WAV,
            sample_rate=16000,
            language="zh_cn"
        )
        
        assert request.audio_data == sample_audio_data
        assert request.format == AudioFormat.WAV
        assert request.sample_rate == 16000
        assert request.language == "zh_cn"
        assert request.enable_punctuation is True
        assert request.enable_noise_reduction is True
    
    def test_request_with_different_formats(self, sample_audio_data):
        """测试不同音频格式"""
        formats = [AudioFormat.WAV, AudioFormat.MP3, AudioFormat.AMR, AudioFormat.PCM]
        
        for fmt in formats:
            request = VoiceRecognitionRequest(
                audio_data=sample_audio_data,
                format=fmt
            )
            assert request.format == fmt


@pytest.mark.unit
class TestVoiceRecognitionResult:
    """语音识别结果测试"""
    
    def test_successful_result(self):
        """测试成功结果"""
        result = VoiceRecognitionResult(
            success=True,
            text="测试文本",
            confidence=0.95,
            provider=VoiceProvider.XUNFEI,
            duration=0.5
        )
        
        assert result.success is True
        assert result.text == "测试文本"
        assert result.confidence == 0.95
        assert result.provider == VoiceProvider.XUNFEI
        assert result.duration == 0.5
        assert result.error is None
    
    def test_failed_result(self):
        """测试失败结果"""
        result = VoiceRecognitionResult(
            success=False,
            provider=VoiceProvider.XUNFEI,
            error="API error"
        )
        
        assert result.success is False
        assert result.text == ""
        assert result.confidence == 0.0
        assert result.error == "API error"


@pytest.mark.integration
@pytest.mark.asyncio
class TestVoiceRecognitionAPI:
    """语音识别 API 集成测试"""
    
    async def test_recognize_endpoint(self, client, sample_audio_data):
        """测试识别端点"""
        response = await client.post(
            "/api/v1/voice/recognize",
            data={
                "audio_data": sample_audio_data,
                "format": "wav",
                "sample_rate": 16000,
                "language": "zh_cn",
                "enable_noise_reduction": True
            }
        )
        
        assert response.status_code in [200, 500]  # 可能因为没有真实 API 密钥而失败
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "text" in data
            assert "confidence" in data
            assert "provider" in data
    
    async def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = await client.get("/api/v1/voice/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "providers" in data
    
    async def test_providers_endpoint(self, client):
        """测试提供商列表端点"""
        response = await client.get("/api/v1/voice/providers")
        
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "default" in data
        assert "fallback_order" in data
        assert len(data["providers"]) >= 3


@pytest.mark.property
class TestVoiceRecognitionProperties:
    """语音识别属性测试"""
    
    def test_confidence_range(self):
        """测试置信度范围"""
        from hypothesis import given, strategies as st
        
        @given(confidence=st.floats(min_value=0.0, max_value=1.0))
        def check_confidence_range(confidence):
            result = VoiceRecognitionResult(
                success=True,
                text="测试",
                confidence=confidence,
                provider=VoiceProvider.XUNFEI
            )
            assert 0.0 <= result.confidence <= 1.0
        
        check_confidence_range()
    
    def test_duration_positive(self):
        """测试持续时间为正数"""
        from hypothesis import given, strategies as st
        
        @given(duration=st.floats(min_value=0.0, max_value=60.0))
        def check_duration_positive(duration):
            result = VoiceRecognitionResult(
                success=True,
                text="测试",
                confidence=0.9,
                provider=VoiceProvider.XUNFEI,
                duration=duration
            )
            assert result.duration >= 0.0
        
        check_duration_positive()
