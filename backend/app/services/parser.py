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
    r"область|обл\.|район|адрес|тел|факс|e-?mail|унп|окпо|кассир|касса|"
    r"платежный документ|будьте здоровы)"
)
# адресные строки в шапке (город, улица) — пропускаем, магазин обычно ООО «…»
ADDRESS_LINE = re.compile(r"(?i)^\s*(г\.?|город|ул\.?|пр-кт|пр\.?|дом|кв\.?)\s")
# название в кавычках — самый надёжный признак: ООО «Евроопт», магазин "Оптика"
QUOTED_NAME = re.compile(r"[«\"']([А-Яа-яЁёA-Za-z0-9 .,&-]{2,40})[»\"']")
# юрлицо с названием: РУП «…», ООО «…», ИП …
LEGAL_FORM = re.compile(
    r"(?i)\b(руп|ооо|оао|зао|чтпуп|уп|ип|тд|тсц)\b[ «\"']*([А-Яа-яЁёA-Za-z0-9 .,&-]{2,40})"
)
# известные сети — распознаём даже без кавычек
CHAIN = re.compile(
    r"(?i)(евроопт|дикси|виталюр|гиппо|доброном|март|веста|корона|простор|"
    r"гастроном|универсам|цум|медтехника|оптика|косметик|миля|зелёный|"
    r"наёмник|монетка|пятёрочка|магнит|лента|ашан|кофе|бургер|kfc|mcdonald|"
    r"белмаркет|грин|санта|пеликан)"
)
# мусор OCR: короткие «клоки» заглавных без строчных и без цифр-кода —
# «ITT EE OOOO EE» — такое названием магазина не бывает
GARBAGE_CAPS = re.compile(r"^[A-ZА-ЯЁ]{1,3}(\s+[A-ZА-ЯЁ0-9]{1,5}){1,5}$")

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
    total_from_items: bool = False  # итог посчитан как сумма позиций (проверить вручную)


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def _plausible(value: float | None) -> bool:
    return value is not None and 0.1 <= value <= 10_000


def _amounts_in_line(line: str) -> list[float]:
    """Суммы в строке; числа, вклеенные в более длинные последовательности
    («207-699. 83», «1.000×49.90»), отсекаем — это мусор OCR, а не сумма."""
    out = []
    for m in re.finditer(AMOUNT, line):
        start, end = m.span()
        before = line[start - 1] if start > 0 else " "
        after = line[end] if end < len(line) else " "
        if before.isdigit() or before == "-" or after.isdigit():
            continue
        value = _to_float(m.group(1))
        if _plausible(value):
            out.append(value)
    return out


def extract_total(text: str) -> tuple[float | None, list[float]]:
    labeled: list[float] = []
    candidates: list[float] = []

    for line in text.splitlines():
        amounts = _amounts_in_line(line)
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
    lines = [l.strip() for l in text.splitlines()]

    def suitable(line: str) -> bool:
        return (4 <= len(line) <= 60
                and not SHOP_BLACKLIST.search(line)
                and not ADDRESS_LINE.match(line))

    # 1) название в кавычках — магазин «Оптика», ООО «Евроопт»: самый надёжный признак
    for line in lines[:8]:
        if not suitable(line):
            continue
        m = QUOTED_NAME.search(line)
        if m:
            name = m.group(1).strip(" .,-")
            if len(name) >= 2 and not GARBAGE_CAPS.match(name):
                return name
    # 2) юрлицо с названием: РУП «Медтехника» → «Медтехника»
    for line in lines[:8]:
        if not suitable(line):
            continue
        m = LEGAL_FORM.search(line)
        if m:
            name = m.group(2).strip(" .,-«»\"'")
            if len(name) >= 2 and not GARBAGE_CAPS.match(name):
                return name
    # 3) известная сеть прямым вхождением
    for line in lines[:8]:
        if not suitable(line):
            continue
        m = CHAIN.search(line)
        if m:
            return line
    # 4) запасной вариант — первая осмысленная строка шапки, но не мусор CAPS
    for line in lines:
        if not suitable(line):
            continue
        if GARBAGE_CAPS.match(line) and not CHAIN.search(line):
            continue
        return line
    return None


def _fallback_total_from_items(text: str) -> float | None:
    """Если помеченный итог не найден, складываем распознанные позиции —
    на большинстве чеков их сумма совпадает с итогом."""
    from .ocr import extract_items

    items = extract_items(text)
    if len(items) >= 2:
        return round(sum(price for _, price in items), 2)
    return None


def parse_receipt_text(text: str) -> ParsedReceipt:
    total, candidates = extract_total(text)
    total_from_items = False
    if total is None:
        total = _fallback_total_from_items(text)
        total_from_items = total is not None
    date = extract_date(text)
    shop = extract_shop(text)

    filled = sum(v is not None for v in (total, date, shop))
    return ParsedReceipt(
        shop_name=shop,
        date=date,
        total=total,
        candidates_total=candidates,
        confidence=round(filled / 3, 2),
        total_from_items=total_from_items,
    )
