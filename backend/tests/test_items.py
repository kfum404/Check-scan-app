from app.services.ocr import extract_items


def test_classic_numbered_item():
    assert extract_items("1. ХЛЕБ РЖАНОЙ              2.45") == [("ХЛЕБ РЖАНОЙ", 2.45)]


def test_qty_column_item():
    assert extract_items("ШАМПУНЬ FRUCTIS КОКОСОВЫЙ 16.59 x1.000 16.59") == [
        ("ШАМПУНЬ FRUCTIS КОКОСОВЫЙ", 16.59)]


def test_code_and_multiply_item():
    assert extract_items("2740 ШОКОЛАДНЫЙ БА 1.000×49.90 49.90") == [
        ("ШОКОЛАДНЫЙ БА", 49.90)]


def test_vat_block_lines_are_not_items():
    """Строки «в том числе НДС…» не должны попадать в позиции ни как имя, ни как цена."""
    text = (
        "Конфета Птичка в молк шок 40г 46010410114121\n"
        "в том числе НДС за 1 единицу. НДС 20%            1.91 1.000 1.91 0.22\n"
        "Чипсы Лэйс со вкус краба 140гр 4690388111274\n"
        "в том числе НДС за 1 единицу. НДС 20%   6.40 X1.000   6.40 1.07\n"
        "ИТОГО                                    30.64\n"
        "ИТОГО НДС                                5.07\n"
        "НАЛИЧНЫМИ                               105.20\n"
        "Сдача                                    50.05"
    )
    assert extract_items(text) == [
        ("Конфета Птичка в молк шок 40г", 1.91),
        ("Чипсы Лэйс со вкус краба 140гр", 6.40),
    ]


def test_total_like_lines_are_not_items():
    for line in ("ИТОГО 40.90", "ИТОГО К ОПЛАТЕ 18.80", "НАЛИЧНЫМИ 105.20",
                 "Сдача 50.05", "4640017891109 4.20 x1.000 4.20"):
        assert extract_items(line) == [], line


def test_potato_is_not_blacklisted_by_karta():
    """«КАРТОФЕЛЬ» не должен отсекаться правилом про банковскую карту."""
    assert extract_items("КАРТОФЕЛЬ СВЕЖИЙ             2.00") == [("КАРТОФЕЛЬ СВЕЖИЙ", 2.00)]


def test_discount_lines_are_not_items():
    """Скидки/купоны и отрицательные суммы — не позиции чека."""
    text = (
        "Шампунь баланс укрепляющий для волос, 500мл\n"
        "4607034474105\n"
        "8.19 x1.000 8.19\n"
        "Скидка -2.00\n"
        "Маска GLAMMY восстановление с\n"
        "кератином, 500 мл\n"
        "4811248013457\n"
        "16.99 x1.000 16.99\n"
        "Скидка -3.00\n"
        "ИТОГО 30.56"
    )
    items = extract_items(text)
    assert ("Скидка", 2.00) not in items
    assert ("Скидка -", 2.00) not in items
    assert all("скидк" not in name.lower() for name, _ in items)
    # позиции присутствуют, скидки не портят ни цены, ни имена
    assert len(items) == 2


def test_multiline_item_name_is_joined():
    """Название, разорванное OCR на две строки, склеивается."""
    text = (
        "Маска GLAMMY восстановление и укрепление с\n"
        "кератином, 500 мл\n"
        "4811248013457\n"
        "16.99 x1.000 16.99"
    )
    items = extract_items(text)
    assert items == [("Маска GLAMMY восстановление и укрепление с кератином, 500 мл", 16.99)]
