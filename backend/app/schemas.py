from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- auth ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user: "UserResponse"


# ---------- receipts ----------
class ReceiptItemOut(BaseModel):
    id: int
    item_name: str
    price: float

    model_config = {"from_attributes": True}


class ReceiptOut(BaseModel):
    id: int
    shop_name: str
    date: datetime
    total_amount: float
    currency: str
    category: str
    status: str

    model_config = {"from_attributes": True}


class ReceiptDetailOut(ReceiptOut):
    items: list[ReceiptItemOut] = []
    ocr_confidence: float | None = None


class ScanResult(BaseModel):
    """Ответ POST /receipts/scan: черновик + сырые данные для экрана корректировки."""
    receipt: ReceiptDetailOut
    low_confidence_fields: list[str] = Field(
        default_factory=list,
        description="Поля, которые OCR распознал с низкой уверенностью — "
                    "клиент подсвечивает их на экране корректировки",
    )


class ReceiptConfirmRequest(BaseModel):
    shop_name: str = Field(min_length=1, max_length=150)
    date: datetime
    total_amount: float = Field(gt=0, le=10_000)
    category: str | None = None
    items: list[ReceiptItemOut] = []


class ReceiptListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ReceiptOut]


# ---------- summary / stats ----------
class SummaryResponse(BaseModel):
    balance: float            # «2 840 Br» с экрана Главная
    month_spent: float
    receipts: list[ReceiptOut]


class StatsEntry(BaseModel):
    label: str                # «Пн»…«Вс» или название категории
    amount: float


class WeeklyStatsResponse(BaseModel):
    by_day: list[StatsEntry]
    by_category: list[StatsEntry]


# ---------- user ----------
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    notifications_enabled: bool
    autosave_enabled: bool
    biometrics_enabled: bool
    theme_preference: str
    monthly_budget: float

    model_config = {"from_attributes": True}


class UserPatchRequest(BaseModel):
    name: str | None = None
    notifications_enabled: bool | None = None
    autosave_enabled: bool | None = None
    biometrics_enabled: bool | None = None
    theme_preference: str | None = Field(default=None, pattern="^(light|dark)$")
    monthly_budget: float | None = Field(default=None, gt=0, le=1_000_000)


class ErrorResponse(BaseModel):
    code: str
    message: str
    fields: list[str] = []
