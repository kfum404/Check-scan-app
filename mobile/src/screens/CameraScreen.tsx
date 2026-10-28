// Камера: съёмка/галерея → OCR на сервере → экран корректировки → сохранение.
// Ручной ввод — тот же экран формы без фото (draft создаётся как "Не распознан",
// сервер всё равно принимает PATCH; для MVP ручной чек сохраняем как подтверждённый
// с магазином из поля).
import React, { useRef, useState } from "react";
import {
  ActivityIndicator, Image, KeyboardAvoidingView, Platform, ScrollView,
  StyleSheet, Text, TouchableOpacity, View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";

import { receiptsApi } from "../api";
import { ApiError } from "../api/client";
import type { ReceiptDetail, ScanResult } from "../api/types";
import { Button, ErrorText, Field } from "../components/ui";
import { useTheme } from "../theme";

type Stage =
  | { kind: "camera" }
  | { kind: "scanning"; uri: string }
  | { kind: "edit"; scan: ScanResult | null; uri?: string };

export default function CameraScreen() {
  const [stage, setStage] = useState<Stage>({ kind: "camera" });

  if (stage.kind === "camera") {
    return <CameraStage onPhoto={(uri) => setStage({ kind: "scanning", uri })} onManual={() => setStage({ kind: "edit", scan: null })} />;
  }
  if (stage.kind === "scanning") {
    return <ScanningStage uri={stage.uri} onDone={(scan) => setStage({ kind: "edit", scan, uri: stage.uri })} onBack={() => setStage({ kind: "camera" })} />;
  }
  return (
    <EditStage
      scan={stage.scan}
      photoUri={stage.uri}
      onDone={() => setStage({ kind: "camera" })}
      onBack={() => setStage({ kind: "camera" })}
    />
  );
}

/* ---------- этап 1: видоискатель ---------- */
function CameraStage(props: { onPhoto: (uri: string) => void; onManual: () => void }) {
  const [permission, requestPermission] = useCameraPermissions();
  const ref = useRef<CameraView>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [facing, setFacing] = useState<"back" | "front">("back");
  const [error, setError] = useState<string>();

  if (!permission) return <View style={s.center}><ActivityIndicator /></View>;
  if (!permission.granted) {
    return (
      <View style={[s.center, { padding: 32 }]}>
        <Text style={{ textAlign: "center", marginBottom: 16 }}>
          Нужен доступ к камере, чтобы сканировать чеки
        </Text>
        <Button title="Разрешить камеру" onPress={() => void requestPermission()} />
      </View>
    );
  }

  const capture = async () => {
    if (busy || !ready) return;
    setBusy(true);
    setError(undefined);
    try {
      const photo = await ref.current?.takePictureAsync({ quality: 0.85 });
      if (photo) {
        props.onPhoto(photo.uri);
      } else {
        setError("Камера ещё не готова, попробуйте ещё раз");
      }
    } catch (e) {
      console.warn("takePictureAsync failed:", e);
      setError("Не удалось сделать фото. Проверьте, что камера не занята другим приложением.");
    } finally {
      setBusy(false);
    }
  };

  const fromGallery = async () => {
    const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.85 });
    const uri = r.assets?.[0]?.uri;
    if (!r.canceled && uri) props.onPhoto(uri);
  };

  return (
    <View style={{ flex: 1, backgroundColor: "#000" }}>
      <CameraView
        style={{ flex: 1 }}
        ref={ref}
        facing={facing}
        onCameraReady={() => setReady(true)}
      />
      <View style={s.frame} pointerEvents="none" />
      <Text style={s.hint}>Текст должен быть читаемым и в фокусе</Text>

      {error ? (
        <View style={{ position: "absolute", top: 110, left: 24, right: 24, backgroundColor: "rgba(200,40,40,0.85)", borderRadius: 12, padding: 10 }}>
          <Text style={{ color: "#fff", fontSize: 13, textAlign: "center" }}>{error}</Text>
        </View>
      ) : null}

      <TouchableOpacity style={[s.close, { position: "absolute", top: 54, left: 20 }]} onPress={() => {}}>
        <Ionicons name="close" size={22} color="#fff" />
      </TouchableOpacity>

      <View style={s.controls}>
        <TouchableOpacity style={s.sideBtn} onPress={() => void fromGallery()}>
          <Ionicons name="image-outline" size={24} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity style={[s.shutter, (!ready || busy) && { opacity: 0.5 }]} onPress={() => void capture()} disabled={busy || !ready}>
          {busy ? <ActivityIndicator color="#000" /> : <View style={s.shutterInner} />}
        </TouchableOpacity>
        <TouchableOpacity style={s.sideBtn} onPress={() => setFacing((f) => (f === "back" ? "front" : "back"))}>
          <Ionicons name="sync-outline" size={24} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

/* ---------- этап 2: распознавание на сервере ---------- */
function ScanningStage(props: { uri: string; onDone: (scan: ScanResult) => void; onBack: () => void }) {
  const { colors } = useTheme();
  const [error, setError] = useState<string>();
  const started = useRef(false);

  const mutation = useMutation({
    mutationFn: async (uri: string) => {
      const form = new FormData();
      // @ts-expect-error RN FormData file descriptor
      form.append("file", { uri, name: "check.jpg", type: "image/jpeg" });
      return receiptsApi.scan(form);
    },
    onSuccess: props.onDone,
    onError: (e) => setError(e instanceof ApiError ? e.message : "Ошибка распознавания"),
  });

  React.useEffect(() => {
    if (!started.current) {
      started.current = true;
      mutation.mutate(props.uri);
    }
  }, []);

  return (
    <View style={{ flex: 1, backgroundColor: "#000" }}>
      <Image source={{ uri: props.uri }} style={{ flex: 1, opacity: 0.5 }} resizeMode="cover" />
      <View style={[StyleSheet.absoluteFill, s.center]}>
        <ActivityIndicator size="large" color="#fff" />
        <Text style={{ color: "#fff", marginTop: 14, fontSize: 15 }}>Распознаём чек…</Text>
        <Text style={{ color: "rgba(255,255,255,0.7)", marginTop: 6, fontSize: 12 }}>
          Обычно 5–30 секунд
        </Text>
        {error ? (
          <View style={{ marginTop: 24, alignItems: "center" }}>
            <ErrorText error={error} />
            <Button title="Попробовать снова" variant="ghost" onPress={() => { setError(undefined); mutation.mutate(props.uri); }} />
            <Button title="Назад" variant="ghost" onPress={props.onBack} />
          </View>
        ) : null}
      </View>
      {!error && (
        <TouchableOpacity style={{ position: "absolute", top: 54, left: 20 }} onPress={props.onBack}>
          <Ionicons name="close" size={24} color="#fff" />
        </TouchableOpacity>
      )}
    </View>
  );
}

/* ---------- этап 3: корректировка и сохранение ---------- */
function EditStage(props: { scan: ScanResult | null; photoUri?: string; onDone: () => void; onBack: () => void }) {
  const { colors } = useTheme();
  const queryClient = useQueryClient();
  const r: ReceiptDetail | null = props.scan?.receipt ?? null;
  const low = new Set(props.scan?.low_confidence_fields ?? []);

  const [amount, setAmount] = useState(r ? String(r.total_amount) : "");
  const [shop, setShop] = useState(r?.shop_name === "Не распознан" ? "" : (r?.shop_name ?? ""));
  const [dateStr, setDateStr] = useState(r ? toInputDate(r.date) : toInputDate(new Date().toISOString()));
  const [error, setError] = useState<string>();

  const confirm = useMutation({
    mutationFn: async () => {
      const total = Number(amount.replace(",", "."));
      if (!shop.trim()) throw new ApiError({ code: "VALIDATION", message: "Укажите магазин" });
      if (!total || total <= 0) throw new ApiError({ code: "VALIDATION", message: "Проверьте сумму" });
      if (!r) {
        // ручной ввод без фото — отдельный эндпоинт
        return receiptsApi.manual({
          shop_name: shop.trim(), date: fromInputDate(dateStr), total_amount: total,
        });
      }
      return receiptsApi.confirm(r.id, {
        shop_name: shop.trim(), date: fromInputDate(dateStr), total_amount: total,
        category: r.category,
        items: r.items.map((i) => ({ item_name: i.item_name, price: i.price })),
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["receipts"] });
      void queryClient.invalidateQueries({ queryKey: ["stats"] });
      props.onDone();
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Не удалось сохранить"),
  });

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ paddingBottom: 32 }} keyboardShouldPersistTaps="handled">
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center",
                       marginHorizontal: 16, marginTop: 16, marginBottom: 8 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <Ionicons name="checkmark-circle" size={16} color={colors.success} />
            <Text style={{ color: colors.success, fontSize: 13, fontWeight: "600" }}>Данные распознаны</Text>
          </View>
          <Text style={{ color: colors.subtext, fontSize: 12 }}>можно поправить</Text>
        </View>

        {props.photoUri && (
          <Image source={{ uri: props.photoUri }} style={{ height: 140, borderRadius: 16, marginHorizontal: 16, marginBottom: 8 }} resizeMode="cover" />
        )}

        <View style={{ flexDirection: "row", alignItems: "center", marginHorizontal: 16, marginBottom: 4 }}>
          <Text style={{ color: colors.text, fontSize: 34, fontWeight: "800", flex: 1 }}>
            {amount ? `${amount} Br` : "— Br"}
          </Text>
          <Ionicons name="pencil" size={20} color={colors.primary} />
        </View>

        <View style={{ paddingHorizontal: 16, marginTop: 8 }}>
          <Field label="Сумма" value={amount} onChangeText={setAmount}
                 keyboardType="decimal-pad" error={low.has("total_amount")} placeholder="0.00" />
          <Field label="Магазин" value={shop} onChangeText={setShop}
                 error={low.has("shop_name")} placeholder="Евроопт" autoCapitalize="sentences" />
          <Field label="Дата и время" value={dateStr} onChangeText={setDateStr}
                 error={low.has("date")} placeholder="14.05.2026, 12:40" />
        </View>

        <ErrorText error={error} />
        <Button title="Сохранить чек" onPress={() => { setError(undefined); confirm.mutate(); }} loading={confirm.isPending} />
        {!r && (
          <TouchableOpacity onPress={props.onBack} style={{ alignItems: "center", marginTop: 4 }}>
            <Text style={{ color: colors.primary, fontSize: 14, fontWeight: "600" }}>Заполнить вручную позже</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

/* ---------- helpers ---------- */
function toInputDate(iso: string): string {
  const d = new Date(iso);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${dd}.${mm}.${d.getFullYear()}, ${hh}:${mi}`;
}
function fromInputDate(s: string): string {
  const m = s.match(/(\d{2})\.(\d{2})\.(\d{4})[,\s]*(\d{2}):(\d{2})?/);
  if (!m) return new Date().toISOString();
  const minute = m[5] ? +m[5] : 0;
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], minute).toISOString();
}

const s = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  frame: {
    position: "absolute", top: "22%", left: 28, right: 28, height: "38%",
    borderWidth: 2, borderColor: "rgba(255,255,255,0.8)", borderStyle: "dashed",
    borderRadius: 20,
  },
  hint: {
    position: "absolute", bottom: 150, alignSelf: "center",
    color: "rgba(255,255,255,0.9)", fontSize: 13,
    backgroundColor: "rgba(0,0,0,0.45)", paddingHorizontal: 14, paddingVertical: 6, borderRadius: 12,
  },
  close: {
    width: 40, height: 40, borderRadius: 20, backgroundColor: "rgba(0,0,0,0.4)",
    alignItems: "center", justifyContent: "center",
  },
  controls: {
    position: "absolute", bottom: 34, left: 0, right: 0,
    flexDirection: "row", alignItems: "center", justifyContent: "space-evenly",
  },
  shutter: {
    width: 74, height: 74, borderRadius: 37, backgroundColor: "#fff",
    alignItems: "center", justifyContent: "center",
  },
  shutterInner: { width: 60, height: 60, borderRadius: 30, backgroundColor: "#fff", borderWidth: 4, borderColor: "#D9D9E3" },
  sideBtn: {
    width: 46, height: 46, borderRadius: 23, backgroundColor: "rgba(0,0,0,0.4)",
    alignItems: "center", justifyContent: "center",
  },
});
