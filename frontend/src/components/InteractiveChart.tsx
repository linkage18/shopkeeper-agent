import React, { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, LineChart, PieChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent, CanvasRenderer]);

function Chart({ chartData }: { chartData: any }) {
  const option = useMemo(() => {
    if (!chartData || !chartData.labels || chartData.labels.length === 0) return null;
    const { chart_type, title, labels, values } = chartData;
    const base = {
      title: { text: title || "", left: "center", textStyle: { fontSize: 14 } },
      tooltip: { trigger: "axis" as const },
      grid: { left: "3%", right: "4%", bottom: "15%", containLabel: true },
      xAxis: { type: "category" as const, data: labels, axisLabel: { rotate: labels.length > 6 ? 45 : 0, fontSize: 11 } },
      yAxis: { type: "value" as const },
      series: [{ data: values, type: chart_type === "pie" ? "bar" : (chart_type as any) || "bar", barMaxWidth: 50 }],
    };
    if (chart_type === "pie") {
      return {
        title: { text: title || "", left: "center", textStyle: { fontSize: 14 } },
        tooltip: { trigger: "item" as const, formatter: "{b}: {c} ({d}%)" },
        series: [{
          type: "pie", radius: ["30%", "55%"], center: ["50%", "55%"],
          data: labels.map((l: string, i: number) => ({ name: l, value: values[i] })),
          emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.5)" } },
          label: { fontSize: 11 },
        }],
      };
    }
    return base;
  }, [chartData]);

  if (!option) return null;
  return <ReactEChartsCore echarts={echarts} option={option} style={{ height: 350 }} notMerge />;
}

export const InteractiveChart = React.memo(Chart);
