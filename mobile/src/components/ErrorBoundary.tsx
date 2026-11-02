// Ограничение ошибок: в релизной сборке необработанная JS-ошибка роняет
// приложение с системным диалогом «сбой». ErrorBoundary показывает текст
// ошибки на экране — и для пользователя понятнее, и для диагностики.
import React from "react";
import { ScrollView, Text, View } from "react-native";

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // в релизе сюда можно подключить сбор crash-репортов
    console.error("ErrorBoundary:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    const e = this.state.error;
    return (
      <View style={{ flex: 1, backgroundColor: "#0F1115", padding: 24, paddingTop: 60 }}>
        <Text style={{ color: "#FF6B6B", fontSize: 20, fontWeight: "800", marginBottom: 12 }}>
          Что-то пошло не так
        </Text>
        <ScrollView>
          <Text style={{ color: "#E8EAF0", fontSize: 14, marginBottom: 8 }}>{String(e.message)}</Text>
          <Text style={{ color: "#8A8FA3", fontSize: 12 }} selectable>
            {String(e.stack).slice(0, 2000)}
          </Text>
        </ScrollView>
      </View>
    );
  }
}
