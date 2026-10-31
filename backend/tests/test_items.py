from app.services.ocr import extract_items


def test_classic_numbered_item():
    assert extract_items("1. ХЛЕБ РЖАНОЙ              2.45") == [("ХЛЕБ РЖАНОЙ", 2.45)]


def test_qty_column_item():
    assert extract_items("ШАМПУНЬ FRUCTIS КОКОСОВЫЙ 16.59 x1.000 16.59") == [
        ("ШАМПУНЬ FRUCTIS КОКОСОВЫЙ", 16.59)]


def test_code_and_multiply_item():
    assert extract_items("2740 ШОКОЛАДНЫЙ БА 1.000×49.90 49.90") == [
        ("ШОКОЛАДНЫЙ БА", 49.90)]


def test_total_like_lines_are_not_items():
    for line in ("ИТОГО 40.90", "ИТОГО К ОПЛАТЕ 18.80", "НАЛИЧНЫМИ 105.20",
                 "Сдача 50.05", "4640017891109 4.20 x1.000 4.20"):
        assert extract_items(line) == [], line
