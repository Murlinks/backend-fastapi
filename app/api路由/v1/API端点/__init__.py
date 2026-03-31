# API 端点模块
from .auth import router as auth
from .users import router as users
from .expenses import router as expenses
from .budgets import router as budgets
from .groups import router as groups
from .ai import router as ai
from .sync import router as sync
from .payments import router as payments
from .integrations import router as integrations
from .monitoring import router as monitoring
from .feedback import router as feedback
from .personalization import router as personalization

__all__ = [
    "auth",
    "users",
    "expenses",
    "budgets",
    "groups",
    "ai",
    "sync",
    "payments",
    "integrations",
    "monitoring",
    "feedback",
    "personalization"
]