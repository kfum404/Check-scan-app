// ЧекСкан — точка входа: сессия → тема → навигация (вход или табы).
import React from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer, DarkTheme, DefaultTheme } from "@react-navigation/native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import RootTabs from "./src/navigation/RootTabs";
import LoginScreen from "./src/screens/LoginScreen";
import { useTheme } from "./src/theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

function Root() {
  const { user, bootstrapping } = useAuth();
  const { colors, dark } = useTheme();

  if (bootstrapping) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  const navTheme = dark ? DarkTheme : DefaultTheme;
  return (
    <NavigationContainer
      theme={{ ...navTheme, colors: { ...navTheme.colors, background: colors.bg, card: colors.card, text: colors.text, border: colors.border, primary: colors.primary } }}
    >
      <StatusBar barStyle={dark ? "light-content" : "dark-content"} />
      {user ? <RootTabs /> : <LoginScreen />}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Root />
        </AuthProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
