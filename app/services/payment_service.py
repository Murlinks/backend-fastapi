"""
第三方支付集成服务
实现微信支付和支付宝账单导入功能
"""
import json
import hashlib
import hmac
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import httpx
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from app.core.config import settings
from app.models.expense import Expense
from app.models.user import User


class PaymentProvider(str, Enum):
    """支付提供商"""
    WECHAT = "wechat"
    ALIPAY = "alipay"


class TransactionType(str, Enum):
    """交易类型"""
    PAYMENT = "payment"
    REFUND = "refund"
    TRANSFER = "transfer"


@dataclass
class PaymentTransaction:
    """支付交易记录"""
    transaction_id: str
    provider: PaymentProvider
    transaction_type: TransactionType
    amount: float
    description: str
    merchant_name: Optional[str]
    category: Optional[str]
    transaction_time: datetime
    status: str
    raw_data: Dict[str, Any]


@dataclass
class PaymentIntegrationConfig:
    """支付集成配置"""
    provider: PaymentProvider
    app_id: str
    app_secret: str
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    is_sandbox: bool = True


class WeChatPayService:
    """微信支付服务"""
    
    def __init__(self, config: PaymentIntegrationConfig):
        self.config = config
        self.base_url = "https://api.weixin.qq.com" if not config.is_sandbox else "https://api.weixin.qq.com"
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    async def get_access_token(self) -> str:
        """获取微信访问令牌"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token
        
        url = f"{self.base_url}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.config.app_id,
            "secret": self.config.app_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "access_token" in data:
                self.access_token = data["access_token"]
                expires_in = data.get("expires_in", 7200)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 提前5分钟过期
                return self.access_token
            else:
                raise Exception(f"获取微信访问令牌失败: {data}")
    
    async def request_bill_permission(self, user_id: str, redirect_uri: str) -> str:
        """请求账单访问权限"""
        # 构建OAuth2授权URL
        params = {
            "appid": self.config.app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "state": f"bill_access_{user_id}"
        }
        
        auth_url = f"https://open.weixin.qq.com/connect/oauth2/authorize?{urlencode(params)}#wechat_redirect"
        return auth_url
    
    async def get_user_openid(self, auth_code: str) -> str:
        """通过授权码获取用户OpenID"""
        url = f"{self.base_url}/sns/oauth2/access_token"
        params = {
            "appid": self.config.app_id,
            "secret": self.config.app_secret,
            "code": auth_code,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "openid" in data:
                return data["openid"]
            else:
                raise Exception(f"获取用户OpenID失败: {data}")
    
    async def fetch_bill_data(self, openid: str, start_date: datetime, end_date: datetime) -> List[PaymentTransaction]:
        """获取微信支付账单数据"""
        # 注意：实际的微信支付账单API需要商户号和相关权限
        # 这里提供一个模拟实现，实际使用时需要根据微信支付官方文档调整
        
        access_token = await self.get_access_token()
        
        # 模拟账单数据请求
        url = f"{self.base_url}/pay/downloadbill"
        
        # 构建请求参数（实际需要根据微信支付API文档调整）
        params = {
            "access_token": access_token,
            "bill_date": start_date.strftime("%Y%m%d"),
            "bill_type": "ALL"
        }
        
        transactions = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    # 解析账单数据（CSV格式）
                    bill_data = response.text
                    transactions = self._parse_wechat_bill_data(bill_data)
                
        except Exception as e:
            print(f"获取微信账单数据失败: {e}")
            if settings.DEBUG:
                transactions = self._generate_mock_wechat_transactions(start_date, end_date)
            else:
                raise
        
        return transactions
    
    def _parse_wechat_bill_data(self, bill_data: str) -> List[PaymentTransaction]:
        """解析微信账单数据"""
        transactions = []
        lines = bill_data.strip().split('\n')
        
        # 跳过标题行
        for line in lines[1:]:
            if line.startswith('`'):  # 微信账单数据行以`开头
                fields = line.split(',')
                if len(fields) >= 10:
                    try:
                        transaction = PaymentTransaction(
                            transaction_id=fields[5].strip('`'),  # 微信订单号
                            provider=PaymentProvider.WECHAT,
                            transaction_type=TransactionType.PAYMENT,
                            amount=float(fields[12].strip('`')),  # 订单金额
                            description=fields[7].strip('`'),  # 商品名称
                            merchant_name=fields[8].strip('`'),  # 商户名称
                            category=self._categorize_wechat_transaction(fields[7].strip('`')),
                            transaction_time=datetime.strptime(fields[0].strip('`'), '%Y-%m-%d %H:%M:%S'),
                            status=fields[9].strip('`'),  # 交易状态
                            raw_data={"fields": fields}
                        )
                        transactions.append(transaction)
                    except (ValueError, IndexError) as e:
                        print(f"解析微信账单行失败: {e}")
                        continue
        
        return transactions
    
    def _generate_mock_wechat_transactions(self, start_date: datetime, end_date: datetime) -> List[PaymentTransaction]:
        """生成模拟微信交易数据"""
        mock_transactions = [
            PaymentTransaction(
                transaction_id="wx_mock_001",
                provider=PaymentProvider.WECHAT,
                transaction_type=TransactionType.PAYMENT,
                amount=25.80,
                description="星巴克咖啡",
                merchant_name="星巴克",
                category="dining",
                transaction_time=start_date + timedelta(hours=10),
                status="SUCCESS",
                raw_data={"mock": True}
            ),
            PaymentTransaction(
                transaction_id="wx_mock_002",
                provider=PaymentProvider.WECHAT,
                transaction_type=TransactionType.PAYMENT,
                amount=12.00,
                description="地铁票",
                merchant_name="北京地铁",
                category="transportation",
                transaction_time=start_date + timedelta(hours=8),
                status="SUCCESS",
                raw_data={"mock": True}
            )
        ]
        
        return mock_transactions
    
    def _categorize_wechat_transaction(self, description: str) -> str:
        """根据交易描述自动分类"""
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ['餐厅', '咖啡', '奶茶', '外卖', '美食']):
            return "dining"
        elif any(keyword in description_lower for keyword in ['地铁', '公交', '出租车', '滴滴', '打车']):
            return "transportation"
        elif any(keyword in description_lower for keyword in ['电影', '游戏', 'ktv', '娱乐']):
            return "entertainment"
        elif any(keyword in description_lower for keyword in ['超市', '购物', '商场', '淘宝', '京东']):
            return "shopping"
        else:
            return "other"


class AlipayService:
    """支付宝服务"""
    
    def __init__(self, config: PaymentIntegrationConfig):
        self.config = config
        self.gateway_url = "https://openapi.alipay.com/gateway.do" if not config.is_sandbox else "https://openapi.alipaydev.com/gateway.do"
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成支付宝签名"""
        # 排序参数
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params if v])
        
        # 使用RSA私钥签名
        if self.config.private_key:
            # 实际实现需要使用RSA签名
            # 这里提供简化版本
            return hashlib.sha256(query_string.encode()).hexdigest()
        else:
            return hashlib.md5(query_string.encode()).hexdigest()
    
    async def request_bill_permission(self, user_id: str, redirect_uri: str) -> str:
        """请求账单访问权限"""
        # 构建支付宝OAuth2授权URL
        params = {
            "app_id": self.config.app_id,
            "method": "alipay.user.info.auth",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "scope": "auth_user",
            "redirect_uri": redirect_uri,
            "state": f"bill_access_{user_id}"
        }
        
        # 生成签名
        params["sign"] = self._generate_sign(params)
        
        auth_url = f"https://openauth.alipay.com/oauth2/publicAppAuthorize.htm?{urlencode(params)}"
        return auth_url
    
    async def get_access_token(self, auth_code: str) -> str:
        """通过授权码获取访问令牌"""
        params = {
            "app_id": self.config.app_id,
            "method": "alipay.system.oauth.token",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "grant_type": "authorization_code",
            "code": auth_code
        }
        
        params["sign"] = self._generate_sign(params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.gateway_url, data=params)
            response.raise_for_status()
            
            data = response.json()
            if "alipay_system_oauth_token_response" in data:
                token_data = data["alipay_system_oauth_token_response"]
                return token_data.get("access_token", "")
            else:
                raise Exception(f"获取支付宝访问令牌失败: {data}")
    
    async def fetch_bill_data(self, access_token: str, start_date: datetime, end_date: datetime) -> List[PaymentTransaction]:
        """获取支付宝账单数据"""
        params = {
            "app_id": self.config.app_id,
            "method": "alipay.data.dataservice.bill.downloadurl.query",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps({
                "bill_type": "trade",
                "bill_date": start_date.strftime("%Y-%m-%d")
            })
        }
        
        params["sign"] = self._generate_sign(params)
        
        transactions = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.gateway_url, data=params)
                response.raise_for_status()
                
                data = response.json()
                if "alipay_data_dataservice_bill_downloadurl_query_response" in data:
                    bill_response = data["alipay_data_dataservice_bill_downloadurl_query_response"]
                    if bill_response.get("code") == "10000":
                        # 下载账单文件
                        bill_download_url = bill_response.get("bill_download_url")
                        if bill_download_url:
                            bill_response = await client.get(bill_download_url)
                            bill_data = bill_response.text
                            transactions = self._parse_alipay_bill_data(bill_data)
                
        except Exception as e:
            print(f"获取支付宝账单数据失败: {e}")
            if settings.DEBUG:
                transactions = self._generate_mock_alipay_transactions(start_date, end_date)
            else:
                raise
        
        return transactions
    
    def _parse_alipay_bill_data(self, bill_data: str) -> List[PaymentTransaction]:
        """解析支付宝账单数据"""
        transactions = []
        lines = bill_data.strip().split('\n')
        
        # 跳过标题行
        for line in lines[5:]:  # 支付宝账单前5行是说明
            if line.strip() and not line.startswith('#'):
                fields = line.split(',')
                if len(fields) >= 15:
                    try:
                        transaction = PaymentTransaction(
                            transaction_id=fields[0],  # 交易号
                            provider=PaymentProvider.ALIPAY,
                            transaction_type=TransactionType.PAYMENT,
                            amount=float(fields[9]),  # 金额
                            description=fields[7],  # 商品名称
                            merchant_name=fields[8],  # 交易对方
                            category=self._categorize_alipay_transaction(fields[7]),
                            transaction_time=datetime.strptime(fields[4], '%Y-%m-%d %H:%M:%S'),
                            status=fields[11],  # 交易状态
                            raw_data={"fields": fields}
                        )
                        transactions.append(transaction)
                    except (ValueError, IndexError) as e:
                        print(f"解析支付宝账单行失败: {e}")
                        continue
        
        return transactions
    
    def _generate_mock_alipay_transactions(self, start_date: datetime, end_date: datetime) -> List[PaymentTransaction]:
        """生成模拟支付宝交易数据"""
        mock_transactions = [
            PaymentTransaction(
                transaction_id="alipay_mock_001",
                provider=PaymentProvider.ALIPAY,
                transaction_type=TransactionType.PAYMENT,
                amount=35.60,
                description="麦当劳",
                merchant_name="麦当劳",
                category="dining",
                transaction_time=start_date + timedelta(hours=12),
                status="TRADE_SUCCESS",
                raw_data={"mock": True}
            ),
            PaymentTransaction(
                transaction_id="alipay_mock_002",
                provider=PaymentProvider.ALIPAY,
                transaction_type=TransactionType.PAYMENT,
                amount=89.90,
                description="淘宝购物",
                merchant_name="淘宝网",
                category="shopping",
                transaction_time=start_date + timedelta(hours=15),
                status="TRADE_SUCCESS",
                raw_data={"mock": True}
            )
        ]
        
        return mock_transactions
    
    def _categorize_alipay_transaction(self, description: str) -> str:
        """根据交易描述自动分类"""
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ['餐厅', '咖啡', '奶茶', '外卖', '美食', '麦当劳', '肯德基']):
            return "dining"
        elif any(keyword in description_lower for keyword in ['地铁', '公交', '出租车', '滴滴', '打车', '共享单车']):
            return "transportation"
        elif any(keyword in description_lower for keyword in ['电影', '游戏', 'ktv', '娱乐', '音乐']):
            return "entertainment"
        elif any(keyword in description_lower for keyword in ['超市', '购物', '商场', '淘宝', '京东', '天猫']):
            return "shopping"
        else:
            return "other"


