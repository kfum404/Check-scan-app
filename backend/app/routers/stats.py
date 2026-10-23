from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Receipt, User
from ..schemas import StatsEntry, WeeklyStatsResponse
from ..security import get_current_user

router = APIRouter(prefix="/stats", tags=["stats"])

DAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_LABELS = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]


def _confirmed(user_id: int):
    return select(Receipt).where(
        Receipt.user_id == user_id, Receipt.status == "confirmed"
    )


def _aggregate(rows) -> dict:
    by_category: dict[str, float] = {}
    amounts = []
    for r in rows:
        amounts.append(float(r.total_amount))
        by_category[r.category] = by_category.get(r.category, 0.0) + float(r.total_amount)
    total = round(sum(amounts), 2)
    count = len(amounts)
    return {
        "total": total,
        "count": count,
        "avg": round(total / count, 2) if count else 0.0,
        "max": round(max(amounts), 2) if amounts else 0.0,
        "by_category": [StatsEntry(label=k, amount=round(v, 2))
                        for k, v in sorted(by_category.items(),
                                           key=lambda kv: kv[1], reverse=True)],
    }


@router.get("/weekly", response_model=WeeklyStatsResponse)
def weekly_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Суммы по дням текущей недели и по категориям — экран Статистика."""
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # агрегируем в Python вместо date_trunc — так работает и на Postgres, и на SQLite (тесты)
    rows = db.scalars(
        select(Receipt).where(
            Receipt.user_id == user.id,
            Receipt.status == "confirmed",
            Receipt.date >= week_start,
        )
    ).all()

    by_day = {i: 0.0 for i in range(7)}
    by_category: dict[str, float] = {}
    for r in rows:
        idx = r.date.weekday()
        amount = float(r.total_amount)
        by_day[idx] += amount
        by_category[r.category] = by_category.get(r.category, 0.0) + amount

    return WeeklyStatsResponse(
        by_day=[StatsEntry(label=DAY_LABELS[i], amount=round(by_day[i], 2))
                for i in range(7)],
        by_category=[StatsEntry(label=k, amount=round(v, 2))
                     for k, v in sorted(by_category.items(),
                                        key=lambda kv: kv[1], reverse=True)],
    )


@router.get("/home")
def home_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Виджеты экрана Главная: потрачено сегодня/за месяц, лимит, категории."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0,
                              tzinfo=None)

    month_rows = db.scalars(
        select(Receipt).where(
            Receipt.user_id == user.id,
            Receipt.status == "confirmed",
            Receipt.date >= month_start,
        )
    ).all()
    today_rows = [r for r in month_rows if r.date >= day_start]

    agg_today = _aggregate(today_rows)
    month_total = round(sum(float(r.total_amount) for r in month_rows), 2)
    budget = float(user.monthly_budget or 5000)

    return {
        "today_spent": agg_today["total"],
        "month_spent": month_total,
        "month_limit": budget,
        "limit_used_pct": round(month_total / budget * 100) if budget else 0,
        "receipts_today": agg_today["count"],
        "avg_receipt_today": agg_today["avg"],
        "categories_today": len({r.category for r in today_rows}),
        "by_category_today": [e.model_dump() for e in agg_today["by_category"]],
    }


@router.get("/summary")
def summary_stats(
    period: str = Query("week", pattern="^(week|month|all)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Экран Статистика: итоги, график динамики и структура за период."""
    now = datetime.now(timezone.utc)
    stmt = _confirmed(user.id)
    if period == "week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        stmt = stmt.where(Receipt.date >= start)
    elif period == "month":
        stmt = stmt.where(Receipt.date >= now.replace(day=1, hour=0, minute=0,
                                                      second=0, microsecond=0,
                                                      tzinfo=None))
    rows = db.scalars(stmt).all()

    agg = _aggregate(rows)

    # динамика: неделя — по дням Пн..Вс; месяц — по неделям; всё — по месяцам
    by_day: list[StatsEntry] = []
    if period == "week":
        acc = {i: 0.0 for i in range(7)}
        for r in rows:
            acc[r.date.weekday()] += float(r.total_amount)
        by_day = [StatsEntry(label=DAY_LABELS[i], amount=round(acc[i], 2))
                  for i in range(7)]
    elif period == "month":
        acc: dict[int, float] = {}
        for r in rows:
            week_no = min((r.date.day - 1) // 7 + 1, 5)
            acc[week_no] = acc.get(week_no, 0.0) + float(r.total_amount)
        by_day = [StatsEntry(label=f"Нед {w}", amount=round(acc[w], 2))
                  for w in sorted(acc)]
    else:
        acc: dict[int, float] = {}
        for r in rows:
            acc[r.date.month] = acc.get(r.date.month, 0.0) + float(r.total_amount)
        by_day = [StatsEntry(label=MONTH_LABELS[m - 1], amount=round(acc[m], 2))
                  for m in sorted(acc)]

    return {"period": period, "by_day": [e.model_dump() for e in by_day], **agg}
