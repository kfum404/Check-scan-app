// Регистрация Expo push-токена: разрешения → токен → на сервер.
// Статус регистрации доступен для отладки: getPushStatus() (показываем в Профиле).
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

import { usersApi } from "../api";

let lastStatus = "ещё не запрашивалось";

export function getPushStatus(): string {
  return lastStatus;
}

// Показывать push даже когда приложение открыто: без обработчика Expo
// доставляет уведомление только слушателям, и оно «молча» не появляется
// в шторке (пользователь думает, что push не пришёл).
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerPushToken(): Promise<void> {
  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "Бюджет",
        importance: Notifications.AndroidImportance.HIGH,
      });
    }
    const { status: existing } = await Notifications.getPermissionsAsync();
    let status = existing;
    if (existing !== "granted") {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== "granted") {
      lastStatus = "нет разрешения на уведомления";
      return;
    }

    const token = (await Notifications.getExpoPushTokenAsync({
      projectId: "34bdc520-4486-4439-9090-8f74f6e0f5fd",
    })).data;
    if (!token) {
      lastStatus = "токен пустой";
      return;
    }

    await usersApi.patch({ push_token: token });
    lastStatus = `токен зарегистрирован (${token.slice(7, 19)}…)`;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    lastStatus = `ошибка: ${msg.slice(0, 90)}`;
  }
}
