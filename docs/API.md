# Контракт API «ЧекСкан»

Базовый URL (prod): `https://checkscan-api.onrender.com` (подставить фактический после деплоя).
Все запросы, кроме `/auth/register` и `/auth/login`, требуют заголовок `Authorization: Bearer <JWT>`.
Коды совпадают с реализацией в `mobile/src/api/` — при изменении контракта править обе стороны.

## Единый формат ошибки

```json
{ "detail": { "code": "RECEIPT_NOT_FOUND", "message": "Чек 42 не найден" } }
```

| Код | HTTP | Когда |
|---|---|---|
| `UNAUTHORIZED` | 401 | нет/протухший токен |
| `BAD_CREDENTIALS` | 401 | неверный email/пароль |
| `EMAIL_TAKEN` | 409 | email уже зарегистрирован |
| `RECEIPT_NOT_FOUND` | 404 | чек не найден или чужой |
| `FILE_TOO_LARGE` | 413 | фото больше 10 МБ |
| `BAD_IMAGE` | 422 | файл не декодируется как изображение |
| `422 VALIDATION` | 422 | невалидное тело (Pydantic, подробности в `detail`) |

Низкая уверенность OCR — **не ошибка**: сервер всегда возвращает черновик,
неуверенные поля перечислены в `low_confidence_fields` (см. ниже), клиент подсвечивает их
на экране корректировки.

## Auth

- `POST /auth/register` — `{email, password(6–128), name?}` → `201 {token, user}`
- `POST /auth/login` — `{email, password}` → `{token, user}`
- `GET /auth/me` → `User`

## Чеки

- `POST /receipts/scan` — `multipart/form-data`, поле `file` (JPEG/PNG, до 10 МБ).
  OCR (Tesseract, rus+eng, авто-поворот) → черновик `status="draft"`:
  ```json
  {
    "receipt": { "id": 12, "shop_name": "ДНС", "date": "...", "total_amount": 4199.0,
                 "currency": "RUB", "category": "Электроника", "status": "draft",
                 "items": [{"id": 1, "item_name": "...", "price": 100.0}],
                 "ocr_confidence": 91.5 },
    "low_confidence_fields": ["total_amount"]
  }
  ```
  Поля для подсветки: `total_amount` (сумма не найдена или уверенность < 65 %),
  `date` (дата не найдена), `shop_name` (магазин не найден).
- `PATCH /receipts/{id}` — подтверждение после правки:
  `{shop_name, date, total_amount(0–10 000), category?, items?}` → `ReceiptDetail`, `status="confirmed"`.
- `POST /receipts/manual` — ручной ввод без фото (кнопка «Заполнить вручную» на экране Камеры):
  то же тело, что у PATCH → `201`, сразу `status="confirmed"`.
- `GET /receipts?page=1&size=20&status=confirmed` — история с пагинацией
  → `{total, page, size, items: Receipt[]}` (сортировка по дате, новые первыми).
- `GET /receipts/{id}` — детали + позиции (bottom sheet истории).
- `DELETE /receipts/{id}` → `204`.

## Главная

- `GET /receipts/summary/home` → `{balance, month_spent, receipts[5]}`.
  Семантика: `balance` = потрачено за текущий месяц (как на макете главного экрана),
  `receipts` — 5 последних подтверждённых чеков.
- `GET /stats/home` → виджеты главного экрана:
  `{today_spent, month_spent, month_limit, limit_used_pct, receipts_today,
    avg_receipt_today, categories_today, by_category_today}`.
  `month_limit` = `users.monthly_budget` (по умолчанию 5000), `limit_used_pct` — процент использования.

## Статистика

- `GET /stats/summary?period=week|month|all` → экран Статистика:
  `{period, by_day: [{label, amount}], total, count, avg, max, by_category}`.
  Динамика: неделя — по дням «Пн»…«Вс», месяц — по неделям «Нед 1»…, всё — по месяцам «Янв»…
- `GET /stats/weekly` → `{by_day[7], by_category}` — суммы по дням текущей недели (альтернативный виджет).

## Профиль

- `PATCH /users/me` — `{name?, notifications_enabled?, autosave_enabled?,
  biometrics_enabled?, theme_preference?("light"|"dark"), monthly_budget?(>0)}` → `User`

`User`: `{id, name, email, notifications_enabled, autosave_enabled, biometrics_enabled,
theme_preference, monthly_budget}`.

## Статус-модель чека

`draft` (распознан, ждёт подтверждения на экране корректировки) → `confirmed` (история и аналитика).
История и статистика по умолчанию показывают только `confirmed`.
