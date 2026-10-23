// Дизайн-токены «ЧекСкан» (из Figma-макетов) + контекст темы.
import React, { createContext, useContext } from "react";

export interface ThemeColors {
  bg: string;
  card: string;
  border: string;
  text: string;
  subtext: string;
  primary: string;
  primarySoft: string;
  onPrimary: string;
  success: string;
  danger: string;
  dangerSoft: string;
  chartGray: string;
  overlay: string;
  tabBar: string;
}

export const light: ThemeColors = {
  bg: "#F6F7FB",
  card: "#FFFFFF",
  border: "#ECEEF5",
  text: "#17182B",
  subtext: "#8A8FA3",
  primary: "#7C5CFC",
  primarySoft: "#EFEBFF",
  onPrimary: "#FFFFFF",
  success: "#2ECC8F",
  danger: "#E5484D",
  dangerSoft: "#FDECEC",
  chartGray: "#E3E5EF",
  overlay: "rgba(23,24,43,0.45)",
  tabBar: "#FFFFFF",
};

export const dark: ThemeColors = {
  bg: "#12131A",
  card: "#1C1E28",
  border: "#262936",
  text: "#F2F3F7",
  subtext: "#8A8FA3",
  primary: "#9B8CFF",
  primarySoft: "#2A2440",
  onPrimary: "#17182B",
  success: "#2ECC8F",
  danger: "#F2555A",
  dangerSoft: "#3A2226",
  chartGray: "#2C2F3D",
  overlay: "rgba(0,0,0,0.6)",
  tabBar: "#1C1E28",
};

// Цвета категорий — как в макете (кольца/иконки).
export const CATEGORY_COLORS: Record<string, string> = {
  "Продукты": "#8B5CF6",
  "Кафе и рестораны": "#EC4899",
  "Транспорт": "#14B8A6",
  "Здоровье": "#F5A623",
  "Аптека": "#F5A623",
  "Одежда и обувь": "#6366F1",
  "Связь и интернет": "#0EA5E9",
  "Товары для дома": "#84CC16",
  "Электроника": "#7C5CFC",
  "Развлечения": "#F97316",
  "Прочее": "#9CA3AF",
};
const PALETTE = ["#8B5CF6", "#EC4899", "#14B8A6", "#F5A623", "#0EA5E9", "#84CC16", "#F97316"];
export function categoryColor(name: string): string {
  return CATEGORY_COLORS[name] ?? PALETTE[Math.abs(hash(name)) % PALETTE.length];
}
function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return h;
}

interface ThemeCtx {
  colors: ThemeColors;
  dark: boolean;
  setDark: (v: boolean) => void;
}

export const ThemeContext = createContext<ThemeCtx>({
  colors: light,
  dark: false,
  setDark: () => {},
});

export const useTheme = () => useContext(ThemeContext);

export function ThemeProvider(props: {
  darkMode: boolean;
  onChange: (v: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <ThemeContext.Provider
      value={{ colors: props.darkMode ? dark : light, dark: props.darkMode, setDark: props.onChange }}
    >
      {props.children}
    </ThemeContext.Provider>
  );
}
