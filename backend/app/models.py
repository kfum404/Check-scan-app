from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, String,
                        Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), default="Саныч")
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    autosave_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    biometrics_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    theme_preference: Mapped[str] = mapped_column(String(10), default="light")
    monthly_budget: Mapped[float] = mapped_column(Numeric(10, 2), default=5000)

    receipts: Mapped[list["Receipt"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    shop_name: Mapped[str] = mapped_column(String(150), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="BYN")
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # draft — распознан, ждёт подтверждения на экране «Карандаш»;
    # confirmed — попал в историю/аналитику.
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    user: Mapped[User] = relationship(back_populates="receipts")
    items: Mapped[list["ReceiptItem"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), index=True
    )
    item_name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    receipt: Mapped[Receipt] = relationship(back_populates="items")
