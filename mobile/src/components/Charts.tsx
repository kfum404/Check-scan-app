// Графики на react-native-svg: столбчатая динамика и кольцевая структура расходов.
import React from "react";
import { Text, View } from "react-native";
import Svg, { Circle, Rect } from "react-native-svg";

import type { StatsEntry } from "../api/types";
import { categoryColor, useTheme } from "../theme";

export function BarsChart(props: { data: StatsEntry[]; highlightMax?: boolean }) {
  const { colors } = useTheme();
  const max = Math.max(...props.data.map((d) => d.amount), 1);
  const maxIdx = props.data.findIndex((d) => d.amount === max);
  const W = 320, H = 140, PAD = 18;

  return (
    <View style={{ alignItems: "center" }}>
      <Svg width={W} height={H}>
        {props.data.map((d, i) => {
          const barW = (W - PAD * 2) / props.data.length - 10;
          const x = PAD + i * ((W - PAD * 2) / props.data.length) + 5;
          const h = Math.max((d.amount / max) * (H - 34), d.amount > 0 ? 6 : 3);
          const highlight = props.highlightMax !== false && i === maxIdx && d.amount > 0;
          return (
            <Rect
              key={d.label + i}
              x={x} y={H - 22 - h} width={barW} height={h} rx={6}
              fill={highlight ? colors.primary : colors.chartGray}
            />
          );
        })}
      </Svg>
      <View style={{ flexDirection: "row", width: W - PAD * 2, justifyContent: "space-between", marginTop: -18 }}>
        {props.data.map((d, i) => (
          <Text key={d.label + i} style={{ color: colors.subtext, fontSize: 11, width: 30, textAlign: "center" }}>
            {d.label}
          </Text>
        ))}
      </View>
    </View>
  );
}

export function DonutChart(props: { data: StatsEntry[]; size?: number }) {
  const { colors } = useTheme();
  const size = props.size ?? 120;
  const r = size / 2 - 8;
  const C = 2 * Math.PI * r;
  const total = props.data.reduce((acc, d) => acc + d.amount, 0) || 1;
  let offset = 0;

  return (
    <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
      <Svg width={size} height={size}>
        {props.data.map((d, i) => {
          const frac = d.amount / total;
          const dash = `${frac * C} ${C}`;
          const el = (
            <Circle
              key={d.label + i}
              cx={size / 2} cy={size / 2} r={r}
              stroke={categoryColor(d.label)}
              strokeWidth={14}
              fill="none"
              strokeDasharray={dash}
              strokeDashoffset={-offset * C}
              strokeLinecap="butt"
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          );
          offset += frac;
          return el;
        })}
      </Svg>
      <View style={{ position: "absolute" }}>
        <Text style={{ color: colors.subtext, fontSize: 10 }}>всего</Text>
      </View>
    </View>
  );
}
