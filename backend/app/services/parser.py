"""Извлечение структурированных данных из сырого текста OCR.

Стратегия: чеки ритейлеров имеют повторяющуюся структуру — ищем паттернами
сумму/дату/магазин и возвращаем всех кандидатов с «уверенностью», чтобы API
мог отметить низкоуверенные поля для экрана корректировки.

Эвристика суммы (проверена на 9 реальных чеках, docs/OCR_ACCURACY.md):
последняя «помеченная» сумма (строка с ИТОГО/SUMME/TOTAL и т.п.) — это итог;
строки про НДС/VAT/MwSt исключаются. Если помеченных нет — максимум
из всех правдоподобных кандидатов.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

# строка с пометкой итога: ИТОГО/ВСЕГО/СУММА/TOTAL/SUMME/GESAMT/К ОПЛАТЕ
TOTAL_LABEL = re.compile(r"(?i)(итог|всего|сумма|total|summe|gesamt|к\s*оплате)")
# строки-процентки/НДС: сумма из них не является итогом («%» ловит «СУММА НДС 20%=699.83»)
TOTAL_TRAP = re.compile(r"(?i)(vat|mwst|ндс|налог|в\s*т\.?\s*ч|в том числе|includes|%)")
# сумма вида 4199.00 / 4 199,00 / 34, 09 (пробел после разделителя — артефакт OCR)
AMOUNT = r"(\d[\d ]{0,5}[.,]\s?\d{2})"
# сумма с валютой без метки итога
CURRENCY_SUFFIX = r"(?i:byn|br|руб|р\.|eur|euro|chf|снф)"

DATE_PATTERNS = [
    r"\b(\d{2}[.,/-]\s?\d{2}[.,/-]\s?\d{2,4})[\s/]*(\d{1,2}:\d{2})?\b",
    r"\b(\d{4}[.,/-]\d{2}[.,/-]\d{2})[\s/T]*(\d{1,2}:\d{2})?\b",
]
# строки-выбросы, которые не бывают названием магазина
SHOP_BLACKLIST = re.compile(
    r"(?i)(чек|касс|смена|приход|покупка|итог|сумма|наличные|карта|сдача|сайт|www|"
    r"область|обл\.|район|адрес|тел|факс|e-?mail)"
)
# адресные строки в шапке (город, улица) — пропускаем, магазин обычно ООО «…»
ADDRESS_LINE = re.compile(r"(?i)^\s*(г\.?|город|ул\.?|пр-кт|пр\.?|дом|кв\.?)\s")

DATE_FORMATS = (
    "%d.%m.%Y %H:%M", "%d.%m.%Y", "%d.%m.%y %H:%M", "%d.%m.%y",
    "%d/%m/%Y", "%d-%m-%Y",
    "%Y-%m-%d %H:%M", "%Y-%m-%d",
)


@dataclass
class ParsedReceipt:
    shop_name: str | None = None
    date: datetime | None = None
    total: float | None = None
    currency: str = "BYN"
    candidates_total: list[float] = field(default_factory=list)
    confidence: float = 0.0  # 0..1, доля успешно извлечённых полей


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def _plausible(value: float | None) -> bool:
    return value is not None and 0.1 <= value <= 10_000


def extract_total(text: str) -> tuple[float | None, list[float]]:
    labeled: list[float] = []
    candidates: list[float] = []

    for line in text.splitlines():
        amounts = [_to_float(m) for m in re.findall(AMOUNT, line)]
        amounts = [a for a in amounts if _plausible(a)]
        if not amounts:
            continue
        if TOTAL_LABEL.search(line) and not TOTAL_TRAP.search(line):
            labeled.extend(amounts)
        elif re.search(AMOUNT + r"\s*" + CURRENCY_SUFFIX, line):
            candidates.extend(amounts)

    if labeled:
        # итог — последняя помеченная сумма (после скидок/пересчётов),
        # кроме ловушек типа «TOTAL INCLUDES VAT»
        return labeled[-1], labeled + candidates
    if candidates:
        # запасной вариант: максимальная сумма с валютой
        return max(candidates), candidates
    return None, []


def extract_date(text: str) -> datetime | None:
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if not m:
            continue
        date_part = re.sub(r"\s", "", m.group(1)).replace(",", ".")
        time_part = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        # если время битое (28:16) — берём только дату
        for raw in filter(None, [f"{date_part} {time_part}" if time_part else None,
                                 date_part]):
            for fmt in DATE_FORMATS:
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue
    return None


def extract_shop(text: str) -> str | None:
    for line in (l.strip() for l in text.splitlines()):
        if len(line) < 4 or len(line) > 60:
            continue
        if SHOP_BLACKLIST.search(line) or ADDRESS_LINE.match(line):
            continue
        # магазин обычно в шапке — первая подходящая строка; без .title(),
        # чтобы «ООО» не превращалось в «Ооо»
        return line
    return None


def parse_receipt_text(text: str) -> ParsedReceipt:
    total, candidates = extract_total(text)
    date = extract_date(text)
    shop = extract_shop(text)

    filled = sum(v is not None for v in (total, date, shop))
    return ParsedReceipt(
        shop_name=shop,
        date=date,
        total=total,
        candidates_total=candidates,
        confidence=round(filled / 3, 2),
    )
