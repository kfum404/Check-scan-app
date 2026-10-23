// Главная: приветствие, период, герой-карта с лимитом, категории, последние чеки.
import React, { useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { LinearGradient } from "expo-linear-gradient";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";

import { receiptsApi, statsApi } from "../api";
import type { HomeStats } from "../api/types";
import { formatAmount, ReceiptRow } from "../components/ReceiptRow";
import { Card, EmptyState, Segmented } from "../components/ui";
import { categoryColor, useTheme } from "../theme";
import { useAuth } from "../auth/AuthContext";
import type { RootTabParamList } from "../navigation/RootTabs";

type Period = "today" | "week" | "month";

export default function HomeScreen({ navigation }: BottomTabScreenProps<RootTabParamList, "Home">) {
  const { colors } = useTheme();
  const { user } = useAuth();
  const [period, setPeriod] = useState<Period>("today");

  const home = useQuery({ queryKey: ["stats", "home"], queryFn: statsApi.home });
  const month = useQuery({ queryKey: ["stats", "summary", "month"], queryFn: () => statsApi.summary("month") });
  const last = useQuery({ queryKey: ["receipts", "last"], queryFn: () => receiptsApi.list(1, 5) });

  const h: HomeStats | undefined = home.data;
  const spent = period === "today" ? h?.today_spent : period === "week" ? undefined : h?.month_spent;
  const subtitle =
    period === "today" ? "Потрачено сегодня" : period === "week" ? "Потрачено за неделю" : "Потрачено за месяц";

  const byCategory =
    period === "today" ? h?.by_category_today
    : period === "week" ? undefined
    : month.data?.by_category;

  const refreshing = home.isRefetching || last.isRefetching;
  const refresh = () => { home.refetch(); month.refetch(); last.refetch(); };

  const now = new Date();
  const months = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
  const days = ["Воскресенье","Понедельник","Вторник","Среда","Четверг","Пятница","Суббота"];
  const weekTotal = (byCategory ?? []).reduce((a, c) => a + c.amount, 0);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bg }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
    >
      <Text style={[s.h1, { color: colors.text }]}>Добрый день, {user?.name ?? "Саныч"}</Text>
      <Text style={{ color: colors.subtext, fontSize: 13, marginHorizontal: 16, marginBottom: 14 }}>
        {now.getDate()} {months[now.getMonth()]}, {days[now.getDay()]}
      </Text>

      <Segmented<Period>
        value={period}
        onChange={setPeriod}
        options={[{ value: "today", label: "Сегодня" }, { value: "week", label: "Неделя" }, { value: "month", label: "Месяц" }]}
      />

      <LinearGradient colors={["#7C5CFC", "#9B8CFF"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                      style={s.hero}>
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 13 }}>{subtitle}</Text>
          <View style={s.heroBadge}><Text style={{ color: "#7C5CFC", fontSize: 11, fontWeight: "700" }}>День</Text></View>
        </View>
        <Text style={s.heroAmount}>{formatAmount(spent ?? h?.month_spent ?? 0, "Br")}</Text>

        <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 14 }}>
          <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 12 }}>
            Месячный лимит · {formatAmount(h?.month_limit ?? 0, "Br")}
          </Text>
          <Text style={{ color: "#fff", fontSize: 12, fontWeight: "700" }}>{h?.limit_used_pct ?? 0}%</Text>
        </View>
        <View style={s.progressTrack}>
          <View style={[s.progressFill, { width: `${Math.min(h?.limit_used_pct ?? 0, 100)}%` }]} />
        </View>

        <View style={{ flexDirection: "row", marginTop: 16 }}>
          <HeroStat value={String(h?.receipts_today ?? 0)} label="чеки за день" />
          <HeroStat value={String(h?.categories_today ?? 0)} label="категории" />
          <HeroStat value={formatAmount(h?.avg_receipt_today ?? 0, "Br")} label="средний чек" />
        </View>
      </LinearGradient>

      {(byCategory?.length ?? 0) > 0 && (
        <Card>
          <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 10 }}>
            <Text style={{ color: colors.text, fontSize: 15, fontWeight: "700" }}>
              Категории {period === "month" ? "за месяц" : "сегодня"}
            </Text>
            <Text style={{ color: colors.text, fontSize: 15, fontWeight: "700" }}>
              {formatAmount(period === "month" ? month.data?.total ?? 0 : weekTotal, "Br")}
            </Text>
          </View>
          <View style={s.stackedBar}>
            {(byCategory ?? []).map((c) => (
              <View key={c.label} style={{
                flex: c.amount, backgroundColor: categoryColor(c.label), height: 8,
                borderTopLeftRadius: 4, borderBottomLeftRadius: 4,
              }} />
            ))}
          </View>
          {(byCategory ?? []).map((c) => {
            const pct = weekTotal ? Math.round((c.amount / weekTotal) * 100) : 0;
            return (
              <View key={c.label} style={{ flexDirection: "row", alignItems: "center", marginTop: 10 }}>
                <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: categoryColor(c.label), marginRight: 8 }} />
                <Text style={{ color: colors.subtext, fontSize: 13, flex: 1 }}>{c.label}</Text>
                <Text style={{ color: colors.subtext, fontSize: 13, width: 40, textAlign: "right" }}>{pct}%</Text>
                <Text style={{ color: colors.text, fontSize: 13, fontWeight: "600", width: 90, textAlign: "right" }}>
                  {formatAmount(c.amount, "Br")}
                </Text>
              </View>
            );
          })}
        </Card>
      )}

      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center",
                     marginHorizontal: 16, marginTop: 6, marginBottom: 10 }}>
        <Text style={{ color: colors.text, fontSize: 17, fontWeight: "800" }}>Последние чеки</Text>
        <TouchableOpacity onPress={() => navigation.navigate("History")}>
          <Text style={{ color: colors.primary, fontSize: 13, fontWeight: "600" }}>Все чеки ›</Text>
        </TouchableOpacity>
      </View>

      {(last.data?.items.length ?? 0) === 0 && (
        <EmptyState title="Чеков пока нет" subtitle="Нажмите «Снять чек», чтобы начать" />
      )}
      {(last.data?.items ?? []).map((r) => (
        <ReceiptRow key={r.id} receipt={r} onPress={() => navigation.navigate("History", { openReceiptId: r.id })} />
      ))}

      <TouchableOpacity style={styles.fab} onPress={() => navigation.navigate("Camera")} activeOpacity={0.85}>
        <Ionicons name="camera" size={20} color="#fff" />
        <Text style={{ color: "#fff", fontSize: 16, fontWeight: "700" }}>Снять чек</Text>
      </TouchableOpacity>
      <View style={{ height: 28 }} />
    </ScrollView>
  );
}

