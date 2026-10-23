// Общие UI-примитивы по макетам: Card, Button, Segmented, Toggle, Input, пустые состояния.
import React from "react";
import {
  ActivityIndicator, StyleSheet, Text, TextInput, TextInputProps,
  TouchableOpacity, View, ViewStyle,
} from "react-native";

import { useTheme } from "../theme";

export function Card(props: { children: React.ReactNode; style?: ViewStyle }) {
  const { colors } = useTheme();
  return (
    <View style={[s.card, { backgroundColor: colors.card, borderColor: colors.border }, props.style]}>
      {props.children}
    </View>
  );
}

export function Button(props: {
  title: string;
  onPress: () => void;
  variant?: "primary" | "danger" | "ghost";
  loading?: boolean;
  icon?: React.ReactNode;
  disabled?: boolean;
}) {
  const { colors } = useTheme();
  const bg =
    props.variant === "danger" ? colors.danger : props.variant === "ghost" ? "transparent" : colors.primary;
  const fg = props.variant === "ghost" ? colors.primary : props.variant === "danger" ? "#fff" : colors.onPrimary;
  return (
    <TouchableOpacity
      style={[s.button, { backgroundColor: bg, opacity: props.disabled || props.loading ? 0.6 : 1 }]}
      onPress={props.onPress}
      disabled={props.disabled || props.loading}
      activeOpacity={0.8}
    >
      {props.loading ? <ActivityIndicator color={fg} /> : (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          {props.icon}
          <Text style={[s.buttonText, { color: fg }]}>{props.title}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

export function Segmented<T extends string>(props: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  style?: ViewStyle;
}) {
  const { colors } = useTheme();
  return (
    <View style={[s.segmented, { backgroundColor: colors.border }, props.style]}>
      {props.options.map((o) => {
        const active = o.value === props.value;
        return (
          <TouchableOpacity
            key={o.value}
            style={[s.segment, active && { backgroundColor: colors.card, borderRadius: 14 }]}
            onPress={() => props.onChange(o.value)}
          >
            <Text style={{ color: active ? colors.text : colors.subtext, fontWeight: active ? "600" : "500", fontSize: 13 }}>
              {o.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export function Toggle(props: { value: boolean; onChange: (v: boolean) => void }) {
  const { colors } = useTheme();
  return (
    <TouchableOpacity
      onPress={() => props.onChange(!props.value)}
      style={[s.toggle, { backgroundColor: props.value ? colors.primary : colors.border }]}
      activeOpacity={0.8}
    >
      <View style={[s.toggleKnob, { alignSelf: props.value ? "flex-end" : "flex-start", backgroundColor: "#fff" }]} />
    </TouchableOpacity>
  );
}

export function Field(props: TextInputProps & { label: string; error?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={{ marginBottom: 12 }}>
      <Text style={{ color: colors.subtext, fontSize: 12, marginBottom: 6 }}>{props.label}</Text>
      <TextInput
        placeholderTextColor={colors.subtext}
        style={[s.input, { backgroundColor: colors.card, borderColor: props.error ? colors.danger : colors.border, color: colors.text }]}
        {...props}
      />
    </View>
  );
}

export function EmptyState(props: { title: string; subtitle?: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ alignItems: "center", paddingVertical: 32 }}>
      <Text style={{ color: colors.text, fontSize: 16, fontWeight: "600" }}>{props.title}</Text>
      {props.subtitle ? <Text style={{ color: colors.subtext, fontSize: 13, marginTop: 4 }}>{props.subtitle}</Text> : null}
    </View>
  );
}

export function ErrorText(props: { error?: string }) {
  const { colors } = useTheme();
  if (!props.error) return null;
  return <Text style={{ color: colors.danger, fontSize: 13, marginBottom: 12 }}>{props.error}</Text>;
}

const s = StyleSheet.create({
  card: {
    borderRadius: 20, borderWidth: 1, padding: 16, marginHorizontal: 16, marginBottom: 12,
  },
  button: {
    height: 52, borderRadius: 16, alignItems: "center", justifyContent: "center",
    marginHorizontal: 16, marginBottom: 12,
  },
  buttonText: { fontSize: 16, fontWeight: "600" },
  segmented: {
    flexDirection: "row", borderRadius: 16, padding: 4, marginHorizontal: 16, marginBottom: 12,
  },
  segment: { flex: 1, paddingVertical: 8, alignItems: "center" },
  toggle: {
    width: 46, height: 26, borderRadius: 13, padding: 3, justifyContent: "center",
  },
  toggleKnob: { width: 20, height: 20, borderRadius: 10 },
  input: {
    borderWidth: 1, borderRadius: 14, paddingHorizontal: 14, height: 48, fontSize: 15,
  },
});
