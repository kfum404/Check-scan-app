// Строка чека в списках (Главная, История) + форматирование сумм и дат.
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import type { Receipt } from "../api/types";
import { categoryColor, useTheme } from "../theme";

export function formatAmount(v: number, currency = "Br"): string {
  const rounded = Math.round(v * 100) / 100;
  const [int, dec] = rounded.toFixed(2).split(".");
  const spaced = int.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${spaced},${dec} ${currency}`;
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function formatDayLabel(iso: string): string {
  const d = new Date(iso);
  const months = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
  const today = new Date();
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const same = (a: Date, b: Date) => a.toDateString() === b.toDateString();
  if (same(d, today)) return `Сегодня · ${d.getDate()} ${months[d.getMonth()]}`;
  if (same(d, yesterday)) return `Вчера · ${d.getDate()} ${months[d.getMonth()]}`;
  const days = ["воскресенье","понедельник","вторник","среда","четверг","пятница","суббота"];
  return `${days[d.getDay()]} · ${d.getDate()} ${months[d.getMonth()]}`;
}

export const CATEGORY_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  "Продукты": "basket",
  "Кафе и рестораны": "cafe",
  "Транспорт": "car-sport",
  "Здоровье": "medkit",
  "Аптека": "medkit",
  "Одежда и обувь": "shirt",
  "Связь и интернет": "wifi",
  "Товары для дома": "home",
  "Электроника": "phone-portrait",
  "Развлечения": "ticket",
  "Прочее": "receipt",
};

export function ReceiptRow(props: { receipt: Receipt; onPress?: () => void }) {
  const { colors } = useTheme();
  const { receipt: r } = props;
  const color = categoryColor(r.category);
  const icon = CATEGORY_ICONS[r.category] ?? "receipt";
  return (
    <TouchableOpacity
      style={[s.row, { backgroundColor: colors.card, borderColor: colors.border }]}
      onPress={props.onPress}
      activeOpacity={props.onPress ? 0.7 : 1}
    >
      <View style={[s.icon, { backgroundColor: color + "22" }]}>
        <Ionicons name={icon} size={20} color={color} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={{ color: colors.text, fontSize: 15, fontWeight: "600" }} numberOfLines={1}>
          {r.shop_name}
        </Text>
        <Text style={{ color: colors.subtext, fontSize: 12, marginTop: 2 }}>
          {r.category} · {formatTime(r.date)}
        </Text>
      </View>
      <Text style={{ color: colors.text, fontSize: 15, fontWeight: "700" }}>
        {formatAmount(r.total_amount, r.currency)}
      </Text>
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  row: {
    flexDirection: "row", alignItems: "center", gap: 12,
    borderRadius: 16, borderWidth: 1, padding: 14,
    marginHorizontal: 16, marginBottom: 8,
  },
  icon: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
});
