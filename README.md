# ЧекСкан — мобильное приложение для учёта расходов по чекам

Пользователь фотографирует чек → сервер распознаёт сумму, дату и магазин
(Tesseract OCR) → данные сохраняются в PostgreSQL → клиент показывает историю,
аналитику и категории расходов.

**Стек:** FastAPI · Tesseract OCR · OpenCV · PostgreSQL · React Native (Expo)

## Структура репозитория

```
backend/    FastAPI + OCR + БД (см. docs/API.md)
mobile/     React Native клиент (Expo)
docs/       API-контракт, метрики OCR, пакет к защите, тексты Issues
design/     Исходные макеты экранов (Figma-экспорт)
```

## Быстрый старт бэкенда

```bash
cd backend
cp .env.example .env          # заполнить под себя
docker compose up --build     # API на :8000, Postgres на :5432
```

Без Docker: установить Tesseract (+ lang `rus`), `pip install -r requirements.txt`,
поднять Postgres локально и указать `DATABASE_URL` в `.env`.

Swagger-документация: `http://localhost:8000/docs`.

## Тесты

```bash
cd backend
pytest tests/ -q
```

## Дорожная карта

| Этап | Содержание | Статус |
|---|---|---|
| M1 | Backend-core: каркас, модели, JWT | ✅ 25 тестов зелёные |
| M2 | OCR: предобработка, парсер, категоризация, метрики | ✅ сумма 86%, дата 71% (docs/OCR_ACCURACY.md) |
| M3 | API: чеки, статистика, профиль | ✅ контракт в docs/API.md |
| M4 | Mobile: 5 экранов по макетам | ✅ tsc без ошибок |
| M5 | Деплой Render + APK | 🟡 конфиги готовы (render.yaml, eas.json), нужны аккаунты Render/Expo |
| M6 | Тестирование, защита | 🟡 пакет к защите в docs/DEFENSE.md |

Задачи разбиты на GitHub Issues (тексты для создания — в `docs/ISSUES.md`).

## Команда и Git-процесс

- `main` защищён: только PR после review второго участника.
- Ветки: `feat/<номер-issue>-<кратко>`, например `feat/4-ocr-pipeline`.
- PR до ~300 строк: «что / почему / как проверить».
