// Экран входа / регистрации — email + пароль и вход через Google (Google Sign-In SDK).
import React, { useState } from "react";
import {
  KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TouchableOpacity, View,
} from "react-native";
import { GoogleSignin, statusCodes } from "@react-native-google-signin/google-signin";
import Constants from "expo-constants";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, ErrorText, Field } from "../components/ui";
import { useTheme } from "../theme";

// Web client ID (тип «Веб-приложение») — выступает аудиторией id_token.
// Личность приложения подтверждается Android-клиентом (пакет + SHA-1 подписи),
// личность пользователя — через нативный Google Sign-In SDK (без браузера).
const GOOGLE_WEB_CLIENT_ID: string =
  (Constants.expoConfig?.extra as any)?.googleClientId ?? "";

GoogleSignin.configure({
  webClientId: GOOGLE_WEB_CLIENT_ID || undefined,
  offlineAccess: false,
});

export default function LoginScreen() {
  const { colors } = useTheme();
  const { login, register, loginWithGoogle } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const submit = async () => {
    setError(undefined);
    if (!email.includes("@")) return setError("Введите корректный email");
    if (password.length < 6) return setError("Пароль — минимум 6 символов");
    setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name || undefined);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось войти");
    } finally {
      setLoading(false);
    }
  };

  const startGoogle = async () => {
    setError(undefined);
    if (!GOOGLE_WEB_CLIENT_ID) {
      setError("Google OAuth не настроен в приложении");
      return;
    }
    setGoogleLoading(true);
    try {
      await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
      let res: any;
      try {
        res = await GoogleSignin.signIn();
      } catch (se: any) {
        throw new Error("signIn: " + (se?.message ?? String(se)) + (se?.code ? ` (код ${se.code})` : ""));
      }
      const direct: string | undefined = res?.idToken ?? res?.data?.idToken;
      let idToken: string | undefined = direct;
      if (!idToken) {
        try {
          idToken = (await GoogleSignin.getTokens()).idToken;
        } catch (te: any) {
          throw new Error("getTokens: " + (te?.message ?? String(te)) + (te?.code ? ` (код ${te.code})` : ""));
        }
      }
      if (!idToken) {
        setError("Google не вернул id_token");
        return;
      }
      await loginWithGoogle(idToken);
    } catch (e: any) {
      if (e?.code === statusCodes.SIGN_IN_CANCELLED) {
        // пользователь закрыл окно — не ошибка
      } else if (e?.code === statusCodes.IN_PROGRESS) {
        // вход уже выполняется
      } else if (e?.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
        setError("Google Play Services недоступны на устройстве");
      } else if (e instanceof ApiError) {
        setError("Сервер: " + e.message);
      } else {
        setError("Google-вход: " + (e?.message ? String(e.message) : String(e)));
      }
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }}
                          behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={s.wrap} keyboardShouldPersistTaps="handled">
        <View style={[s.logo, { backgroundColor: colors.primarySoft }]}>
          <Text style={{ fontSize: 40 }}>🧾</Text>
        </View>
        <Text style={{ color: colors.text, fontSize: 26, fontWeight: "800", marginTop: 16 }}>
          ЧекСкан
        </Text>
        <Text style={{ color: colors.subtext, fontSize: 14, marginTop: 6, marginBottom: 28, textAlign: "center" }}>
          Сканируйте чеки — учёт расходов сам
        </Text>

        {mode === "register" && (
          <Field label="Имя" value={name} onChangeText={setName} placeholder="Саныч" autoCapitalize="words" />
        )}
        <Field label="Email" value={email} onChangeText={setEmail}
               placeholder="you@example.com" keyboardType="email-address" autoCapitalize="none" />
        <Field label="Пароль" value={password} onChangeText={setPassword}
               placeholder="минимум 6 символов" secureTextEntry />

        <ErrorText error={error} />
        <Button title={mode === "login" ? "Войти" : "Создать аккаунт"} onPress={submit} loading={loading} />

        <View style={{ flexDirection: "row", alignItems: "center", gap: 12, marginVertical: 16 }}>
          <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
          <Text style={{ color: colors.subtext, fontSize: 12 }}>или</Text>
          <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
        </View>

        <Button
          title="Войти через Google"
          variant="ghost"
          icon={<Text style={{ fontSize: 16, fontWeight: "800", color: colors.primary }}>G</Text>}
          onPress={() => void startGoogle()}
          loading={googleLoading}
        />

        <TouchableOpacity onPress={() => { setMode(mode === "login" ? "register" : "login"); setError(undefined); }}>
          <Text style={{ color: colors.primary, fontSize: 14, fontWeight: "600", marginTop: 20 }}>
            {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  wrap: { flexGrow: 1, justifyContent: "center", padding: 24, paddingBottom: 60, alignItems: "center" },
  logo: { width: 84, height: 84, borderRadius: 26, alignItems: "center", justifyContent: "center" },
});
