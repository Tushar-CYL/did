"use client";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

export default function Echart({ option, height = 220 }: { option: EChartsOption; height?: number }) {
  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      opts={{ renderer: "svg" }}
      notMerge
    />
  );
}
