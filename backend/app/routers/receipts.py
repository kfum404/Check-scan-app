import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..db import get_db
from ..models import Receipt, ReceiptItem, User
from ..schemas import (ReceiptConfirmRequest, ReceiptDetailOut, ReceiptListResponse,
                       ReceiptOut, ScanResult, SummaryResponse)
from ..security import get_current_user
from ..services import categorize, ocr, parser

router = APIRouter(prefix="/receipts", tags=["receipts"])

LOW_CONFIDENCE_THRESHOLD = 65.0  # % уверенности Tesseract


def _save_upload(content: bytes) -> str:
    folder = Path(settings.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.jpg"
    path.write_bytes(content)
    return str(path)


def _not_found(receipt_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "RECEIPT_NOT_FOUND", "message": f"Чек {receipt_id} не найден"},
    )


@router.post("/scan", response_model=ScanResult, status_code=201)
async def scan_receipt(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Загрузка фото чека → OCR → черновик (status=draft) для экрана корректировки."""
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "message": "Фото больше 10 МБ"},
        )
    try:
        text, ocr_conf, _, _ = ocr.image_to_text_auto(
            content, settings.TESSERACT_LANG, settings.TESSERACT_PSM)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"code": "BAD_IMAGE", "message": str(e)},
        )

    parsed = parser.parse_receipt_text(text)
    items_raw = ocr.extract_items(text)

    # запасные значения, чтобы черновик всегда можно было сохранить и поправить руками
    now = datetime.now(timezone.utc)
    receipt = Receipt(
        user_id=user.id,
        shop_name=parsed.shop_name or "Не распознан",
        date=parsed.date or now,
        total_amount=parsed.total or 0.01,
        currency=parsed.currency,
        category=categorize.categorize(text, parsed.shop_name),
        status="draft",
        image_path=_save_upload(content),
        ocr_confidence=ocr_conf,
    )
    db.add(receipt)
    db.flush()
    for name, price in items_raw:
        db.add(ReceiptItem(receipt_id=receipt.id, item_name=name, price=price))
    db.commit()

    low_fields = []
    if parsed.total is None or ocr_conf < LOW_CONFIDENCE_THRESHOLD:
        low_fields.append("total_amount")
    if parsed.date is None:
        low_fields.append("date")
    if parsed.shop_name is None:
        low_fields.append("shop_name")

    detail = db.scalar(
        select(Receipt)
        .options(selectinload(Receipt.items))
        .where(Receipt.id == receipt.id)
    )
    return ScanResult(receipt=ReceiptDetailOut.model_validate(detail), low_confidence_fields=low_fields)


@router.patch("/{receipt_id}", response_model=ReceiptDetailOut)
def confirm_receipt(
    receipt_id: int,
    body: ReceiptConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Подтверждение/правка после ручной корректировки → status=confirmed."""
    receipt = db.get(Receipt, receipt_id)
    if receipt is None or receipt.user_id != user.id:
        raise _not_found(receipt_id)

    receipt.shop_name = body.shop_name
    receipt.date = body.date
    receipt.total_amount = body.total_amount
    receipt.category = body.category or receipt.category
    receipt.status = "confirmed"
    if body.items:
        receipt.items.clear()
        db.flush()
        for it in body.items:
            db.add(ReceiptItem(receipt_id=receipt.id, item_name=it.item_name, price=it.price))
    db.commit()
    return db.scalar(
        select(Receipt).options(selectinload(Receipt.items)).where(Receipt.id == receipt_id)
    )


@router.get("", response_model=ReceiptListResponse)
def list_receipts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Receipt).where(Receipt.user_id == user.id)
    if status_filter:
        stmt = stmt.where(Receipt.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Receipt.date.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return ReceiptListResponse(total=total, page=page, size=size,
                               items=[ReceiptOut.model_validate(r) for r in rows])


@router.get("/{receipt_id}", response_model=ReceiptDetailOut)
def get_receipt(receipt_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    receipt = db.scalar(
        select(Receipt)
        .options(selectinload(Receipt.items))
        .where(Receipt.id == receipt_id, Receipt.user_id == user.id)
    )
    if receipt is None:
        raise _not_found(receipt_id)
    return receipt


@router.post("/manual", response_model=ReceiptDetailOut, status_code=201)
def create_manual(
    body: ReceiptConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ручной ввод чека без фото (кнопка «Заполнить вручную» на экране Камеры)."""
    receipt = Receipt(
        user_id=user.id,
        shop_name=body.shop_name,
        date=body.date,
        total_amount=body.total_amount,
        category=body.category or "Прочее",
        status="confirmed",
    )
    db.add(receipt)
    db.flush()
    for it in body.items:
        db.add(ReceiptItem(receipt_id=receipt.id, item_name=it.item_name, price=it.price))
    db.commit()
    return db.scalar(
        select(Receipt).options(selectinload(Receipt.items)).where(Receipt.id == receipt.id)
    )


@router.delete("/{receipt_id}", status_code=204)
def delete_receipt(receipt_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    receipt = db.get(Receipt, receipt_id)
    if receipt is None or receipt.user_id != user.id:
        raise _not_found(receipt_id)
    db.delete(receipt)
    db.commit()


@router.get("/summary/home", response_model=SummaryResponse)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Баланс и последние чеки для экрана Главная."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spent = db.scalar(
        select(func.coalesce(func.sum(Receipt.total_amount), 0)).where(
            Receipt.user_id == user.id,
            Receipt.status == "confirmed",
            Receipt.date >= month_start,
        )
    ) or 0
    last = db.scalars(
        select(Receipt)
        .where(Receipt.user_id == user.id, Receipt.status == "confirmed")
        .order_by(Receipt.date.desc())
        .limit(5)
    ).all()
    return SummaryResponse(
        balance=float(spent),
        month_spent=float(spent),
        receipts=[ReceiptOut.model_validate(r) for r in last],
    )


# Статистика вынесена в routers/stats.py
