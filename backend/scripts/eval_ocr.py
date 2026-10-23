"""Офлайн-прогон OCR-пайплайна проекта на реальных фото чеков.

Использует боевые модули app.services: ocr -> parser -> categorize.
Полезно для снятия метрик точности на командном датасете (см. docs/OCR_ACCURACY.md).

Запуск (из папки backend):
    pip install -r requirements.txt
    python scripts/eval_ocr.py <папка_с_чеками> [results.json]

Tesseract должен быть в PATH. Для Windows-портативной установки укажите путь:
    set TESSERACT_CMD=C:\path\to\tesseract.exe
    set TESSDATA_PREFIX=C:\path\to\tessdata
"""
import json
import os
import sys
import time

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIPTS = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "eval_results.json"

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
sys.path.insert(0, BACKEND)

import pytesseract  # noqa: E402

if os.environ.get("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]

from app.services import categorize, ocr, parser  # noqa: E402

results = []
for name in sorted(os.listdir(RECEIPTS)):
    path = os.path.join(RECEIPTS, name)
    if not name.lower().endswith((".jpg", ".jpeg", ".png")) or os.path.getsize(path) < 10000:
        continue
    with open(path, "rb") as f:
        content = f.read()
    t0 = time.time()
    try:
        text, conf, angle, variant = ocr.image_to_text_auto(content, lang="rus+eng", psm=6)
        parsed = parser.parse_receipt_text(text)
        category = categorize.categorize(text, parsed.shop_name)
        items = ocr.extract_items(text)
        error = None
    except Exception as e:  # noqa: BLE001 - отчёт по каждому чеку, не падаем целиком
        text, conf, angle, variant, category, items = "", 0.0, 0, "-", None, []
        parsed = parser.ParsedReceipt()
        error = str(e)
    results.append({
        "file": name,
        "ocr_confidence_tesseract": conf,
        "rotation_applied": angle,
        "preprocess_variant": variant,
        "parsed": {
            "shop_name": parsed.shop_name,
            "date": parsed.date.isoformat() if parsed.date else None,
            "total": parsed.total,
            "candidates": parsed.candidates_total,
            "parser_confidence": parsed.confidence,
        },
        "category": category,
        "items_extracted": len(items),
        "seconds": round(time.time() - t0, 1),
        "error": error,
        "text_head": text[:600],
    })
    print(f"[{name}] conf={conf} rot={angle} var={variant} "
          f"total={parsed.total} date={parsed.date} shop={parsed.shop_name} "
          f"cat={category} items={len(items)} ({time.time()-t0:.1f}s)")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nSaved:", OUT)
