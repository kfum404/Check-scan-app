# Мобильный клиент «ЧекСкан» (React Native / Expo)

## Почему Expo

- Камера (`expo-camera`), безопасное хранение токена (`expo-secure-store`),
  сборка APK через EAS Build без настройки Android SDK локально.
- Для диплома достаточно managed workflow; нативный код не понадобится.

## Создание проекта

```bash
npx create-expo-app@latest CheckScan --template blank-typescript
cd CheckScan
npx expo install expo-camera expo-secure-store @react-navigation/native \
  @react-navigation/bottom-tabs react-native-screens react-native-safe-area-context
npm install @tanstack/react-query victory-native axios
```

## Структура

```
src/
├── api/
│   ├── client.ts        # axios-инстанс: baseURL + Bearer-токен
│   ├── receipts.ts      # scanReceipt(formData), confirmReceipt, listReceipts…
│   └── types.ts         # типы 1:1 по docs/API.md (User, Receipt, ScanResult…)
├── screens/
│   ├── HomeScreen.tsx        # Главная.png
│   ├── CameraScreen.tsx      # Камера.png + экран корректировки
│   ├── StatsScreen.tsx       # Статистика.png
│   ├── HistoryScreen.tsx     # История.png (+ bottom sheet — Оверлей к истории.png)
│   └── ProfileScreen.tsx     # Профиль.png
├── components/          # ReceiptCard, CategoryBadge, WeekChart…
├── theme/               # дизайн-токены (цвета/типографика из Figma, light/dark)
└── hooks/               # useAuth, useReceipts (React Query: кэш + пулл-ту-рефреш)
```

## Ключевые фрагменты

### src/api/client.ts

```ts
import axios from "axios";
import * as SecureStore from "expo-secure-store";

export const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL, // https://checkscan-api.onrender.com
});

api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Единая обработка ошибок по контракту: err.response.data.detail.code
api.interceptors.response.use(
  (r) => r,
  (err) => Promise.reject(new ApiError(err.response?.data?.detail ?? err.message))
);

export class ApiError extends Error {
  constructor(public detail: { code: string; message: string; fields?: string[] }) {
    super(detail.message);
  }
}
```

### Загрузка фото чека

```ts
const form = new FormData();
form.append("file", {
  uri: photo.uri,
  name: "check.jpg",
  type: "image/jpeg",
} as unknown as Blob);
const { data } = await api.post<ScanResult>("/receipts/scan", form, {
  headers: { "Content-Type": "multipart/form-data" },
});
// data.low_confidence_fields — подсветить эти поля на экране корректировки
```

## Сборка APK

```bash
npm install -g eas-cli
eas login
eas build:configure          # создаёт eas.json
eas build --platform android --profile apk
# профиль apk в eas.json: { "buildType": "apk" } — без подписи Google Play,
# для защиты этого достаточно; ссылку на скачивание выдаст EAS
```

## Подключение к бэкенду локально

Эмулятор Android: `EXPO_PUBLIC_API_URL=http://10.0.2.2:8000`.
Физическое устройство: компьютер и телефон в одной Wi-Fi сети,
`EXPO_PUBLIC_API_URL=http://<IP-компьютера>:8000`.
