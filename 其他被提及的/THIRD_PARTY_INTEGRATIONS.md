# 第三方集成系统文档

## 概述

本项目提供了完整的第三方集成框架，支持多种类型的第三方服务集成，包括支付服务、AI服务、短信服务、OCR识别、语音服务等。

## 架构设计

### 核心组件

1. **BaseIntegration**: 所有集成的基础抽象类
2. **IntegrationManager**: 集成管理器，负责统一管理所有集成
3. **IntegrationRegistry**: 集成注册表，自动发现和注册集成类
4. **IntegrationConfig**: 集成配置模型
5. **IntegrationResponse**: 统一的响应格式

### 集成类型

- **PAYMENT**: 支付服务（微信支付、支付宝）
- **AI_SERVICE**: AI服务（DeepSeek）
- **SMS**: 短信服务（阿里云短信）
- **OCR**: OCR识别（百度OCR）
- **VOICE**: 语音服务（百度语音）
- **WEBHOOK**: Webhook处理器
- **BANK**: 银行服务（预留）
- **ANALYTICS**: 数据分析（预留）
- **NOTIFICATION**: 通知服务（预留）
- **STORAGE**: 存储服务（预留）

## 已实现的集成

### 1. DeepSeek AI服务
- **功能**: 文本分析、支出信息提取、情感分析、冲动消费检测
- **配置**: API密钥、API地址
- **用途**: 智能分析用户输入，提供财务建议

### 2. 阿里云短信服务
- **功能**: 发送短信、发送验证码
- **配置**: AccessKey、SecretKey
- **用途**: 用户验证、通知发送

### 3. 微信支付集成
- **功能**: 获取交易记录、账户余额
- **配置**: AppID、AppSecret
- **用途**: 导入微信支付账单

### 4. 支付宝集成
- **功能**: 获取交易记录、账户余额
- **配置**: AppID、私钥
- **用途**: 导入支付宝账单

### 5. 百度OCR识别
- **功能**: 文本识别、票据识别
- **配置**: API Key、Secret Key
- **用途**: 识别发票、收据等财务凭证

### 6. 百度语音服务
- **功能**: 语音转文字、文字转语音
- **配置**: API Key、Secret Key
- **用途**: 语音记账、语音播报

### 7. Webhook处理器
- **功能**: 处理各种Webhook事件
- **配置**: Webhook密钥
- **用途**: 接收和处理第三方服务的回调事件

## 配置说明

### 环境变量配置

```bash
# DeepSeek AI
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_URL=https://api.deepseek.com

# 阿里云短信
SMS_ACCESS_KEY=your_aliyun_access_key
SMS_SECRET_KEY=your_aliyun_secret_key

# 微信支付
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

# 支付宝
ALIPAY_APP_ID=your_alipay_app_id
ALIPAY_PRIVATE_KEY=your_alipay_private_key

# 百度OCR
BAIDU_OCR_API_KEY=your_baidu_ocr_api_key
BAIDU_OCR_SECRET_KEY=your_baidu_ocr_secret_key

# 百度语音
BAIDU_VOICE_API_KEY=your_baidu_voice_api_key
BAIDU_VOICE_SECRET_KEY=your_baidu_voice_secret_key

# Webhook
WEBHOOK_SECRET=your_webhook_secret

# 集成系统控制
INTEGRATIONS_ENABLED=true
INTEGRATIONS_AUTO_INIT=true
```

### 程序化配置

```python
from app.integrations.base import IntegrationConfig, IntegrationType

# 创建集成配置
config = IntegrationConfig(
    name="deepseek",
    type=IntegrationType.AI_SERVICE,
    enabled=True,
    credentials={
        "api_key": "your_api_key",
        "api_url": "https://api.deepseek.com"
    },
    config={
        "model": "deepseek-chat",
        "max_tokens": 500,
        "temperature": 0.7
    },
    timeout=30,
    retry_count=3
)

# 初始化集成
from app.integrations.manager import integration_manager
success = await integration_manager.initialize_integration("deepseek", config)
```

## API接口

### 集成管理接口

#### 获取可用集成
```http
GET /api/v1/integrations/available
```

#### 获取集成状态
```http
GET /api/v1/integrations/status
GET /api/v1/integrations/status/{integration_name}
```

#### 配置集成
```http
POST /api/v1/integrations/configure/{integration_name}
Content-Type: application/json

{
    "name": "deepseek",
    "type": "ai_service",
    "enabled": true,
    "credentials": {
        "api_key": "your_api_key",
        "api_url": "https://api.deepseek.com"
    },
    "config": {
        "model": "deepseek-chat"
    }
}
```

#### 测试集成
```http
POST /api/v1/integrations/test/{integration_name}
POST /api/v1/integrations/test-all
```

#### 启用/禁用集成
```http
POST /api/v1/integrations/enable/{integration_name}
POST /api/v1/integrations/disable/{integration_name}
```

#### 处理Webhook
```http
POST /api/v1/integrations/webhook/{webhook_url}
Content-Type: application/json

{
    "event_id": "event_123",
    "event_type": "payment.completed",
    "source": "payment_service",
    "data": {
        "order_id": "order_123",
        "amount": 100.00
    }
}
```

## 使用示例

