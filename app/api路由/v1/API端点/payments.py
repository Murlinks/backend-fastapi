"""第三方支付集成API：微信/支付宝账单导入"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import csv
import io
import zipfile
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.payment_service import payment_service, PaymentProvider, PaymentTransaction
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.expense import Expense
from app.models.payment_authorization import PaymentAuthorization
from app.core.database import get_db

router = APIRouter()


class PaymentAuthRequest(BaseModel):
    """支付授权请求"""
    provider: PaymentProvider
    redirect_uri: str


class PaymentAuthResponse(BaseModel):
    """支付授权响应"""
    auth_url: str
    provider: PaymentProvider
    state: str


class BillImportRequest(BaseModel):
    """账单导入请求"""
    provider: PaymentProvider
    start_date: datetime
    end_date: datetime
    auth_code: Optional[str] = None
    access_token: Optional[str] = None
    user_identifier: Optional[str] = None


class BillImportResponse(BaseModel):
    """账单导入响应"""
    success: bool
    imported_count: int
    skipped_count: int
    transactions: List[dict]
    message: str


class FileImportResponse(BaseModel):
    success: bool
    imported_count: int
    skipped_count: int
    parsed_count: int
    provider: PaymentProvider
    message: str


class PaymentProviderInfo(BaseModel):
    """支付提供商信息"""
    provider: PaymentProvider
    name: str
    is_available: bool
    requires_auth: bool


def _pick_field(row: Dict[str, Any], aliases: List[str]) -> str:
    for key in aliases:
        if key in row and str(row[key]).strip():
            return str(row[key]).strip()
    return ""


def _parse_amount(amount_text: str) -> float:
    cleaned = amount_text.replace("¥", "").replace("￥", "").replace(",", "").strip()
    if not cleaned:
        return 0.0
    return abs(float(cleaned))


def _parse_datetime(value: str) -> datetime:
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(value.strip(), pattern)
        except Exception:
            continue
    return datetime.utcnow()


def _normalize_csv_text(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "gbk", "utf-16"):
        try:
            return raw_bytes.decode(encoding)
        except Exception:
            continue
    return raw_bytes.decode("utf-8", errors="ignore")


def _parse_wechat_personal_csv(csv_text: str) -> List[PaymentTransaction]:
    transactions: List[PaymentTransaction] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        amount_text = _pick_field(row, ["金额(元)", "金额", "收/支金额(元)", "收支金额(元)"])
        io_type = _pick_field(row, ["收/支", "收支类型"])
        status = _pick_field(row, ["当前状态", "交易状态"]) or "UNKNOWN"
        if not amount_text or "支出" not in io_type:
            continue
        description = _pick_field(row, ["商品", "商品说明", "交易类型"]) or "微信账单导入"
        merchant_name = _pick_field(row, ["交易对方", "商户"]) or None
        trade_time = _pick_field(row, ["交易时间", "记账时间"])
        transaction_id = _pick_field(row, ["交易单号", "微信支付业务单号", "资金流水单号"])
        if not transaction_id:
            transaction_id = "wx_csv_" + hashlib.md5(
                f"{trade_time}_{amount_text}_{description}".encode()
            ).hexdigest()[:16]
        transactions.append(
            PaymentTransaction(
                transaction_id=transaction_id,
                provider=PaymentProvider.WECHAT,
                transaction_type="payment",
                amount=_parse_amount(amount_text),
                description=description,
                merchant_name=merchant_name,
                category=None,
                transaction_time=_parse_datetime(trade_time or ""),
                status=status,
                raw_data=row,
            )
        )
    return transactions


def _parse_alipay_personal_csv(csv_text: str) -> List[PaymentTransaction]:
    transactions: List[PaymentTransaction] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        amount_text = _pick_field(row, ["金额", "交易金额（元）", "交易金额(元)"])
        io_type = _pick_field(row, ["收/支", "收支类型"])
        status = _pick_field(row, ["交易状态", "状态"]) or "UNKNOWN"
        if not amount_text or "支出" not in io_type:
            continue
        description = _pick_field(row, ["商品说明", "商品名称", "备注"]) or "支付宝账单导入"
        merchant_name = _pick_field(row, ["交易对方", "对方账号"]) or None
        trade_time = _pick_field(row, ["交易创建时间", "交易时间"])
        transaction_id = _pick_field(row, ["交易号", "支付宝交易号", "商家订单号"])
        if not transaction_id:
            transaction_id = "alipay_csv_" + hashlib.md5(
                f"{trade_time}_{amount_text}_{description}".encode()
            ).hexdigest()[:16]
        transactions.append(
            PaymentTransaction(
                transaction_id=transaction_id,
                provider=PaymentProvider.ALIPAY,
                transaction_type="payment",
                amount=_parse_amount(amount_text),
                description=description,
                merchant_name=merchant_name,
                category=None,
                transaction_time=_parse_datetime(trade_time or ""),
                status=status,
                raw_data=row,
            )
        )
    return transactions


async def _upsert_authorization(
    db: AsyncSession,
    user_id: str,
    provider: PaymentProvider,
    user_identifier: Optional[str] = None,
    access_token: Optional[str] = None,
) -> None:
    stmt = select(PaymentAuthorization).where(
        PaymentAuthorization.user_id == user_id,
        PaymentAuthorization.provider == provider.value,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record:
        if user_identifier:
            record.user_identifier = user_identifier
        if access_token:
            record.access_token = access_token
        record.last_authorized_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()
        return
    db.add(
        PaymentAuthorization(
            user_id=user_id,
            provider=provider.value,
            user_identifier=user_identifier,
            access_token=access_token,
            last_authorized_at=datetime.utcnow(),
        )
    )


async def _get_authorization(
    db: AsyncSession,
    user_id: str,
    provider: PaymentProvider,
) -> Optional[PaymentAuthorization]:
    stmt = select(PaymentAuthorization).where(
        PaymentAuthorization.user_id == user_id,
        PaymentAuthorization.provider == provider.value,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _persist_transactions(
    db: AsyncSession,
    user: User,
    transactions: List[PaymentTransaction],
) -> Dict[str, Any]:
    imported_count = 0
    skipped_count = 0
    imported_transactions = []
    for transaction in transactions:
        exists_stmt = select(Expense.id).where(
            Expense.user_id == user.id,
            Expense.description.contains(str(transaction.transaction_id)),
        )
        existing_expense = await db.execute(exists_stmt)
        if existing_expense.scalar_one_or_none() is not None:
            skipped_count += 1
            continue
        expense_data = payment_service.convert_to_expense(transaction, str(user.id))
        expense = Expense(
            user_id=user.id,
            amount=expense_data["amount"],
            category=expense_data["category"],
            description=expense_data["description"],
            location=expense_data.get("location"),
            created_at=expense_data["created_at"]
        )
        db.add(expense)
        imported_count += 1
        imported_transactions.append({
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "description": transaction.description,
            "merchant_name": transaction.merchant_name,
            "category": transaction.category,
            "transaction_time": transaction.transaction_time.isoformat(),
            "provider": transaction.provider,
        })
    return {
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "transactions": imported_transactions,
    }


@router.get("/providers", response_model=List[PaymentProviderInfo])
async def get_payment_providers():
    """获取可用的支付提供商列表"""
    providers_info = [
        PaymentProviderInfo(
            provider=PaymentProvider.WECHAT,
            name="微信支付",
            is_available=payment_service.is_provider_available(PaymentProvider.WECHAT),
            requires_auth=True
        ),
        PaymentProviderInfo(
            provider=PaymentProvider.ALIPAY,
            name="支付宝",
            is_available=payment_service.is_provider_available(PaymentProvider.ALIPAY),
            requires_auth=True
        ),
    ]
    return providers_info


@router.post("/auth", response_model=PaymentAuthResponse)
async def request_payment_auth(
    auth_request: PaymentAuthRequest,
    current_user: User = Depends(get_current_user)
):
    """请求支付账单访问权限，返回授权URL"""
    if not payment_service.is_provider_available(auth_request.provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"支付提供商 {auth_request.provider} 不可用"
        )
    
    try:
        auth_url = await payment_service.request_payment_permission(
            provider=auth_request.provider,
            user_id=str(current_user.id),
            redirect_uri=auth_request.redirect_uri
        )
        
        return PaymentAuthResponse(
            auth_url=auth_url,
            provider=auth_request.provider,
            state=f"bill_access_{current_user.id}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"请求授权失败: {str(e)}"
        )


@router.post("/auth/callback")
async def handle_auth_callback(
    provider: PaymentProvider,
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="状态参数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """处理支付授权回调"""
    expected_state = f"bill_access_{current_user.id}"
    if state != expected_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的状态参数"
        )
    
    try:
        auth_result = await payment_service.handle_auth_callback(
            provider=provider,
            auth_code=code,
            state=state
        )
        
        user_identifier = auth_result.get("user_identifier")
        access_token = auth_result.get("access_token")
        await _upsert_authorization(
            db=db,
            user_id=str(current_user.id),
            provider=provider,
            user_identifier=user_identifier,
            access_token=access_token,
        )
        await db.commit()

        return {
            "success": True,
            "message": "授权成功",
            "provider": provider,
            "auth_result": auth_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理授权回调失败: {str(e)}"
        )


@router.post("/import", response_model=BillImportResponse)
async def import_bill_data(
    import_request: BillImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导入支付账单数据为支出记录"""
    if not payment_service.is_provider_available(import_request.provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"支付提供商 {import_request.provider} 不可用"
        )
    if import_request.end_date <= import_request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="结束日期必须大于开始日期"
        )
    max_range = timedelta(days=90)
    if import_request.end_date - import_request.start_date > max_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="导入时间范围不能超过3个月"
        )
    
    try:
        access_token = import_request.access_token
        user_identifier = import_request.user_identifier or ""
        if import_request.provider == PaymentProvider.ALIPAY and not access_token:
            auth_record = await _get_authorization(db, str(current_user.id), PaymentProvider.ALIPAY)
            if auth_record and auth_record.access_token:
                access_token = auth_record.access_token
        if import_request.provider == PaymentProvider.WECHAT and not user_identifier:
            auth_record = await _get_authorization(db, str(current_user.id), PaymentProvider.WECHAT)
            if auth_record and auth_record.user_identifier:
                user_identifier = auth_record.user_identifier
        transactions = await payment_service.import_bill_data(
            provider=import_request.provider,
            user_identifier=user_identifier,
            start_date=import_request.start_date,
            end_date=import_request.end_date,
            access_token=access_token
        )
        persist_result = await _persist_transactions(db, current_user, transactions)
        await db.commit()
        return BillImportResponse(
            success=True,
            imported_count=persist_result["imported_count"],
            skipped_count=persist_result["skipped_count"],
            transactions=persist_result["transactions"],
            message=f"成功导入 {persist_result['imported_count']} 条记录，跳过 {persist_result['skipped_count']} 条重复记录"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入账单数据失败: {str(e)}"
        )


