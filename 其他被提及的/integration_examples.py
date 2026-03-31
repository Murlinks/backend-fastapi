"""
第三方集成使用示例
演示如何使用各种集成功能
"""
import asyncio
from app.integrations.manager import integration_manager
from app.integrations.base import IntegrationConfig, IntegrationType


async def example_deepseek_analysis():
    """DeepSeek AI分析示例"""
    print("=== DeepSeek AI分析示例 ===")
    
    deepseek = integration_manager.get_integration("deepseek")
    if not deepseek:
        print("DeepSeek集成未配置")
        return
    
    # 支出信息提取
    text = "今天在星巴克花了35元买了一杯拿铁咖啡"
    result = await deepseek.analyze_text(text, analysis_type="expense_extraction")
    
    if result.success:
        data = result.data
        print(f"✓ 支出信息提取成功:")
        print(f"  金额: {data.get('amount')}元")
        print(f"  分类: {data.get('category')}")
        print(f"  描述: {data.get('description')}")
        print(f"  置信度: {data.get('confidence')}")
    else:
        print(f"✗ 分析失败: {result.error}")
    
    # 情感分析
    text = "最近花钱太多了，感觉压力很大，不知道该怎么控制支出"
    result = await deepseek.analyze_text(text, analysis_type="emotion_analysis")
    
    if result.success:
        data = result.data
        print(f"✓ 情感分析成功:")
        print(f"  情感类型: {data.get('emotion')}")
        print(f"  压力水平: {data.get('stress_level')}/10")
        print(f"  财务压力: {'是' if data.get('financial_stress') else '否'}")
        print(f"  建议: {', '.join(data.get('suggestions', []))}")
    else:
        print(f"✗ 情感分析失败: {result.error}")


async def example_sms_service():
    """短信服务示例"""
    print("\n=== 短信服务示例 ===")
    
    sms = integration_manager.get_integration("aliyun_sms")
    if not sms:
        print("短信服务集成未配置")
        return
    
    # 发送验证码
    result = await sms.send_verification_code(
        phone_number="13800138000",
        code="123456"
    )
    
    if result.success:
        print("✓ 验证码发送成功")
        print(f"  消息ID: {result.data.get('message_id')}")
    else:
        print(f"✗ 验证码发送失败: {result.error}")


async def example_ocr_recognition():
    """OCR识别示例"""
    print("\n=== OCR识别示例 ===")
    
    ocr = integration_manager.get_integration("baidu_ocr")
    if not ocr:
        print("OCR集成未配置")
        return
    
    # 模拟图片数据（实际使用时应该是真实的图片字节数据）
    fake_image_data = b"fake_image_data_for_demo"
    
    result = await ocr.recognize_receipt(fake_image_data)
    
    if result.success:
        data = result.data
        print("✓ 票据识别成功:")
        print(f"  商家名称: {data.get('merchant_name')}")
        print(f"  总金额: {data.get('total_amount')}")
        print(f"  交易时间: {data.get('transaction_time')}")
        print(f"  商品列表: {data.get('items', [])}")
    else:
        print(f"✗ 票据识别失败: {result.error}")


async def example_voice_service():
    """语音服务示例"""
    print("\n=== 语音服务示例 ===")
    
    voice = integration_manager.get_integration("baidu_voice")
    if not voice:
        print("语音服务集成未配置")
        return
    
    # 文字转语音
    text = "您好，今天的支出总额是128元，主要用于餐饮和交通"
    result = await voice.text_to_speech(text)
    
    if result.success:
        data = result.data
        print("✓ 文字转语音成功:")
        print(f"  音频大小: {data.get('size')} 字节")
        print(f"  内容类型: {data.get('content_type')}")
        print("  音频数据已生成（base64编码）")
    else:
        print(f"✗ 文字转语音失败: {result.error}")


