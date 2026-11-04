# ЧекСкан — мобильное приложение для учёта расходов по чекам

Пользователь фотографирует чек → сервер распознаёт сумму, дату, магазин и
позиции (Tesseract OCR) → данные сохраняются в PostgreSQL → клиент показывает
историю, аналитику, категории расходов и месячный бюджет.

**Стек:** React Native (Expo SDK 52) · FastAPI · PostgreSQL · Tesseract OCR ·
OpenCV · Expo Push (FCM) · Google Sign-In

## Функции

- Регистрация/вход: логин-пароль (JWT) и **Google Sign-In (OAuth)**.
- Сканирование чека камерой или из галереи; OCR на сервере.
- Распознавание: итоговая сумма, дата, магазин, позиции (без скидок и купонов).
- История чеков с деталями позиций; ручное исправление данных.
- Аналитика и категоризация расходов (правила по ключевым словам).
- Месячный бюджет: редактируемый лимит, **push-уведомления** при 80% и 100%.
- Экспорт истории в **CSV во внешнюю FS** (папка Downloads через SAF).
- Кэширование истории на устройстве; данные восстанавливаются из облака
  при входе на другом устройстве.

## Структура репозитория

```
backend/    FastAPI + OCR + БД: app/{routers,models,services,db},
            tests/, tessdata/, Dockerfile, docker-compose.yml, render.yaml
mobile/     React Native клиент (Expo): src/{screens,components,api,
            notifications}, app.json, eas.json, credentials/ (demo-keystore)
docs/       API-контракт (docs/API.md), метрики OCR (OCR_ACCURACY.md),
            пакет к защите (DEFENSE.md), тексты Issues (ISSUES.md)
design/     Исходные макеты экранов (Figma-экспорт)
```

## Бэкенд: запуск

```bash
cd backend
cp .env.example .env          # заполнить под себя
docker compose up --build     # API на :8000, Postgres на :5432
```

Без Docker: установить Tesseract (+ язык `rus`), `pip install -r requirements.txt`,
поднять Postgres и указать `DATABASE_URL` в `.env`.

Swagger-документация: `http://localhost:8000/docs`.

### Переменные окружения (backend/.env)

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | подключение к PostgreSQL |
| `JWT_SECRET` / `JWT_EXPIRES_MINUTES` | подпись и срок токенов |
| `UPLOAD_DIR` | каталог загруженных фото чеков |
| `TESSERACT_LANG` / `TESSERACT_PSM` | язык и режим страницы OCR |
| `GOOGLE_CLIENT_ID` | Web client ID Google Cloud (вход через Google) |

## Мобильный клиент

```bash
cd mobile
npm install
npx expo start                 # разработка (Expo Go / dev-client)
```

Сборка APK через EAS (профиль `apk` в `eas.json`, `credentialsSource: local` —
keystore лежит в `mobile/credentials/`, демо-пароль в `credentials.json`):

```bash
export EXPO_TOKEN=<токен>
npx eas build --platform android --profile apk
```

Адрес бэкенда задаётся через `EXPO_PUBLIC_API_URL` (в профиле сборки eas.json
уже указан боевой сервер `http://193.233.82.97:8000`).

## Тесты

```bash
cd backend
pytest tests/ -q      # 54 теста: парсер, категоризация, API, push
```

## Соответствие требованиям проекта

| Требование | Реализация |
|---|---|
| Авторизация через OAuth | Google Sign-In (`@react-native-google-signin/google-signin`) |
| Восстановление данных из облака | все данные на сервере, при входе с любого устройства |
| Работа с медиатекой | выбор чека из галереи, сохранение снимка |
| Push-уведомления | Expo Push + FCM: месячный лимит 80% / 100% |
| Кэширование во внутреннюю FS | кэш истории на устройстве |
| Внешняя FS (Downloads) | экспорт CSV через Storage Access Framework |
| Камера | съёмка чека (`expo-camera`), fallback на системную камеру |
| «Сложный» сервер | FastAPI + OCR-пайплайн + PostgreSQL + push-диспетчер |

## Дорожная карта

| Этап | Содержание | Статус |
|---|---|---|
| M1 | Backend-core: каркас, модели, JWT | ✅ |
| M2 | OCR: предобработка, парсер, категоризация, метрики | ✅ сумма ~86% (docs/OCR_ACCURACY.md) |
| M3 | API: чеки, статистика, профиль, push | ✅ контракт в docs/API.md |
| M4 | Mobile: экраны по макетам, камера, push, OAuth, экспорт CSV | ✅ |
| M5 | Деплой: VPS (Ubuntu + Docker), сборка APK через EAS | ✅ сервер 193.233.82.97, APK v16 |
| M6 | Тестирование, защита | ✅ пакет к защите в docs/DEFENSE.md |

Задачи разбиты на GitHub Issues (тексты для создания — в `docs/ISSUES.md`).

## Команда и Git-процесс

- `main` защищён: только PR после review второго участника.
- Ветки: `feat/<номер-issue>-<кратко>`, например `feat/4-ocr-pipeline`.
- PR до ~300 строк: «что / почему / как проверить».
