from app.services.categorize import FALLBACK_CATEGORY, categorize


def test_shop_match():
    assert categorize("ХЛЕБ 2.45", "ООО Евроопт") == "Продукты"


def test_item_keyword_match():
    assert categorize("1. МОЛОКО 3.2% 3.10") == "Продукты"
    assert categorize("додо пицца") == "Кафе и рестораны"
    assert categorize("АЗС №12 бензин") == "Транспорт"


def test_fallback():
    assert categorize("ничего непонятного") == FALLBACK_CATEGORY


def test_keywords_from_real_receipts():
    """Словарь пополнен по результатам прогона на 9 реальных чеках."""
    assert categorize("", "HIT-Tankstel le") == "Транспорт"
    assert categorize("", "DNS 2350") == "Электроника"
    assert categorize("", "HOFER KG") == "Продукты"
    assert categorize("", "Fressnapf Köln") == "Товары для дома"
    assert categorize("ОПЛАТА ПРОЕЗДА ТРАМВАЙ", "ООО Электротранспорт") == "Транспорт"
