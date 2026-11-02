// Экран входа / регистрации — email + пароль и вход через Google (OAuth 2.0).
import React, { useState } from "react";
import {
  KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TouchableOpacity, View,
} from "react-native";
import * as WebBrowser from "expo-web-browser";

import { ApiError, API_URL } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, ErrorText, Field } from "../components/ui";
import { useTheme } from "../theme";

export default function LoginScreen() {
  const { colors } = useTheme();
  const { login, register, loginWithToken } = useAuth();
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

  // OAuth: открываем согласие Google в системном окне, сервер вернёт
  // редирект на checkscan://auth?token=<JWT>
  const loginWithGoogle = async () => {
    setError(undefined);
    setGoogleLoading(true);
    try {
      const res = await WebBrowser.openAuthSessionAsync(
        `${API_URL}/auth/google/start`,
        "checkscan://auth",
      );
      if (res.type === "success" && res.url.startsWith("checkscan://auth")) {
        const params = new URLSearchParams(res.url.split("?")[1] ?? "");
        const token = params.get("token");
        const oauthError = params.get("error");
        if (token) await loginWithToken(token);
        else if (oauthError === "oauth_not_configured")
          setError("Google OAuth пока не настроен на сервере");
        else setError("Вход через Google отменён или не удался");
      } else if (res.type !== "cancel") {
        setError("Вход через Google отменён или не удался");
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось войти через Google");
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
          onPress={() => void loginWithGoogle()}
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