class PaymentIntegrationService:
    """支付集成服务"""
    
    def __init__(self):
        self.wechat_service = None
        self.alipay_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """初始化支付服务"""
        # 微信支付配置
        if settings.WECHAT_APP_ID and settings.WECHAT_APP_SECRET:
            wechat_config = PaymentIntegrationConfig(
                provider=PaymentProvider.WECHAT,
                app_id=settings.WECHAT_APP_ID,
                app_secret=settings.WECHAT_APP_SECRET,
                is_sandbox=settings.DEBUG
            )
            self.wechat_service = WeChatPayService(wechat_config)
        
        # 支付宝配置
        if settings.ALIPAY_APP_ID and settings.ALIPAY_PRIVATE_KEY:
            alipay_config = PaymentIntegrationConfig(
                provider=PaymentProvider.ALIPAY,
                app_id=settings.ALIPAY_APP_ID,
                app_secret="",  # 支付宝不需要app_secret
                private_key=settings.ALIPAY_PRIVATE_KEY,
                is_sandbox=settings.DEBUG
            )
            self.alipay_service = AlipayService(alipay_config)
    
    async def request_payment_permission(self, provider: PaymentProvider, user_id: str, redirect_uri: str) -> str:
        """请求支付账单访问权限"""
        if provider == PaymentProvider.WECHAT and self.wechat_service:
            return await self.wechat_service.request_bill_permission(user_id, redirect_uri)
        elif provider == PaymentProvider.ALIPAY and self.alipay_service:
            return await self.alipay_service.request_bill_permission(user_id, redirect_uri)
        else:
            raise Exception(f"不支持的支付提供商: {provider}")
    
    async def handle_auth_callback(self, provider: PaymentProvider, auth_code: str, state: str) -> Dict[str, Any]:
        """处理授权回调"""
        if provider == PaymentProvider.WECHAT and self.wechat_service:
            openid = await self.wechat_service.get_user_openid(auth_code)
            return {
                "provider": provider,
                "user_identifier": openid,
                "state": state
            }
        elif provider == PaymentProvider.ALIPAY and self.alipay_service:
            access_token = await self.alipay_service.get_access_token(auth_code)
            return {
                "provider": provider,
                "access_token": access_token,
                "state": state
            }
        else:
            raise Exception(f"不支持的支付提供商: {provider}")
    
    async def import_bill_data(
        self, 
        provider: PaymentProvider, 
        user_identifier: str, 
        start_date: datetime, 
        end_date: datetime,
        access_token: Optional[str] = None
    ) -> List[PaymentTransaction]:
        """导入账单数据"""
        if provider == PaymentProvider.WECHAT and self.wechat_service:
            return await self.wechat_service.fetch_bill_data(user_identifier, start_date, end_date)
        elif provider == PaymentProvider.ALIPAY and self.alipay_service and access_token:
            return await self.alipay_service.fetch_bill_data(access_token, start_date, end_date)
        else:
            raise Exception(f"不支持的支付提供商或缺少必要参数: {provider}")
    
    def convert_to_expense(self, transaction: PaymentTransaction, user_id: str) -> Dict[str, Any]:
        """将支付交易转换为支出记录"""
        return {
            "user_id": user_id,
            "amount": transaction.amount,
            "category": transaction.category or "other",
            "description": f"[{transaction.provider.upper()}] {transaction.description}",
            "location": transaction.merchant_name,
            "created_at": transaction.transaction_time,
            "metadata": {
                "provider": transaction.provider,
                "transaction_id": transaction.transaction_id,
                "merchant_name": transaction.merchant_name,
                "original_status": transaction.status,
                "import_source": "payment_integration"
            }
        }
    
    def is_provider_available(self, provider: PaymentProvider) -> bool:
        """检查支付提供商是否可用"""
        if provider == PaymentProvider.WECHAT:
            return self.wechat_service is not None
        elif provider == PaymentProvider.ALIPAY:
            return self.alipay_service is not None
        return False
    
    def get_available_providers(self) -> List[PaymentProvider]:
        """获取可用的支付提供商列表"""
        providers = []
        if self.wechat_service:
            providers.append(PaymentProvider.WECHAT)
        if self.alipay_service:
            providers.append(PaymentProvider.ALIPAY)
        return providers


# 全局支付集成服务实例
payment_service = PaymentIntegrationService()