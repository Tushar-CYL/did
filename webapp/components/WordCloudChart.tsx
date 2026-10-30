"use client";
import ReactECharts from "echarts-for-react";
import "echarts-wordcloud"; // registers the "wordCloud" series on the echarts singleton

export interface CloudWord {
  text: string;
  count: number;
  color?: string;
}

// vivid, dark-theme-friendly palette for words that don't carry their own color
const PALETTE = [
  "#ffe600", "#35a4e8", "#57e188", "#ff8a4a", "#9c82d4", "#8ad1ff",
  "#ff6d6d", "#27acaa", "#f3c300", "#7ad1b0", "#c0a3ff", "#ffb02e",
];

export default function WordCloudChart({
  words,
  height = 340,
  max = 60,
}: {
  words: CloudWord[];
  height?: number;
  max?: number;
}) {
  const data = [...words].sort((a, b) => b.count - a.count).slice(0, max);
  const hi = Math.max(1, ...data.map((w) => w.count));

  const option = {
    tooltip: {
      show: true,
      formatter: (p: any) => `${p.name} — <b>${p.value}</b> role${p.value === 1 ? "" : "s"}`,
    },
    series: [{
      type: "wordCloud",
      shape: "circle",
      left: "center", top: "center", width: "98%", height: "96%",
      sizeRange: [13, 52],
      rotationRange: [-90, 90],
      rotationStep: 90,
      gridSize: 7,
      drawOutOfBound: false,
      shrinkToFit: true,
      layoutAnimation: true,
      textStyle: {
        fontFamily: "Segoe UI, Arial, sans-serif",
        fontWeight: "bold",
      },
      emphasis: { textStyle: { textShadowBlur: 6, textShadowColor: "rgba(255,255,255,.35)" } },
      data: data.map((w, i) => ({
        name: w.text,
        value: w.count,
        textStyle: {
          // bigger words brighter; use the word's practice color when provided
          color: w.color || PALETTE[i % PALETTE.length],
          opacity: 0.6 + 0.4 * (w.count / hi),
        },
      })),
    }],
  };

  return (
    <ReactECharts option={option} style={{ height, width: "100%" }} opts={{ renderer: "canvas" }} notMerge />
  );
}
