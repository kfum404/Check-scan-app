// Регистрация Expo push-токена: разрешения → токен → на сервер.
// Вызывается один раз после входа/загрузки профиля; ошибки глотаем —
// уведомления — необязательная фича, ломать вход из-за них нельзя.
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

import { usersApi } from "../api";

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
    if (status !== "granted") return;

    const token = (await Notifications.getExpoPushTokenAsync({
      projectId: "34bdc520-4486-4439-9090-8f74f6e0f5fd",
    })).data;
    if (!token) return;

    await usersApi.patch({ push_token: token });
  } catch {
    // нет сети / нет поддержки push — молча пропускаем
  }
}
