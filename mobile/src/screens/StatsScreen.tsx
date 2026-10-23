// Статистика: период (неделя/месяц/всё), итоги, динамика (столбцы), структура (кольцо).
import React, { useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";

import { useQuery } from "@tanstack/react-query";

import { statsApi } from "../api";
import type { SummaryStats } from "../api/types";
import { BarsChart, DonutChart } from "../components/Charts";
import { formatAmount } from "../components/ReceiptRow";
import { Card, EmptyState, Segmented } from "../components/ui";
import { categoryColor, useTheme } from "../theme";

type Period = "week" | "month" | "all";

export default function StatsScreen() {
  const { colors } = useTheme();
  const [period, setPeriod] = useState<Period>("week");
  const q = useQuery({
    queryKey: ["stats", "summary", period],
    queryFn: () => statsApi.summary(period),
  });
  const d: SummaryStats | undefined = q.data;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bg }}
      refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={q.refetch} />}
    >
      <Text style={[s.h1, { color: colors.text }]}>Статистика</Text>
      <Text style={{ color: colors.subtext, fontSize: 13, marginHorizontal: 16, marginBottom: 14 }}>
        {period === "week" ? "Текущая неделя" : period === "month" ? "Текущий месяц" : "Вся история"}
      </Text>

      <Segmented<Period>
        value={period}
        onChange={setPeriod}
        options={[
          { value: "week", label: "Неделя" },
          { value: "month", label: "Месяц" },
          { value: "all", label: "За всё время" },
        ]}
      />

      <Card>
        <Text style={{ color: colors.subtext, fontSize: 13 }}>
          {period === "week" ? "Расходы за неделю" : period === "month" ? "Расходы за месяц" : "Расходы всего"}
        </Text>
        <Text style={{ color: colors.text, fontSize: 32, fontWeight: "800", marginTop: 4 }}>
          {formatAmount(d?.total ?? 0, "Br")}
        </Text>
        <View style={{ flexDirection: "row", marginTop: 14 }}>
          <SummaryStat value={String(d?.count ?? 0)} label="чеков" />
          <SummaryStat value={formatAmount(d?.avg ?? 0, "Br")} label="средний чек" />
          <SummaryStat value={formatAmount(d?.max ?? 0, "Br")} label="максимум" />
        </View>
      </Card>

      <Card>
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 12 }}>
          <Text style={{ color: colors.text, fontSize: 15, fontWeight: "700" }}>Динамика расходов</Text>
          {d && d.by_day.length > 0 && (
            <Text style={{ color: colors.primary, fontSize: 12, fontWeight: "600" }}>
              пик · {d.by_day.reduce((a, b) => (b.amount > a.amount ? b : a)).label}
            </Text>
          )}
        </View>
        {(d?.by_day.length ?? 0) === 0 ? (
          <EmptyState title="Нет данных" subtitle="Сканируйте чеки, чтобы увидеть динамику" />
        ) : (
          <BarsChart data={d?.by_day ?? []} />
        )}
      </Card>

      <Card>
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 12 }}>
          <Text style={{ color: colors.text, fontSize: 15, fontWeight: "700" }}>Структура расходов</Text>
          <Text style={{ color: colors.subtext, fontSize: 12 }}>
            {period === "week" ? "за неделю" : period === "month" ? "за месяц" : "всего"}
          </Text>
        </View>
        {(d?.by_category.length ?? 0) === 0 ? (
          <EmptyState title="Категорий пока нет" />
        ) : (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 16 }}>
            <DonutChart data={d?.by_category ?? []} />
            <View style={{ flex: 1 }}>
              {(d?.by_category ?? []).map((c) => {
                const pct = d?.total ? Math.round((c.amount / d.total) * 100) : 0;
                return (
                  <View key={c.label} style={{ flexDirection: "row", alignItems: "center", marginBottom: 8 }}>
                    <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: categoryColor(c.label), marginRight: 8 }} />
                    <View style={{ flex: 1 }}>
                      <Text style={{ color: colors.text, fontSize: 13 }} numberOfLines={1}>{c.label}</Text>
                      <Text style={{ color: colors.subtext, fontSize: 11 }}>{pct}%</Text>
                    </View>
                    <Text style={{ color: colors.text, fontSize: 13, fontWeight: "600" }}>
                      {formatAmount(c.amount, "Br")}
                    </Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}
      </Card>
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

function SummaryStat(props: { value: string; label: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ flex: 1 }}>
      <Text style={{ color: colors.text, fontSize: 16, fontWeight: "800" }}>{props.value}</Text>
      <Text style={{ color: colors.subtext, fontSize: 11, marginTop: 2 }}>{props.label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  h1: { fontSize: 22, fontWeight: "800", marginHorizontal: 16, marginTop: 16, marginBottom: 4 },
});
