import React, { useState, useEffect, useMemo, useRef } from "react";
import { apiGet, apiPost } from "../lib/authApi";
import { InteractiveChart } from "./InteractiveChart";

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
  const schemaCacheRef = useRef<{ data: any; at: number } | null>(null);
  const SCHEMA_CACHE_MS = 10 * 60 * 1000;

  useEffect(() => {
    let cancelled = false;
    const now = Date.now();
    const cached = schemaCacheRef.current;
    if (cached && now - cached.at < SCHEMA_CACHE_MS) {
      setSchema(cached.data);
      return;
    }
    const fastTimer = setTimeout(() => {
      if (!cancelled && !schema) {
        setError("数据库结构加载超时，请确认后端已启动（端口 8002）");
      }
    }, 4000);
    apiGet("/api/schema")
      .then((d) => {
        clearTimeout(fastTimer);
        schemaCacheRef.current = { data: d, at: Date.now() };
        if (!cancelled) setSchema(d);
      })
      .catch((e) => {
        clearTimeout(fastTimer);
        if (!cancelled) setError(e.message || "加载数据库结构失败");
      });
    return () => { cancelled = true; clearTimeout(fastTimer); };
  }, []);

  const reloadSchema = async () => {
    setError("");
    setSchema(null);
    try {
      const d = await apiGet("/api/schema?refresh=true");
      schemaCacheRef.current = { data: d, at: Date.now() };
      setSchema(d);
    } catch (e: any) {
      setError(e.message || "加载数据库结构失败");
    }
  };

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

  // 判断某列是否是时间维度
  const isDateField = (name: string) => /year|month|day|date|quarter/i.test(name);

  // 可用的图表类型（根据当前选择自动过滤）
  const availableCharts = useMemo(() => {
    const charts: { type: string; label: string; disabled?: boolean; reason?: string }[] = [
      { type: "bar", label: "柱状图" },
      { type: "pie", label: "饼图" },
      { type: "line", label: "折线图" },
    ];
    // 饼图需要 1 维度 + 1 指标
    if (dims.length !== 1 || meas.length !== 1) {
      charts[1].disabled = true;
      charts[1].reason = "饼图需要恰好 1 个维度和 1 个指标";
    }
    // 折线图需要时间维度
    if (!dims.some((d) => isDateField(d))) {
      charts[2].disabled = true;
      charts[2].reason = "折线图需要时间维度（年/月/日）";
    }
    // 自动选择第一个可用的
    if (charts.find((c) => c.type === chartType)?.disabled) {
      const first = charts.find((c) => !c.disabled);
      if (first) setChartType(first.type);
    }
    return charts;
  }, [dims, meas, chartType]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        {/* 左侧：维度 + 指标选择 */}
        <div className="w-64 border-r border-porcelain-200 overflow-y-auto p-4 space-y-6">
          {schema && (
            <>
              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold text-porcelain-600 uppercase tracking-wider">维度</h3>
                  <button onClick={reloadSchema} className="text-[10px] text-porcelain-400 hover:text-kinpaku">刷新结构</button>
                </div>
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
                  {availableCharts.map((c) => (
                    <option key={c.type} value={c.type} disabled={c.disabled}>
                      {c.label}{c.disabled ? `（${c.reason}）` : ""}
                    </option>
                  ))}
                </select>
                {availableCharts.find((c) => c.type === chartType && c.disabled) && (
                  <p className="text-[10px] text-red-500 mt-1">当前选择不支持此图表类型</p>
                )}
              </div>
              <button onClick={handleGenerate} disabled={loading || dims.length === 0 || meas.length === 0}
                className="w-full rounded-md bg-porcelain-900 px-3 py-2 text-xs font-medium text-white hover:bg-porcelain-800 disabled:opacity-50">
                {loading ? "生成中..." : "生成可视化"}
              </button>
            </>
          )}
          {!schema && (
            <div className="space-y-3">
              <p className="text-xs text-porcelain-400">
                {error ? "数据库结构加载失败" : "加载数据库结构..."}
              </p>
              {error && (
                <>
                  <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs leading-5 text-red-600">
                    {error}
                  </div>
                  <button
                    onClick={reloadSchema}
                    className="w-full rounded-md border border-porcelain-200 bg-white px-3 py-2 text-xs font-medium text-porcelain-600 hover:bg-porcelain-100"
                  >
                    重新加载
                  </button>
                </>
              )}
            </div>
          )}
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
