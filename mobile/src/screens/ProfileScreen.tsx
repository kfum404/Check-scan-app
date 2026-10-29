// Профиль: карточка пользователя, привязки (заглушки), тема, тумблеры, выход.
import React, { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, ErrorText, Segmented, Toggle } from "../components/ui";
import { useTheme } from "../theme";

export default function ProfileScreen() {
  const { colors, dark } = useTheme();
  const { user, logout, updateUser } = useAuth();
  const [error, setError] = useState<string>();

  if (!user) return null;

  const patch = async (body: Parameters<typeof updateUser>[0]) => {
    try {
      setError(undefined);
      await updateUser(body);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось сохранить");
    }
  };

  const confirmLogout = () => {
    Alert.alert("Выйти из аккаунта?", "Локальные данные сессии будут удалены", [
      { text: "Отмена", style: "cancel" },
      { text: "Выйти", style: "destructive", onPress: () => void logout() },
    ]);
  };

  const initials = user.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.bg }}>
      <Text style={[s.h1, { color: colors.text }]}>Профиль</Text>

      <Card>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
          <View style={[s.avatar, { backgroundColor: colors.primary }]}>
            <Text style={{ color: colors.onPrimary, fontSize: 20, fontWeight: "800" }}>{initials}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ color: colors.text, fontSize: 17, fontWeight: "700" }}>{user.name}</Text>
            <Text style={{ color: colors.subtext, fontSize: 13, marginTop: 2 }}>{user.email}</Text>
          </View>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginTop: 12 }}>
          <Ionicons name="checkmark-circle" size={14} color={colors.success} />
          <Text style={{ color: colors.subtext, fontSize: 12 }}>Аккаунт активен</Text>
        </View>
      </Card>

      <Text style={s.section}>Вход через сервисы</Text>
      <Card style={{ paddingVertical: 6 }}>
        <ServiceRow icon="logo-google" name="Google" note="в разработке" action="Скоро" onPress={() => {}} />
        <ServiceRow icon="mail" name="Email" note={user.email} action="Подключен" done onPress={() => {}} />
      </Card>

      <Text style={s.section}>Тема и формат</Text>
      <Card>
        <Segmented<"light" | "dark">
          value={dark ? "dark" : "light"}
          onChange={(v) => void patch({ theme_preference: v })}
          options={[
            { value: "light", label: "☀️ Светлая" },
            { value: "dark", label: "🌙 Темная" },
          ]}
          style={{ marginHorizontal: 0, marginBottom: 0 }}
        />
      </Card>
      <Card style={{ paddingVertical: 6 }}>
        <View style={s.kvRow}>
          <Text style={{ color: colors.text, fontSize: 15 }}>Валюта</Text>
          <Text style={{ color: colors.subtext, fontSize: 14 }}>Белорусский рубль · Br</Text>
        </View>
        <View style={[s.kvRow, { borderBottomWidth: 0 }]}>
          <Text style={{ color: colors.text, fontSize: 15 }}>Формат суммы</Text>
          <Text style={{ color: colors.subtext, fontSize: 14 }}>1 240 Br</Text>
        </View>
      </Card>

      <Text style={s.section}>Настройки</Text>
      <Card style={{ paddingVertical: 6 }}>
        <SettingRow
          title="Уведомления" note="напоминание об дневном лимите"
          value={user.notifications_enabled} onChange={(v) => void patch({ notifications_enabled: v })}
        />
        <SettingRow
          title="Автосохранение чеков" note="после успешного распознавания"
          value={user.autosave_enabled} onChange={(v) => void patch({ autosave_enabled: v })}
        />
        <SettingRow
          title="Вход с помощью биометрии" note="Face ID · Touch ID"
          value={user.biometrics_enabled} onChange={(v) => void patch({ biometrics_enabled: v })}
        />
      </Card>

      <ErrorText error={error} />
      <Button title="Выйти из аккаунта" variant="danger" icon={<Ionicons name="log-out-outline" size={18} color="#fff" />}
              onPress={confirmLogout} />

      <Text style={{ color: colors.subtext, fontSize: 11, textAlign: "center", marginBottom: 32 }}>
        ЧекСкан · версия 1.4.0
      </Text>
    </ScrollView>
  );
}

function ServiceRow(props: {
  icon: keyof typeof Ionicons.glyphMap;
  name: string; note: string; action: string; done?: boolean; onPress: () => void;
}) {
  const { colors } = useTheme();
  return (
    <TouchableOpacity style={s.kvRow} onPress={props.onPress}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12, flex: 1 }}>
        <Ionicons name={props.icon} size={20} color={colors.text} />
        <View>
          <Text style={{ color: colors.text, fontSize: 15 }}>{props.name}</Text>
          <Text style={{ color: colors.subtext, fontSize: 11 }}>{props.note}</Text>
        </View>
      </View>
      <Text style={{ color: props.done ? colors.success : colors.primary, fontSize: 13, fontWeight: "600" }}>
        {props.action}
      </Text>
    </TouchableOpacity>
  );
}

function SettingRow(props: { title: string; note: string; value: boolean; onChange: (v: boolean) => void }) {
  const { colors } = useTheme();
  return (
    <View style={s.kvRow}>
      <View style={{ flex: 1, paddingRight: 12 }}>
        <Text style={{ color: colors.text, fontSize: 15 }}>{props.title}</Text>
        <Text style={{ color: colors.subtext, fontSize: 11 }}>{props.note}</Text>
      </View>
      <Toggle value={props.value} onChange={props.onChange} />
    </View>
  );
}

const s = StyleSheet.create({
  h1: { fontSize: 22, fontWeight: "800", marginHorizontal: 16, marginTop: 16, marginBottom: 14 },
  section: { color: "#8A8FA3", fontSize: 12, marginHorizontal: 20, marginBottom: 8, marginTop: 4,
             textTransform: "uppercase", letterSpacing: 0.5 },
  avatar: { width: 56, height: 56, borderRadius: 28, alignItems: "center", justifyContent: "center" },
  kvRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#ECEEF5",
  },
});
