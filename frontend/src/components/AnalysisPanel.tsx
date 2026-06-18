import React, { useState, useEffect, useMemo } from "react";
import { apiGet, apiPost } from "../lib/authApi";
import { InteractiveChart } from "./InteractiveChart";

/* 动态可视化面板 — 从 Schema 自动生成可选维度和指标 */
export const AnalysisPanel = React.memo(function AnalysisPanel({ onBack }: { onBack?: () => void }) {
  const [schema, setSchema] = useState<any>(null);
  const [dims, setDims] = useState<string[]>([]);
  const [meas, setMeas] = useState<string[]>([]);
  const [chartType, setChartType] = useState("bar");
  const [chartData, setChartData] = useState<any>(null);
  const [tableData, setTableData] = useState<any[]>([]);
  const [sql, setSql] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/api/schema").then((d) => setSchema(d)).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    if (dims.length === 0 || meas.length === 0) return;
    setLoading(true); setChartData(null); setTableData([]); setError("");
    try {
      const data = await apiPost("/api/viz/generate", {
        dimensions: dims, measures: meas, chart_type: chartType,
      });
      if (data.error) { setError(data.error); return; }
      if (data.chart_data) setChartData(data.chart_data);
      if (data.table_data) setTableData(data.table_data);
      if (data.sql) setSql(data.sql);
    } catch (e: any) { setError(e.message || "生成失败"); }
    finally { setLoading(false); }
  };

  const toggleDim = (col: string) => setDims((p) => p.includes(col) ? p.filter((d) => d !== col) : [...p, col]);
  const toggleMea = (col: string) => setMeas((p) => p.includes(col) ? p.filter((d) => d !== col) : [...p, col]);

  // 自动推荐图表类型
  const recommendedChart = useMemo(() => {
    if (dims.length === 1 && meas.length === 1) {
      return "bar";
    }
    return chartType;
  }, [dims, meas, chartType]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        {/* 左侧：维度 + 指标选择 */}
        <div className="w-64 border-r border-porcelain-200 overflow-y-auto p-4 space-y-6">
          {schema && (
            <>
              <div>
                <h3 className="text-xs font-semibold text-porcelain-600 uppercase tracking-wider mb-2">维度</h3>
                <div className="space-y-1">
                  {schema.dimensions?.map((d: any) => (
                    <label key={`${d.table}.${d.column}`} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={dims.includes(d.column)}
                        onChange={() => toggleDim(d.column)}
                        className="rounded border-porcelain-300 text-kinpaku focus:ring-kinpaku" />
                      <span className="text-xs text-porcelain-700">{d.column}</span>
                      <span className="text-[10px] text-porcelain-400">{d.table}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-xs font-semibold text-porcelain-600 uppercase tracking-wider mb-2">指标</h3>
                <div className="space-y-1">
                  {schema.measures?.map((m: any) => (
                    <label key={`${m.table}.${m.column}`} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={meas.includes(m.column)}
                        onChange={() => toggleMea(m.column)}
                        className="rounded border-porcelain-300 text-kinpaku focus:ring-kinpaku" />
                      <span className="text-xs text-porcelain-700">{m.column}</span>
                      <span className="text-[10px] text-porcelain-400">{m.table}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-xs font-semibold text-porcelain-600 uppercase tracking-wider mb-2">图表类型</h3>
                <select value={chartType} onChange={(e) => setChartType(e.target.value)}
                  className="w-full rounded-md border border-porcelain-300 bg-white px-2 py-1.5 text-xs outline-none focus:border-kinpaku">
                  <option value="bar">柱状图 (推荐)</option>
                  <option value="line">折线图</option>
                  <option value="pie">饼图</option>
                </select>
                {recommendedChart !== chartType && (
                  <p className="text-[10px] text-kinpaku mt-1">推荐使用柱状图</p>
                )}
              </div>
              <button onClick={handleGenerate} disabled={loading || dims.length === 0 || meas.length === 0}
                className="w-full rounded-md bg-porcelain-900 px-3 py-2 text-xs font-medium text-white hover:bg-porcelain-800 disabled:opacity-50">
                {loading ? "生成中..." : "生成可视化"}
              </button>
            </>
          )}
          {!schema && <p className="text-xs text-porcelain-400">加载数据库结构...</p>}
        </div>

        {/* 右侧：图表 + 数据 */}
        <div className="flex-1 flex flex-col min-w-0">
          {chartData && (
            <div className="border-b border-porcelain-200 p-4">
              <div className="rounded-lg border border-porcelain-200 bg-white p-2">
                <InteractiveChart chartData={chartData} />
              </div>
            </div>
          )}
          {error && (
            <div className="p-4">
              <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">{error}</div>
            </div>
          )}
          <div className="flex-1 overflow-y-auto p-4">
            {tableData.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-porcelain-200">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="bg-porcelain-100">
                      {Object.keys(tableData[0]).map((h) => (
                        <th key={h} className="border border-porcelain-200 px-3 py-2 text-left font-semibold text-porcelain-700 whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.map((row, rIdx) => (
                      <tr key={rIdx} className={rIdx % 2 === 0 ? "bg-white" : "bg-porcelain-50"}>
                        {Object.keys(tableData[0]).map((h) => (
                          <td key={h} className="border border-porcelain-200 px-3 py-1.5 text-porcelain-600 whitespace-nowrap">
                            {row[h] !== null && row[h] !== undefined ? String(row[h]) : ""}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {!chartData && !tableData.length && !error && (
              <div className="flex h-full items-center justify-center text-xs text-porcelain-400">
                {loading ? "生成中..." : "选择维度和指标后生成可视化"}
              </div>
            )}
            {sql && (
              <details className="mt-4">
                <summary className="cursor-pointer text-xs text-porcelain-400 hover:text-porcelain-600">查看 SQL</summary>
                <pre className="mt-2 rounded bg-porcelain-50 p-3 text-xs text-porcelain-600 overflow-x-auto">{sql}</pre>
              </details>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});
