"""Правила категоризации расходов."""
from __future__ import annotations

import re

RULES: list[tuple[str, list[str]]] = [
    ("Продукты", [
        "евроопт", "доброном", "санта", "копеечка", "виталюр", "гиппо",
        "продукты", "супермаркет", "гастроном",
        "молоко", "хлеб", "сыр", "колбаса", "масло", "яйц", "сахар", "мука",
        "hofer", "billa", "spar", "пятерочка", "магнит", "лента", "перекресток",
    ]),
    ("Кафе и рестораны", [
        "кафе", "ресторан", "столовая", "пицца", "суши", "бар", "кофе",
        "бургер", "шаурма", "додо", "хот-дог", "харчэўня", "харчовня",
        "карчэўня", "berghotel",
    ]),
    ("Транспорт", [
        "азс", "заправка", "автобус", "метро", "такси", "парковк",
        "белнефтехим", "газпромнефть",
        "трамвай", "электротранспорт", "проезд", "билет", "tankstelle",
        "tankstel", "diesel", "бензин",
    ]),
    ("Аптека", ["аптека", "лекарств", "таблетк", "витамин"]),
    ("Одежда и обувь", [
        "одежда", "обувь", "секонд", "reserved", "zara", "белвест",
    ]),
    ("Связь и интернет", ["мтс", "а1", "life:)", "интернет", "телефон", "связь"]),
    ("Товары для дома", [
        "хозтовар", "дом", "стройматериал", "обои", "мебель", "посуда",
        "fressnapf", "зоомагазин",
    ]),
    ("Электроника", ["dns", "ситилинк", "эльдорадо", "технопарк", "o'data"]),
    ("Развлечения", ["кино", "театр", "билет", "игр", "клуб", "боулинг"]),
]

FALLBACK_CATEGORY = "Прочее"

# короткие ключевые слова ищем только как отдельный токен, иначе «spar»
# срабатывает на «sparen», «a100» на артефактах футера, «бар» на «Bar Euro»
_TOKEN_RE = re.compile(r"[a-zа-яё0-9]+")
MIN_SUBSTRING_LEN = 6


def _matches(keyword: str, raw: str, compact: str) -> bool:
    if len(keyword) >= MIN_SUBSTRING_LEN:
        return keyword in raw or keyword in compact  # OCR рвёт слова: «Tankstel le»
    return any(keyword == tok for tok in _TOKEN_RE.findall(raw))


def _classify(text: str | None) -> str | None:
    if not text:
        return None
    raw = text.lower()
    compact = raw.replace(" ", "")
    for category, keywords in RULES:
        if any(_matches(kw, raw, compact) for kw in keywords):
            return category
    return None


def categorize(text: str, shop_name: str | None = None) -> str:
    # сначала магазин — он надёжнее текста чека
    # («Bar Euro» на чеке зоомагазина не должен давать «Кафе и рестораны»)
    shop_hit = _classify(shop_name)
    if shop_hit:
        return shop_hit
    return _classify(text) or FALLBACK_CATEGORY
