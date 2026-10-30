"use client";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

export default function Echart({
  option,
  height = 220,
  onEvents,
}: {
  option: EChartsOption;
  height?: number;
  // ECharts event name -> handler (e.g. { click: (p) => ... }) for drill-downs
  onEvents?: Record<string, (params: any) => void>;
}) {
  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      opts={{ renderer: "svg" }}
      onEvents={onEvents}
      notMerge
    />
  );
}