@router.post("/import/file", response_model=FileImportResponse)
async def import_bill_file(
    provider: PaymentProvider = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传微信/支付宝个人账单CSV或ZIP并导入支出"""
    filename = (file.filename or "").lower()
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")

    try:
        if filename.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
                csv_names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
                if not csv_names:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ZIP中未找到CSV文件")
                raw_bytes = zf.read(csv_names[0])
        elif not filename.endswith(".csv"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持CSV或ZIP文件")
    except zipfile.BadZipFile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ZIP文件损坏或格式非法")

    csv_text = _normalize_csv_text(raw_bytes)
    if provider == PaymentProvider.WECHAT:
        transactions = _parse_wechat_personal_csv(csv_text)
    elif provider == PaymentProvider.ALIPAY:
        transactions = _parse_alipay_personal_csv(csv_text)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="暂不支持该平台文件导入")

    if not transactions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未从账单中解析到可导入的支出记录")

    try:
        persist_result = await _persist_transactions(db, current_user, transactions)
        await db.commit()
        return FileImportResponse(
            success=True,
            imported_count=persist_result["imported_count"],
            skipped_count=persist_result["skipped_count"],
            parsed_count=len(transactions),
            provider=provider,
            message=f"文件解析{len(transactions)}条，成功导入{persist_result['imported_count']}条，跳过{persist_result['skipped_count']}条",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件导入失败: {str(e)}"
        )


@router.get("/history")
async def get_import_history(
    provider: Optional[PaymentProvider] = Query(None, description="支付提供商筛选"),
    limit: int = Query(50, ge=1, le=100, description="返回记录数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取支付导入的支出历史"""
    conditions = [
        Expense.user_id == current_user.id,
        Expense.description.like("[%]%"),
    ]

    if provider:
        conditions.append(Expense.description.like(f"[{provider.value.upper()}]%"))

    stmt = (
        select(
            Expense.id,
            Expense.amount,
            Expense.category,
            Expense.description,
            Expense.location,
            Expense.created_at,
        )
        .where(*conditions)
        .order_by(Expense.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    expenses = result.all()

    count_stmt = select(func.count()).select_from(Expense).where(*conditions)
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar_one() or 0
    
    return {
        "expenses": [
            {
                "id": str(expense.id),
                "amount": float(expense.amount),
                "category": expense.category,
                "description": expense.description,
                "location": expense.location,
                "created_at": expense.created_at.isoformat(),
            }
            for expense in expenses
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


@router.delete("/disconnect/{provider}")
async def disconnect_payment_provider(
    provider: PaymentProvider,
    current_user: User = Depends(get_current_user)
):
    """断开支付提供商连接"""
    return {
        "success": True,
        "message": f"已断开与 {provider} 的连接",
        "provider": provider
    }


@router.get("/test/{provider}")
async def test_payment_integration(
    provider: PaymentProvider,
    current_user: User = Depends(get_current_user)
):
    """测试支付集成（仅DEBUG环境）"""
    from app.core.config import settings
    
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="测试接口仅在开发环境可用"
        )
    
    if not payment_service.is_provider_available(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"支付提供商 {provider} 不可用"
        )
    
    try:
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        transactions = await payment_service.import_bill_data(
            provider=provider,
            user_identifier="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "provider": provider,
            "test_transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "amount": t.amount,
                    "description": t.description,
                    "category": t.category,
                    "transaction_time": t.transaction_time.isoformat()
                }
                for t in transactions
            ],
            "message": f"测试成功，获取到 {len(transactions)} 条模拟交易记录"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试失败: {str(e)}"
        )