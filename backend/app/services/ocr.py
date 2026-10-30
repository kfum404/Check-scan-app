"""OCR-пайплайн: предобработка фото (OpenCV) → Tesseract → текст.

Импорты cv2/pytesseract ленивые: модуль должен импортироваться и в тестах,
и на машинах без Tesseract (например, CI без OCR).

image_to_text_auto — боевой вход: подбирает поворот (0/90/180/270) и выбирает
лучший из двух проходов (адаптивный порог / просто grayscale), что критично
для мятых чеков, снятых под углом (см. docs/OCR_ACCURACY.md).
"""
from __future__ import annotations

import io
import re

ROTATIONS = (0, 90, 180, 270)


def _decode(image_bytes: bytes) -> "object":  # -> numpy.ndarray
    import cv2
    import numpy as np

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Не удалось декодировать изображение")
    return img


def _preprocess_variants(img: "object") -> dict[str, "object"]:
    """Два варианта бинаризации: для чёткой печати хорош адаптивный порог,
    для бледной термобумаги он выжигает текст — тогда лучше просто grayscale."""
    import cv2

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    return {"thresh": thresh, "gray": gray}


def _bundled_tessdata() -> "str | None":
    """Папка с языковыми пакетами из репозитория (backend/tessdata).

    Пакеты из apt/системы отличаются по качеству распознавания — чтобы результат
    на любом сервере совпадал с замерами в docs/OCR_ACCURACY.md, используем
    зафиксированные tessdata_fast. Переопределить можно переменной TESSDATA_PREFIX.
    """
    from pathlib import Path

    d = Path(__file__).resolve().parent.parent.parent / "tessdata"
    return str(d) if (d / "rus.traineddata").exists() else None


def _configure_tesseract() -> None:
    """Путь к бинарнику (на Windows-разработке Tesseract не в PATH) + tessdata."""
    import os

    import pytesseract

    from ..config import settings

    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    bundled = _bundled_tessdata()
    if bundled and not os.environ.get("TESSDATA_PREFIX"):
        os.environ["TESSDATA_PREFIX"] = bundled


def _ocr(img: "object", lang: str, psm: int) -> tuple[str, float]:
    import pytesseract
    from PIL import Image

    _configure_tesseract()
    config = f"--psm {psm}"
    text = pytesseract.image_to_string(img, lang=lang, config=config)
    data = pytesseract.image_to_data(
        Image.fromarray(img), lang=lang, config=config,
        output_type=pytesseract.Output.DICT,
    )
    confs = [int(c) for c in data["conf"] if int(c) >= 0]
    avg = sum(confs) / len(confs) if confs else 0.0
    return text, round(avg, 2)


def _resize_max(img: "object", max_side: int = 700) -> "object":
    import cv2

    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1:
        return img
    return cv2.resize(img, (int(w * scale), int(h * scale)))


# rotate по часовой → константа cv2 (против часовой на тот же угол)
_CW_TO_CV2 = {0: None, 90: "ROTATE_90_COUNTERCLOCKWISE",
              180: "ROTATE_180", 270: "ROTATE_90_CLOCKWISE"}

# слова, которые почти всегда есть на чеке: верный поворот даёт больше совпадений
_ROTATION_KEYWORDS = re.compile(
    r"(?i)(итог|сумм|total|summe|gesamt|чек|оплат|касс|сдач|наличн|стоим)")


def _score_rotation(img: "object", lang: str, psm: int) -> tuple[int, int, float]:
    """Метрика выбора поворота: (совпадений ключевых слов, число уверенных
    слов ≥3 символов, средняя уверенность). Ключевые слова главнее — перевёрнутый
    текст Tesseract распознаёт «уверенно», но осмысленных слов чека в нём нет."""
    import pytesseract
    from PIL import Image

    _configure_tesseract()
    data = pytesseract.image_to_data(
        Image.fromarray(img), lang=lang, config=f"--psm {psm}",
        output_type=pytesseract.Output.DICT,
    )
    words = [t for t, c in zip(data["text"], data["conf"])
             if int(c) >= 60 and len(t.strip()) >= 3]
    allc = [int(c) for c in data["conf"] if int(c) >= 0]
    avg = sum(allc) / len(allc) if allc else 0.0
    kw = len(_ROTATION_KEYWORDS.findall(" ".join(words)))
    return kw, len(words), round(avg, 2)


def _apply_cw_rotation(img: "object", degrees_cw: int) -> "object":
    import cv2

    const = _CW_TO_CV2.get(degrees_cw)
    return img if const is None else cv2.rotate(img, getattr(cv2, const))


def image_to_text_auto(image_bytes: bytes, lang: str = "rus+eng",
                       psm: int = 6) -> tuple[str, float, int, str]:
    """Полный пайплайн: поворот (OSD + голосование) + выбор предобработки.

    Возвращает (текст, средняя уверенность 0..100, угол поворота по часовой, вариант).

    OSD Tesseract на чеках с криллицей/таблицами часто ошибается, поэтому его
    ответ не применяем напрямую: скорим всех кандидатов (OSD, победитель
    голосования, 0°/180°) по числу уверенных слов и берём лучшего.
    """
    img = _decode(image_bytes)
    # скорим повороты на уменьшенной копии: 700px мало — мелкий шрифт чека
    # перестаёт распознаваться и метрика вырождается
    thumb = _preprocess_variants(_resize_max(img, 1200))["gray"]

    # все 4 угла скорим на уменьшенной копии: метрика — ключевые слова чека,
    # затем уверенные слова; OSD не используем — на чеках с кириллицей он
    # регулярно выбирает неверный угол
    best_angle, best_key = 0, (-1, -1, -1.0)
    for angle in ROTATIONS:
        rot = thumb if angle == 0 else _apply_cw_rotation(thumb, angle)
        key = _score_rotation(rot, lang, psm)
        if key > best_key:
            best_angle, best_key = angle, key
    full = _apply_cw_rotation(img, best_angle)

    # полное распознавание двумя способами бинаризации
    best: tuple[str, float, str] = ("", -1.0, "thresh")
    for variant, processed in _preprocess_variants(full).items():
        text, conf = _ocr(processed, lang, psm)
        if conf > best[1]:
            best = (text, conf, variant)
    return best[0], best[1], best_angle, best[2]


def preprocess(image_bytes: bytes) -> "object":  # -> numpy.ndarray
    """Ч/б, адаптивный порог, лёгкое устранение шума (легаси-вход для тестов)."""
    return _preprocess_variants(_decode(image_bytes))["thresh"]


def image_to_text(image_bytes: bytes, lang: str = "rus+eng",
                  psm: int = 6) -> tuple[str, float]:
    """Возвращает (текст, средняя уверенность Tesseract 0..100)."""
    processed = preprocess(image_bytes)
    return _ocr(processed, lang, psm)


def extract_items(text: str) -> list[tuple[str, float]]:
    """Пытается вытащить позиции чека вида '1. ХЛЕБ РЖАНОЙ        2.45'."""
    import re

    items: list[tuple[str, float]] = []
    for line in text.splitlines():
        m = re.match(r"^\s*\d+\s*[.)]?\s*(.{3,60}?)\s+(\d{1,5}[.,]\d{2})\s*$", line)
        if m:
            name = m.group(1).strip()
            if not re.search(r"(?i)(итог|сумма|всего|наличн|карта|mwst|vat)", name):
                items.append((name, float(m.group(2).replace(",", "."))))
    return items
