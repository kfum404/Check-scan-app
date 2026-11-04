"""Push-уведомления через Expo Push API.

После каждого сохранённого чека проверяем месячный итог: при пересечении
80% лимита — предупреждение, при пересечении 100% — алерт. Повторно одно
и то же уведомление не шлём (шлём только в момент пересечения порога).
Отправка идёт в фоновом потоке, чтобы не задерживать ответ API.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone

from sqlalchemy import func, select

from ..db import SessionLocal
from ..models import Receipt, User

log = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
WARN_RATIO = 0.8


def _month_total_confirmed(db, user_id: int) -> float:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0,
                              tzinfo=None)  # наивное, как в stats.py
    # Важно: месяц считаем по created_at (когда чек сохранили), а не по дате
    # на чеке — иначе скан старого чека не попадает в текущий месяц и лимит
    # «молча» не срабатывает. Для старых строк created_at = date (backfill).
    month_field = func.coalesce(Receipt.created_at, Receipt.date)
    total = db.scalar(
        select(func.coalesce(func.sum(Receipt.total_amount), 0)).where(
            Receipt.user_id == user_id,
            Receipt.status == "confirmed",
            month_field >= month_start,
        )
    )
    return float(total or 0)


def budget_event(budget: float, before: float, after: float) -> tuple[str, str] | None:
    """Событие для уведомления, если чек пересёк порог лимита."""
    warn_line = budget * WARN_RATIO
    if before < budget <= after:
        return ("Месячный лимит исчерпан",
                f"Потрачено {after:.2f} Br из {budget:.0f} Br")
    if before < warn_line <= after:
        pct = int(after / budget * 100) if budget else 0
        return ("Приближение к месячному лимиту",
                f"Потрачено {pct}% лимита ({after:.2f} Br из {budget:.0f} Br)")
    return None


def _send_expo_push(token: str, title: str, body: str) -> None:
    payload = json.dumps({
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
    }).encode()
    req = urllib.request.Request(
        EXPO_PUSH_URL, data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        # тело ответа читаем обязательно: Expo возвращает статус доставки
        # конкретному токену («ok» / DeviceNotRegistered / invalid …)
        reply = resp.read().decode("utf-8", "replace")
        log.info("expo push response %s: %s", resp.status, reply[:300])


def check_and_notify(user_id: int, added_amount: float) -> None:
    """Проверяет лимит после сохранения чека на added_amount и шлёт push.

    Уровневая логика с хранением состояния: предупреждение (80%) и алерт
    (лимит) отправляются один раз за месяц каждый. Это чинит два случая:
    1) лимит уже превышен до сохранения — алерт всё равно придёт при следующем
       чеке, а не «молчит», как логика «пересечения порога»;
    2) сервер перезапускался — состояние живёт в БД, а не в памяти.
    """
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None or not user.notifications_enabled or not user.push_token:
            return
        budget = float(user.monthly_budget or 0)
        if budget <= 0:
            return
        after = _month_total_confirmed(db, user_id)

        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        if user.push_month != month_key:
            user.push_month = month_key
            user.push_level = 0
            db.commit()

        warn_line = budget * WARN_RATIO
        if after >= budget:
            level = 2
            event = ("Месячный лимит исчерпан",
                     f"Потрачено {after:.2f} Br из {budget:.0f} Br")
        elif after >= warn_line:
            pct = int(after / budget * 100) if budget else 0
            level = 1
            event = ("Приближение к месячному лимиту",
                     f"Потрачено {pct}% лимита ({after:.2f} Br из {budget:.0f} Br)")
        else:
            return
        if level <= (user.push_level or 0):
            return  # этот уровень уже озвучивали в этом месяце
        try:
            _send_expo_push(user.push_token, event[0], event[1])
            user.push_level = level
            db.commit()
            log.info("push sent to user %s: %s", user_id, event[0])
        except Exception:
            log.exception("push delivery failed for user %s", user_id)
    finally:
        db.close()


def notify_async(user_id: int, added_amount: float) -> None:
    """Запускает проверку лимита в фоне (не блокирует ответ API)."""
    import threading

    threading.Thread(
        target=check_and_notify, args=(user_id, added_amount), daemon=True,
    ).start()
