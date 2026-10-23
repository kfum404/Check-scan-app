// Корневые табы по макетам: Главная / Камера / Статистика / История / Профиль.
import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import CameraScreen from "../screens/CameraScreen";
import HistoryScreen from "../screens/HistoryScreen";
import HomeScreen from "../screens/HomeScreen";
import ProfileScreen from "../screens/ProfileScreen";
import StatsScreen from "../screens/StatsScreen";
import { useTheme } from "../theme";

export type RootTabParamList = {
  Home: undefined;
  Camera: undefined;
  Stats: undefined;
  History: { openReceiptId?: number } | undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();

const ICONS: Record<keyof RootTabParamList, keyof typeof Ionicons.glyphMap> = {
  Home: "home",
  Camera: "camera",
  Stats: "pie-chart",
  History: "time",
  Profile: "person",
};

const LABELS: Record<keyof RootTabParamList, string> = {
  Home: "Главная",
  Camera: "Камера",
  Stats: "Статистика",
  History: "История",
  Profile: "Профиль",
};

export default function RootTabs() {
  const { colors } = useTheme();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.subtext,
        tabBarStyle: { backgroundColor: colors.tabBar, borderTopColor: colors.border },
        tabBarIcon: ({ color, size, focused }) => (
          <Ionicons
            name={(focused ? ICONS[route.name] : `${ICONS[route.name]}-outline`) as keyof typeof Ionicons.glyphMap}
            color={color}
            size={size}
          />
        ),
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ title: LABELS.Home }} />
      <Tab.Screen name="Camera" component={CameraScreen} options={{ title: LABELS.Camera }} />
      <Tab.Screen name="Stats" component={StatsScreen} options={{ title: LABELS.Stats }} />
      <Tab.Screen name="History" component={HistoryScreen as React.ComponentType} options={{ title: LABELS.History }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ title: LABELS.Profile }} />
    </Tab.Navigator>
  );
}
