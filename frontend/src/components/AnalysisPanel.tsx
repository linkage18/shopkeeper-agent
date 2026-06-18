import React, { useState, useEffect, useMemo } from "react";
import { apiGet, apiPost } from "../lib/authApi";
import { InteractiveChart } from "./InteractiveChart";

interface Template {
  id: string; name: string; label: string; description: string;
  params: { name: string; label: string; type: string; options?: string[]; default?: any }[];
}

/* 将后端返回的结果数据渲染为 HTML 表格 */
const DataTable = React.memo(function DataTable({ rows }: { rows: Record<string, any>[] }) {
  if (!rows || rows.length === 0) return <p className="text-xs text-porcelain-400 py-4">无数据</p>;
  const headers = Object.keys(rows[0]);
  return (
    <div className="overflow-x-auto mb-4 rounded-lg border border-porcelain-200">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-porcelain-100">
            {headers.map((h) => (
              <th key={h} className="border border-porcelain-200 px-3 py-2 text-left font-semibold text-porcelain-700 whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rIdx) => (
            <tr key={rIdx} className={rIdx % 2 === 0 ? "bg-white" : "bg-porcelain-50"}>
              {headers.map((h) => (
                <td key={h} className="border border-porcelain-200 px-3 py-1.5 text-porcelain-600 whitespace-nowrap">
                  {row[h] !== null && row[h] !== undefined ? String(row[h]) : ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});

const ReportContent = React.memo(function ReportContent({
  report, chartData, results
}: {
  report: string; chartData?: any; results?: Record<string, any>;
}) {
  const overview = useMemo(() => {
    if (!report) return null;
    return report.split("\n").filter(l => l.startsWith("#") || l.startsWith(">") || l.startsWith("**")).join("\n");
  }, [report]);

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {chartData && (
        <div className="mb-4 rounded-lg border border-porcelain-200 bg-white p-2">
          <InteractiveChart chartData={chartData} />
        </div>
      )}
      {overview && <div className="text-xs text-porcelain-500 mb-4 whitespace-pre-wrap">{overview}</div>}
      {results && Object.entries(results).map(([key, val]) => {
        if (key.endsWith("_error")) {
          return <div key={key} className="mb-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">{String(val)}</div>;
        }
        if (key === "total" && Array.isArray(val) && val.length > 0) {
          return <div key={key} className="mb-2 text-sm font-semibold text-porcelain-700">总计：{String(val[0]?.total ?? "")}</div>;
        }
        if (Array.isArray(val)) {
          return <div key={key} className="mb-2"><div className="text-xs font-semibold text-porcelain-600 mb-1">{key}</div><DataTable rows={val} /></div>;
        }
        return null;
      })}
      {!results && <div className="flex h-full items-center justify-center text-xs text-porcelain-400">选择模板并运行分析</div>}
    </div>
  );
});

const TemplateList = React.memo(function TemplateList({ templates, selected, onSelect }: {
  templates: Template[]; selected: string; onSelect: (id: string) => void;
}) {
  return (
    <div className="w-56 border-r border-porcelain-200 overflow-y-auto p-3 space-y-1">
      {templates.map((t) => (
        <button key={t.id} onClick={() => onSelect(t.id)}
          className={`block w-full rounded-md px-3 py-2 text-left text-xs transition ${selected === t.id ? "bg-porcelain-900 text-white" : "text-porcelain-600 hover:bg-porcelain-100"}`}>
          <div className="font-medium">{t.label}</div>
          <div className="mt-0.5 opacity-60">{t.description}</div>
        </button>
      ))}
    </div>
  );
});

const ParamForm = React.memo(function ParamForm({ tmpl, params, onParamChange, onRun, loading }: {
  tmpl: Template; params: Record<string, any>; onParamChange: (n: string, v: any) => void; onRun: () => void; loading: boolean;
}) {
  return (
    <div className="border-b border-porcelain-200 bg-porcelain-50/50 px-4 py-3 space-y-2">
      <div className="flex flex-wrap gap-3">
        {tmpl.params.map((p) => (
          <div key={p.name} className="flex items-center gap-2">
            <label className="text-xs font-medium text-porcelain-600 whitespace-nowrap">{p.label}</label>
            {p.type === "select" ? (
              <select value={params[p.name] ?? p.default ?? ""} onChange={(e) => onParamChange(p.name, e.target.value)}
                className="rounded-md border border-porcelain-300 bg-white px-2 py-1 text-xs outline-none focus:border-kinpaku">
                {(p.options || []).map((opt) => <option key={opt} value={opt}>{opt}</option>)}
              </select>
            ) : (
              <input type="text" value={params[p.name] ?? p.default ?? ""} onChange={(e) => onParamChange(p.name, e.target.value)}
                className="w-24 rounded-md border border-porcelain-300 bg-white px-2 py-1 text-xs outline-none focus:border-kinpaku" />
            )}
          </div>
        ))}
      </div>
      <button onClick={onRun} disabled={loading}
        className="rounded-md bg-porcelain-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-porcelain-800 disabled:opacity-50">
        {loading ? "分析中..." : "运行分析"}
      </button>
    </div>
  );
});

export const AnalysisPanel = React.memo(function AnalysisPanel({ onBack }: { onBack?: () => void }) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [params, setParams] = useState<Record<string, any>>({});
  const [report, setReport] = useState<string>("");
  const [chartData, setChartData] = useState<any>(null);
  const [results, setResults] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet("/api/reports/templates").then((d) => setTemplates(d.templates || [])).catch(() => {});
  }, []);

  const tmpl = templates.find((t) => t.id === selected);
  const handleParamChange = (name: string, value: any) => setParams((p) => ({ ...p, [name]: value }));

  const handleSelect = (id: string) => { setSelected(id); setParams({}); setReport(""); setChartData(null); setResults(null); };

  const handleRun = async () => {
    if (!selected) return;
    setLoading(true); setReport(""); setChartData(null); setResults(null);
    try {
      const fullParams = { ...params };
      if (tmpl) for (const p of tmpl.params) {
        if (fullParams[p.name] === undefined && p.default !== undefined) fullParams[p.name] = p.default;
      }
      const data = await apiPost("/api/reports/analyze", { template_id: selected, params: fullParams });
      setReport(data.report_md || "");
      setResults(data.results || null);
      if (data.chart_data) setChartData(data.chart_data);
    } catch (e: any) { setReport("错误：" + e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        <TemplateList templates={templates} selected={selected} onSelect={handleSelect} />
        <div className="flex flex-1 flex-col min-w-0">
          {tmpl && <ParamForm tmpl={tmpl} params={params} onParamChange={handleParamChange} onRun={handleRun} loading={loading} />}
          <ReportContent report={report} chartData={chartData} results={results} />
        </div>
      </div>
    </div>
  );
});
