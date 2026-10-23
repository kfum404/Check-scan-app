# Контракт API «ЧекСкан»

Базовый URL (prod): `https://checkscan-api.onrender.com` (подставить фактический).
Все запросы, кроме `/auth/*`, требуют заголовок `Authorization: Bearer <JWT>`.

## Единый формат ошибки

```json
{ "detail": { "code": "OCR_LOW_CONFIDENCE", "message": "Не удалось уверенно распознать сумму", "fields": ["total_amount"] } }
```

| Код | HTTP | Когда |
|---|---|---|
| `UNAUTHORIZED` | 401 | нет/протухший токен |
| `BAD_CREDENTIALS` | 401 | неверный email/пароль |
| `EMAIL_TAKEN` | 409 | email уже зарегистрирован |
| `RECEIPT_NOT_FOUND` | 404 | чек не найден или чужой |
| `FILE_TOO_LARGE` | 413 | фото > 10 МБ |
| `BAD_IMAGE` | 422 | файл не декодируется как изображение |

## Эндпоинты

### Auth
- `POST /auth/register` — `{email, password, name?}` → `{token, user}`
- `POST /auth/login` — `{email, password}` → `{token, user}`
- `GET /auth/me` → `User`

### Чеки
- `POST /receipts/scan` — `multipart/form-data`, поле `file` (JPEG/PNG).
  Возвращает черновик `status="draft"` + `low_confidence_fields` — поля для
  подсветки на экране корректировки («карандаш»).
- `PATCH /receipts/{id}` — подтверждение после правки:
  `{shop_name, date, total_amount, category?, items?}` → `status="confirmed"`.
- `GET /receipts?page=1&size=20&status=confirmed` — история с пагинацией.
- `GET /receipts/{id}` — детали + позиции (bottom sheet истории).

### Главная и статистика
- `GET /receipts/summary/home` → `{balance, month_spent, receipts[5]}`.
  > Решить командой семантику `balance`: сейчас = потрачено за месяц.
  > Если на макете это «остаток бюджета», добавить поле `monthly_budget` в `users`.
- `GET /stats/weekly` → `{by_day: [{label: "Пн"…"Вс", amount}], by_category: [...]}`

### Профиль
- `PATCH /users/me` — `{notifications_enabled?, biometrics_enabled?, theme_preference?}`

## Статус-модель чека

`draft` (распознан, ждёт подтверждения) → `confirmed` (в истории и аналитике).
История и статистика по умолчанию показывают только `confirmed`.