function HeroStat(props: { value: string; label: string }) {
  return (
    <View style={{ flex: 1 }}>
      <Text style={{ color: "#fff", fontSize: 16, fontWeight: "800" }}>{props.value}</Text>
      <Text style={{ color: "rgba(255,255,255,0.75)", fontSize: 11, marginTop: 2 }}>{props.label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  h1: { fontSize: 22, fontWeight: "800", marginHorizontal: 16, marginTop: 16, marginBottom: 4 },
  hero: { borderRadius: 24, padding: 18, marginHorizontal: 16, marginBottom: 14 },
  heroBadge: { backgroundColor: "#fff", borderRadius: 10, paddingHorizontal: 10, paddingVertical: 3 },
  heroAmount: { color: "#fff", fontSize: 38, fontWeight: "800", marginTop: 6 },
  progressTrack: { height: 8, borderRadius: 4, backgroundColor: "rgba(255,255,255,0.35)", marginTop: 8 },
  progressFill: { height: 8, borderRadius: 4, backgroundColor: "#fff" },
  stackedBar: { flexDirection: "row", height: 8, borderRadius: 4, overflow: "hidden", gap: 2 },
});

const styles = StyleSheet.create({
  fab: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    backgroundColor: "#7C5CFC", borderRadius: 18, height: 52,
    marginHorizontal: 16, marginTop: 8,
  },
});
