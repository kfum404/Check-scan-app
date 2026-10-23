from app.services.parser import extract_date, extract_shop, extract_total, parse_receipt_text

SAMPLE = """ООО "Евроопт"
г. Минск, ул. Победы, 7
Чек № 001234   Касса 2   Смена 12
23.10.2026 14:32
1. ХЛЕБ РЖАНОЙ              2.45
2. МОЛОКО 3.2%             3.10
3. СЫР РОССИЙСКИЙ          5.60
ИТОГО:                     11.15
Наличные                  20.00
Сдача                      8.85
Спасибо за покупку!
"""


def test_extract_total_prefers_labeled_line():
    total, candidates = extract_total(SAMPLE)
    assert total == 11.15
    # «Наличные 20.00» и «Сдача 8.85» — не кандидаты: нет ни метки итога, ни валюты
    assert 20.00 not in candidates and 8.85 not in candidates


def test_extract_total_returns_none_on_garbage():
    assert extract_total("abcdefghijklmnopqrstuvwxyz")[0] is None


def test_extract_date():
    d = extract_date(SAMPLE)
    assert d is not None and d.day == 23 and d.month == 10 and d.year == 2026
    assert d.hour == 14 and d.minute == 32


def test_extract_shop_skips_service_lines():
    shop = extract_shop(SAMPLE)
    assert shop is not None
    assert "Евроопт" in shop


def test_extract_shop_skips_address_lines():
    """Город/улица в шапке — не магазин (билет Электротранспорта)."""
    text = "г. Набережные Челны\nООО Электротранспорт\n29.10.2019"
    assert extract_shop(text) == "ООО Электротранспорт"


def test_parse_receipt_confidence():
    parsed = parse_receipt_text(SAMPLE)
    assert parsed.confidence == 1.0
    assert parsed.total == 11.15


def test_parse_receipt_partial_text():
    parsed = parse_receipt_text("ИТОГО: 5.00")
    assert parsed.total == 5.00
    assert parsed.confidence < 1.0  # магазин и дата не найдены — клиент подсветит поля


def test_vat_line_is_not_total():
    """TOTAL INCLUDES VAT — ловушка: НДС не является итогом."""
    text = "CHIN H. MEEN & SON'S LTD\nTOTAL 19.50\nTOTAL INCLUDES VAT OF : 1.77\nCash 20.00"
    total, _ = extract_total(text)
    assert total == 19.50


def test_last_labeled_wins_after_discount():
    """После скидки итог — последняя помеченная сумма (Fressnapf: 34,97 → 34,09)."""
    text = "Summe [ 3] EUR 34,97\nMwSt.-Senkung -0,88\nSumme EUR 34,09\nBar Euro EUR 50,09"
    total, _ = extract_total(text)
    assert total == 34.09


def test_amount_with_space_after_separator():
    total, _ = extract_total("Summe EUR 34, 09")
    assert total == 34.09


def test_date_variants():
    assert extract_date("30.07.2007/13:29:17") is not None  # "/" между датой и временем
    assert extract_date("30,07,2007") is not None           # запятые вместо точек
    assert extract_date("02.05.23 28:16") is not None       # битое время — берём дату
    assert extract_date("2020-12-04T09:36:54") is not None  # ISO с T
