import React, { useState, useEffect, useMemo } from "react";
import { apiGet, apiPost } from "../lib/authApi";
import { InteractiveChart } from "./InteractiveChart";

interface Template {
  id: string; name: string; label: string; description: string;
  params: { name: string; label: string; type: string; options?: string[]; default?: any }[];
}

/* 将 markdown 管道表格行解析为二维数组 */
function parseTableLines(lines: string[]): { headers: string[]; rows: string[][] } | null {
  // 过滤出连续的表格行
  const tableLines = lines.filter(l => l.startsWith("| ") && l.endsWith("|"));
  if (tableLines.length < 3) return null; // 至少需要表头 + 分隔线 + 一行数据
  const headerRow = tableLines[0].split("|").filter(c => c.trim()).map(c => c.trim());
  const dataRows: string[][] = [];
  for (let i = 2; i < tableLines.length; i++) { // 跳过第1行(表头)和第2行(分隔线)
    const cells = tableLines[i].split("|").filter(c => c.trim()).map(c => c.trim());
    if (cells.length === headerRow.length) dataRows.push(cells);
  }
  if (dataRows.length === 0) return null;
  return { headers: headerRow, rows: dataRows };
}

const ReportContent = React.memo(function ReportContent({ report, chartData }: { report: string; chartData?: any }) {
  const rendered = useMemo(() => {
    if (!report) return null;
    const lines = report.split("\n");
    const elements: React.ReactNode[] = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      // 检测是否进入表格区域
      if (line.startsWith("| ") && lines[i + 1]?.startsWith("| ---")) {
        // 收集表格行
        const tableLines: string[] = [];
        while (i < lines.length && lines[i].startsWith("| ")) {
          tableLines.push(lines[i]);
          i++;
        }
        const tbl = parseTableLines(tableLines);
        if (tbl) {
          elements.push(
            <div key={`tbl-${elements.length}`} className="overflow-x-auto mb-4 rounded-lg border border-porcelain-200">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-porcelain-100">
                    {tbl.headers.map((h, idx) => (
                      <th key={idx} className="border border-porcelain-200 px-3 py-2 text-left font-semibold text-porcelain-700 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tbl.rows.map((row, rIdx) => (
                    <tr key={rIdx} className={rIdx % 2 === 0 ? "bg-white" : "bg-porcelain-50"}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="border border-porcelain-200 px-3 py-1.5 text-porcelain-600 whitespace-nowrap">{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
          continue;
        }
      }
      // 非表格后处理
      if (line.startsWith("# ")) {
        elements.push(<h1 key={i} className="text-lg font-semibold text-porcelain-900 mt-4 mb-2">{line.slice(2)}</h1>);
      } else if (line.startsWith("## ")) {
        elements.push(<h2 key={i} className="text-base font-semibold text-porcelain-800 mt-3 mb-1">{line.slice(3)}</h2>);
      } else if (line.startsWith("> ")) {
        elements.push(<blockquote key={i} className="border-l-2 border-porcelain-300 pl-3 text-xs text-porcelain-500 my-1">{line.slice(2)}</blockquote>);
      } else if (line.trim()) {
        elements.push(<p key={i} className="text-xs text-porcelain-600 my-1">{line}</p>);
      } else {
        elements.push(<br key={i} />);
      }
      i++;
    }
    return elements;
  }, [report]);
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {chartData && (
        <div className="mb-4 rounded-lg border border-porcelain-200 bg-white p-2">
          <InteractiveChart chartData={chartData} />
        </div>
      )}
      {report ? <div className="text-porcelain-700">{rendered}</div> : (
        <div className="flex h-full items-center justify-center text-xs text-porcelain-400">选择模板并运行分析</div>
      )}
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
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet("/api/reports/templates").then((d) => setTemplates(d.templates || [])).catch(() => {});
  }, []);

  const tmpl = templates.find((t) => t.id === selected);
  const handleParamChange = (name: string, value: any) => setParams((p) => ({ ...p, [name]: value }));

  const handleSelect = (id: string) => { setSelected(id); setParams({}); setReport(""); setChartData(null); };

  const handleRun = async () => {
    if (!selected) return;
    setLoading(true); setReport(""); setChartData(null);
    try {
      const fullParams = { ...params };
      if (tmpl) for (const p of tmpl.params) {
        if (fullParams[p.name] === undefined && p.default !== undefined) fullParams[p.name] = p.default;
      }
      const data = await apiPost("/api/reports/analyze", { template_id: selected, params: fullParams });
      setReport(data.report_md || "");
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
          <ReportContent report={report} chartData={chartData} />
        </div>
      </div>
    </div>
  );
});