### 1. 使用DeepSeek分析文本

```python
from app.integrations.manager import integration_manager

# 获取DeepSeek集成
deepseek = integration_manager.get_integration("deepseek")

if deepseek:
    # 分析支出信息
    result = await deepseek.analyze_text(
        "今天在星巴克花了35元买咖啡",
        analysis_type="expense_extraction"
    )
    
    if result.success:
        expense_info = result.data
        print(f"金额: {expense_info['amount']}")
        print(f"分类: {expense_info['category']}")
        print(f"描述: {expense_info['description']}")
```

### 2. 发送短信验证码

```python
# 获取短信集成
sms = integration_manager.get_integration("aliyun_sms")

if sms:
    # 发送验证码
    result = await sms.send_verification_code(
        phone_number="13800138000",
        code="123456"
    )
    
    if result.success:
        print("验证码发送成功")
    else:
        print(f"发送失败: {result.error}")
```

### 3. OCR识别票据

```python
# 获取OCR集成
ocr = integration_manager.get_integration("baidu_ocr")

if ocr:
    # 读取图片文件
    with open("receipt.jpg", "rb") as f:
        image_data = f.read()
    
    # 识别票据
    result = await ocr.recognize_receipt(image_data)
    
    if result.success:
        receipt_info = result.data
        print(f"商家: {receipt_info['merchant']}")
        print(f"金额: {receipt_info['amount']}")
        print(f"时间: {receipt_info['date']}")
```

## 扩展开发

### 创建新的集成

1. **继承基础类**

```python
from app.integrations.base import BaseIntegration, IntegrationType, IntegrationResponse
from app.integrations.registry import register_integration

@register_integration("my_service")
class MyServiceIntegration(BaseIntegration):
    @property
    def name(self) -> str:
        return "我的服务"
    
    @property
    def type(self) -> IntegrationType:
        return IntegrationType.ANALYTICS
    
    @property
    def required_credentials(self) -> List[str]:
        return ["api_key", "api_secret"]
    
    async def initialize(self) -> bool:
        # 初始化逻辑
        return True
    
    async def test_connection(self) -> IntegrationResponse:
        # 测试连接逻辑
        return IntegrationResponse(success=True)
    
    async def cleanup(self) -> None:
        # 清理逻辑
        pass
```

2. **注册集成**

集成类会通过装饰器自动注册，也可以手动注册：

```python
from app.integrations.registry import integration_registry
integration_registry.register("my_service", MyServiceIntegration)
```

3. **添加配置**

在 `app/core/config.py` 中添加配置：

```python
def get_integration_configs(self) -> Dict[str, Dict[str, Any]]:
    configs = {
        # ... 其他配置
        "my_service": {
            "name": "my_service",
            "type": "analytics",
            "enabled": bool(self.MY_SERVICE_API_KEY),
            "credentials": {
                "api_key": self.MY_SERVICE_API_KEY,
                "api_secret": self.MY_SERVICE_API_SECRET
            }
        }
    }
    return configs
```

## 监控和日志

### 集成状态监控

```python
# 获取所有集成状态
status = integration_manager.get_all_status()

for name, info in status.items():
    print(f"{name}: {info['status']}")
    print(f"  成功率: {info['statistics']['success_rate']:.1f}%")
    print(f"  总请求: {info['statistics']['total_requests']}")
```

### 健康检查

```python
# 系统健康检查
health = await integration_manager.health_check()
print(f"健康分数: {health['health_score']:.1f}%")
print(f"活跃集成: {health['active_integrations']}/{health['total_integrations']}")
```

### 日志记录

所有集成操作都会记录详细日志，包括：
- 请求和响应信息
- 错误和异常
- 性能指标
- 状态变化

## 安全考虑

1. **凭证管理**: 所有API密钥和敏感信息都通过环境变量管理
2. **签名验证**: Webhook事件支持签名验证
3. **访问控制**: API接口需要用户认证
4. **错误处理**: 统一的错误处理和重试机制
5. **日志安全**: 敏感信息不会记录到日志中

## 性能优化

1. **连接池**: HTTP客户端使用连接池
2. **重试机制**: 自动重试失败的请求
3. **超时控制**: 可配置的请求超时时间
4. **限流保护**: 支持速率限制配置
5. **异步处理**: 所有操作都是异步的

## 故障排除

### 常见问题

1. **集成初始化失败**
   - 检查环境变量配置
   - 验证API密钥有效性
   - 查看详细错误日志

2. **API调用失败**
   - 检查网络连接
   - 验证API配额和限制
   - 查看响应状态码

3. **Webhook事件处理失败**
   - 验证签名配置
   - 检查事件格式
   - 查看处理器日志

### 调试工具

```python
# 测试单个集成
result = await integration_manager.test_integration("deepseek")
print(f"测试结果: {result.success}")
if not result.success:
    print(f"错误信息: {result.error}")

# 测试所有集成
results = await integration_manager.test_all_integrations()
for name, result in results.items():
    print(f"{name}: {'✓' if result.success else '✗'}")
```

## 更新日志

### v1.0.0 (2024-01-26)
- 初始版本发布
- 支持7种集成类型
- 完整的管理API
- 自动发现和注册机制
- Webhook事件处理
- 健康检查和监控功能