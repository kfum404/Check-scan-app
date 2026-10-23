// История: поиск, фильтры по периоду, группировка по дням, детализация в bottom sheet.
import React, { useEffect, useMemo, useState } from "react";
import {
  Alert, Modal, RefreshControl, ScrollView, Share, StyleSheet, Text,
  TextInput, TouchableOpacity, View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { receiptsApi } from "../api";
import type { Receipt } from "../api/types";
import { formatAmount, formatDayLabel, formatTime, ReceiptRow } from "../components/ReceiptRow";
import { Button, EmptyState } from "../components/ui";
import { useTheme } from "../theme";

type Filter = "all" | "today" | "week" | "month";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Все время" },
  { value: "today", label: "Сегодня" },
  { value: "week", label: "7 дней" },
  { value: "month", label: "30 дней" },
];

export default function HistoryScreen(props: { openReceiptId?: number }) {
  const { colors } = useTheme();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [selectedId, setSelectedId] = useState<number | null>(props.openReceiptId ?? null);

  const list = useQuery({
    queryKey: ["receipts", "history"],
    queryFn: () => receiptsApi.list(1, 200),
  });

  useEffect(() => {
    if (props.openReceiptId) setSelectedId(props.openReceiptId);
  }, [props.openReceiptId]);

  const remove = useMutation({
    mutationFn: receiptsApi.remove,
    onSuccess: () => {
      setSelectedId(null);
      void queryClient.invalidateQueries({ queryKey: ["receipts"] });
      void queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const filtered = useMemo(() => {
    let items = list.data?.items ?? [];
    const now = new Date();
    if (filter === "today") {
      items = items.filter((r) => sameDay(new Date(r.date), now));
    } else if (filter === "week") {
      const t = new Date(now); t.setDate(now.getDate() - 7);
      items = items.filter((r) => new Date(r.date) >= t);
    } else if (filter === "month") {
      const t = new Date(now); t.setDate(now.getDate() - 30);
      items = items.filter((r) => new Date(r.date) >= t);
    }
    const q = query.trim().toLowerCase();
    if (q) {
      items = items.filter((r) =>
        r.shop_name.toLowerCase().includes(q) ||
        r.category.toLowerCase().includes(q) ||
        String(r.total_amount).includes(q)
      );
    }
    return items;
  }, [list.data, filter, query]);

  const groups = useMemo(() => {
    const map = new Map<string, Receipt[]>();
    for (const r of filtered) {
      const key = new Date(r.date).toDateString();
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(r);
    }
    return [...map.entries()];
  }, [filtered]);

  const monthTotal = useMemo(
    () => (list.data?.items ?? []).reduce((a, r) => a + r.total_amount, 0),
    [list.data]
  );

  const confirmDelete = (id: number) => {
    Alert.alert("Удалить чек?", "Действие нельзя отменить", [
      { text: "Отмена", style: "cancel" },
      { text: "Удалить", style: "destructive", onPress: () => remove.mutate(id) },
    ]);
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center",
                     marginHorizontal: 16, marginTop: 16, marginBottom: 4 }}>
        <Text style={{ color: colors.text, fontSize: 22, fontWeight: "800" }}>История чеков</Text>
        <View style={{ backgroundColor: colors.primarySoft, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 5 }}>
          <Text style={{ color: colors.primary, fontSize: 12, fontWeight: "700" }}>
            {formatAmount(monthTotal, "Br")} · {list.data?.total ?? 0}
          </Text>
        </View>
      </View>

      <View style={[s.search, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <Ionicons name="search" size={18} color={colors.subtext} />
        <TextInputLike value={query} onChangeText={setQuery} placeholder="Поиск по магазину или сумме" />
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false}
                  contentContainerStyle={{ gap: 8, paddingHorizontal: 16, marginBottom: 12 }}>
        {FILTERS.map((f) => {
          const active = f.value === filter;
          return (
            <TouchableOpacity
              key={f.value}
              onPress={() => setFilter(f.value)}
              style={[s.chip, { backgroundColor: active ? colors.primary : colors.card,
                                borderColor: active ? colors.primary : colors.border }]}
            >
              <Text style={{ color: active ? colors.onPrimary : colors.subtext, fontSize: 13, fontWeight: "600" }}>
                {f.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      <ScrollView
        refreshControl={<RefreshControl refreshing={list.isRefetching} onRefresh={list.refetch} />}
      >
        {groups.length === 0 && <EmptyState title="Ничего не найдено" subtitle="Попробуйте изменить фильтр" />}
        {groups.map(([day, items]) => (
          <View key={day}>
            <Text style={{ color: colors.subtext, fontSize: 12, marginHorizontal: 16, marginBottom: 8, marginTop: 4 }}>
              {formatDayLabel(items[0].date)}
            </Text>
            {items.map((r) => (
              <ReceiptRow key={r.id} receipt={r} onPress={() => setSelectedId(r.id)} />
            ))}
          </View>
        ))}
        <View style={{ height: 24 }} />
      </ScrollView>

      <ReceiptDetailModal receiptId={selectedId} onClose={() => setSelectedId(null)} onDelete={confirmDelete} />
    </View>
  );
}

function TextInputLike(props: { value: string; onChangeText: (v: string) => void; placeholder: string }) {
  const { colors } = useTheme();
  return (
    <TextInput
      value={props.value}
      onChangeText={props.onChangeText}
      placeholder={props.placeholder}
      placeholderTextColor={colors.subtext}
      style={{ flex: 1, marginLeft: 8, fontSize: 14, color: colors.text, paddingVertical: 0 }}
    />
  );
}

function ReceiptDetailModal(props: {
  receiptId: number | null;
  onClose: () => void;
  onDelete: (id: number) => void;
}) {
  const { colors } = useTheme();
  const detail = useQuery({
    queryKey: ["receipts", "detail", props.receiptId],
    queryFn: () => receiptsApi.detail(props.receiptId!),
    enabled: props.receiptId != null,
  });
  const r = detail.data;

  const exportReceipt = async () => {
    if (!r) return;
    const lines = [
      `${r.shop_name} — ${formatAmount(r.total_amount, r.currency)}`,
      `${r.category} · ${new Date(r.date).toLocaleString()}`,
      "",
      ...(r.items ?? []).map((i) => `${i.item_name} — ${formatAmount(i.price, r.currency)}`),
    ].join("\n");
    await Share.share({ message: lines });
  };

  return (
    <Modal visible={props.receiptId != null} transparent animationType="slide" onRequestClose={props.onClose}>
      <TouchableOpacity style={[StyleSheet.absoluteFill, { backgroundColor: colors.overlay }]} onPress={props.onClose} />
      <View style={[s.sheet, { backgroundColor: colors.card }]}>
        {!r ? (
          <EmptyState title="Загрузка…" />
        ) : (
          <>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: colors.text, fontSize: 18, fontWeight: "800" }}>{r.shop_name}</Text>
                <Text style={{ color: colors.subtext, fontSize: 12, marginTop: 2 }}>
                  {r.category} · {formatTime(r.date)}
                </Text>
              </View>
              <TouchableOpacity onPress={props.onClose}>
                <Ionicons name="close" size={22} color={colors.subtext} />
              </TouchableOpacity>
            </View>

            <Text style={{ color: colors.subtext, fontSize: 12, marginTop: 16, marginBottom: 6 }}>Позиции</Text>
            {(r.items ?? []).slice(0, 6).map((i) => (
              <View key={i.id ?? i.item_name} style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 6 }}>
                <Text style={{ color: colors.text, fontSize: 14, flex: 1, paddingRight: 12 }} numberOfLines={1}>
                  {i.item_name}
                </Text>
                <Text style={{ color: colors.text, fontSize: 14 }}>{formatAmount(i.price, r.currency)}</Text>
              </View>
            ))}
            {(r.items.length > 6) && (
              <Text style={{ color: colors.subtext, fontSize: 12 }}>+ ещё {r.items.length - 6} позиции</Text>
            )}
            {(r.items.length === 0) && (
              <Text style={{ color: colors.subtext, fontSize: 13 }}>Позиции не распознаны</Text>
            )}

            <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 14, marginBottom: 16 }}>
              <Text style={{ color: colors.subtext, fontSize: 13 }}>Всего · {r.items.length} позиций</Text>
              <Text style={{ color: colors.text, fontSize: 17, fontWeight: "800" }}>
                {formatAmount(r.total_amount, r.currency)}
              </Text>
            </View>

            <View style={{ flexDirection: "row", gap: 10 }}>
              <View style={{ flex: 1 }}>
                <Button title="Экспорт" variant="ghost" onPress={() => void exportReceipt()} />
              </View>
              <View style={{ flex: 1 }}>
                <Button title="Удалить" variant="danger" onPress={() => props.onDelete(r.id)} />
              </View>
            </View>
          </>
        )}
      </View>
    </Modal>
  );
}

function sameDay(a: Date, b: Date) {
  return a.toDateString() === b.toDateString();
}

const s = StyleSheet.create({
  search: {
    flexDirection: "row", alignItems: "center", borderWidth: 1, borderRadius: 14,
    marginHorizontal: 16, marginBottom: 12, paddingHorizontal: 12, height: 44,
  },
  chip: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 7 },
  sheet: {
    position: "absolute", bottom: 0, left: 0, right: 0,
    borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, paddingBottom: 30,
  },
});
