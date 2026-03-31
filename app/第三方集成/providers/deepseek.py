"""
DeepSeek AI服务集成
"""
import httpx
import json
from typing import List, Dict, Any
import logging

from ..base import AIServiceIntegration, IntegrationResponse
from ..registry import register_integration

logger = logging.getLogger(__name__)


@register_integration("deepseek")
class DeepSeekIntegration(AIServiceIntegration):
    """DeepSeek AI服务集成"""
    
    @property
    def name(self) -> str:
        return "DeepSeek AI"
    
    @property
    def required_credentials(self) -> List[str]:
        return ["api_key", "api_url"]
    
    async def initialize(self) -> bool:
        """初始化DeepSeek服务"""
        try:
            self.client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.config.credentials['api_key']}",
                    "Content-Type": "application/json"
                }
            )
            
            # 测试连接
            test_result = await self.test_connection()
            return test_result.success
            
        except Exception as e:
            logger.error(f"DeepSeek初始化失败: {e}")
            return False
    
    async def test_connection(self) -> IntegrationResponse:
        """测试DeepSeek连接"""
        try:
            response = await self.client.post(
                f"{self.config.credentials['api_url']}/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                }
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
    
    async def analyze_text(self, text: str, **kwargs) -> IntegrationResponse:
        """分析文本"""
        analysis_type = kwargs.get("analysis_type", "general")
        
        if analysis_type == "expense_extraction":
            return await self._extract_expense_info(text)
        elif analysis_type == "emotion_analysis":
            return await self._analyze_emotion(text)
        elif analysis_type == "impulse_detection":
            return await self._detect_impulse_buying(text, kwargs.get("amount"))
        else:
            return await self._general_analysis(text)
    
    async def generate_response(self, prompt: str, **kwargs) -> IntegrationResponse:
        """生成AI响应"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # 添加上下文消息
            if "context" in kwargs:
                context_messages = kwargs["context"]
                if isinstance(context_messages, list):
                    messages = context_messages + messages
            
            response = await self.client.post(
                f"{self.config.credentials['api_url']}/v1/chat/completions",
                json={
                    "model": kwargs.get("model", "deepseek-chat"),
                    "messages": messages,
                    "max_tokens": kwargs.get("max_tokens", 500),
                    "temperature": kwargs.get("temperature", 0.7)
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                return IntegrationResponse(
                    success=True,
                    data={
                        "response": content,
                        "usage": data.get("usage", {}),
                        "model": data.get("model")
                    },
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
                error=f"生成响应失败: {str(e)}"
            )
    
    async def _extract_expense_info(self, text: str) -> IntegrationResponse:
        """提取支出信息"""
        prompt = f"""
        请从以下文本中提取支出信息，返回JSON格式：
        {{
            "amount": 金额(数字),
            "category": "分类(dining/transportation/shopping/entertainment/healthcare/education/other)",
            "description": "描述",
            "confidence": 置信度(0-1)
        }}
        
        文本: {text}
        """
        
        response = await self.generate_response(prompt, max_tokens=200, temperature=0.3)
        
        if response.success:
            try:
                # 尝试解析JSON
                content = response.data["response"]
                # 提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return IntegrationResponse(
                        success=True,
                        data=result
                    )
                else:
                    return IntegrationResponse(
                        success=False,
                        error="无法解析AI返回的JSON"
                    )
            except json.JSONDecodeError:
                return IntegrationResponse(
                    success=False,
                    error="AI返回的不是有效JSON格式"
                )
        
        return response
    
    async def _analyze_emotion(self, text: str) -> IntegrationResponse:
        """分析情感"""
        prompt = f"""
        请分析以下文本的情感状态，返回JSON格式：
        {{
            "emotion": "情感类型(happy/sad/angry/anxious/neutral/excited/stressed)",
            "confidence": 置信度(0-1),
            "stress_level": 压力水平(0-10),
            "financial_stress": 是否有财务压力(true/false),
            "suggestions": ["建议1", "建议2"]
        }}
        
        文本: {text}
        """
        
        response = await self.generate_response(prompt, max_tokens=300, temperature=0.5)
        
        if response.success:
            try:
                content = response.data["response"]
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return IntegrationResponse(
                        success=True,
                        data=result
                    )
            except json.JSONDecodeError:
                pass
        
        return IntegrationResponse(
            success=False,
            error="情感分析失败"
        )
    
    async def _detect_impulse_buying(self, text: str, amount: float = None) -> IntegrationResponse:
        """检测冲动消费"""
        prompt = f"""
        请分析以下文本是否存在冲动消费行为，返回JSON格式：
        {{
            "is_impulse": 是否冲动消费(true/false),
            "confidence": 置信度(0-1),
            "risk_factors": ["风险因素1", "风险因素2"],
            "suggestions": ["建议1", "建议2"]
        }}
        
        文本: {text}
        """
        
        if amount:
            prompt += f"\n金额: {amount}元"
        
        response = await self.generate_response(prompt, max_tokens=300, temperature=0.4)
        
        if response.success:
            try:
                content = response.data["response"]
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return IntegrationResponse(
                        success=True,
                        data=result
                    )
            except json.JSONDecodeError:
                pass
        
        return IntegrationResponse(
            success=False,
            error="冲动消费检测失败"
        )
    
    async def _general_analysis(self, text: str) -> IntegrationResponse:
        """通用分析"""
        prompt = f"""
        请分析以下文本并提供有用的财务建议：
        
        文本: {text}
        
        请提供简洁明了的分析和建议。
        """
        
        return await self.generate_response(prompt, max_tokens=400, temperature=0.7)
    
    async def cleanup(self) -> None:
        """清理资源"""
        if hasattr(self, 'client'):
            await self.client.aclose()