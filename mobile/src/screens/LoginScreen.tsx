// Экран входа / регистрации — email + пароль (OAuth в roadmap, issue #16).
import React, { useState } from "react";
import {
  KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TouchableOpacity, View,
} from "react-native";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, ErrorText, Field } from "../components/ui";
import { useTheme } from "../theme";

export default function LoginScreen() {
  const { colors } = useTheme();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

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

        <TouchableOpacity onPress={() => { setMode(mode === "login" ? "register" : "login"); setError(undefined); }}>
          <Text style={{ color: colors.primary, fontSize: 14, fontWeight: "600" }}>
            {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
          </Text>
        </TouchableOpacity>

        <Text style={{ color: colors.subtext, fontSize: 11, marginTop: 24, textAlign: "center" }}>
          Вход через Google / Apple — в разработке
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  wrap: { flexGrow: 1, justifyContent: "center", padding: 24, paddingBottom: 60, alignItems: "center" },
  logo: { width: 84, height: 84, borderRadius: 26, alignItems: "center", justifyContent: "center" },
});