async def example_payment_integration():
    """支付集成示例"""
    print("\n=== 支付集成示例 ===")
    
    # 微信支付
    wechat = integration_manager.get_integration("wechat_pay")
    if wechat:
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        result = await wechat.get_transactions(start_date, end_date)
        
        if result.success:
            transactions = result.data.get('transactions', [])
            print(f"✓ 微信支付交易记录获取成功: {len(transactions)} 条")
            for tx in transactions[:3]:  # 显示前3条
                print(f"  - {tx.get('description')}: {tx.get('amount')}元")
        else:
            print(f"✗ 微信支付交易记录获取失败: {result.error}")
    else:
        print("微信支付集成未配置")
    
    # 支付宝
    alipay = integration_manager.get_integration("alipay")
    if alipay:
        result = await alipay.get_balance()
        
        if result.success:
            balance = result.data.get('balance', 0)
            print(f"✓ 支付宝余额查询成功: {balance}元")
        else:
            print(f"✗ 支付宝余额查询失败: {result.error}")
    else:
        print("支付宝集成未配置")


async def example_webhook_handling():
    """Webhook处理示例"""
    print("\n=== Webhook处理示例 ===")
    
    webhook = integration_manager.get_integration("webhook_handler")
    if not webhook:
        print("Webhook处理器未配置")
        return
    
    from app.integrations.base import WebhookEvent
    from datetime import datetime
    
    # 模拟支付完成事件
    event = WebhookEvent(
        event_id="payment_123",
        event_type="payment.completed",
        source="payment_service",
        timestamp=datetime.now(),
        data={
            "order_id": "order_123",
            "amount": 99.99,
            "user_id": "user_456",
            "payment_method": "wechat_pay"
        }
    )
    
    result = await webhook.handle_webhook(event)
    
    if result.success:
        print("✓ Webhook事件处理成功")
        print(f"  事件类型: {event.event_type}")
        print(f"  处理结果: {result.data.get('message')}")
    else:
        print(f"✗ Webhook事件处理失败: {result.error}")


async def example_integration_management():
    """集成管理示例"""
    print("\n=== 集成管理示例 ===")
    
    # 获取所有集成状态
    all_status = integration_manager.get_all_status()
    print(f"当前共有 {len(all_status)} 个集成:")
    
    for name, status in all_status.items():
        status_icon = "✓" if status["status"] == "active" else "✗"
        print(f"  {status_icon} {status['name']} ({status['type']})")
        print(f"    状态: {status['status']}")
        print(f"    成功率: {status['statistics']['success_rate']:.1f}%")
        print(f"    总请求: {status['statistics']['total_requests']}")
    
    # 健康检查
    health = await integration_manager.health_check()
    print(f"\n系统健康状况:")
    print(f"  健康分数: {health['health_score']:.1f}%")
    print(f"  活跃集成: {health['active_integrations']}/{health['total_integrations']}")
    print(f"  错误集成: {health['error_integrations']}")


async def example_test_all_integrations():
    """测试所有集成示例"""
    print("\n=== 测试所有集成 ===")
    
    results = await integration_manager.test_all_integrations()
    
    success_count = 0
    for name, result in results.items():
        status_icon = "✓" if result.success else "✗"
        print(f"  {status_icon} {name}")
        
        if result.success:
            success_count += 1
            if result.response_time:
                print(f"    响应时间: {result.response_time:.3f}s")
        else:
            print(f"    错误: {result.error}")
    
    print(f"\n测试结果: {success_count}/{len(results)} 个集成通过测试")


async def main():
    """主函数 - 运行所有示例"""
    print("第三方集成系统使用示例")
    print("=" * 50)
    
    # 检查集成管理器是否已初始化
    if not integration_manager.is_initialized():
        print("集成管理器未初始化，请先启动应用")
        return
    
    try:
        # 运行各种示例
        await example_integration_management()
        await example_test_all_integrations()
        await example_deepseek_analysis()
        await example_sms_service()
        await example_ocr_recognition()
        await example_voice_service()
        await example_payment_integration()
        await example_webhook_handling()
        
        print("\n" + "=" * 50)
        print("所有示例运行完成！")
        
    except Exception as e:
        print(f"运行示例时发生错误: {e}")


if __name__ == "__main__":
    # 注意：这个脚本需要在应用启动后运行，或者手动初始化集成系统
    print("请在应用启动后运行此示例，或者通过API接口测试集成功能")
    print("API文档地址: http://localhost:8000/docs")