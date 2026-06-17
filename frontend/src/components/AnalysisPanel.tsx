import { useState, useEffect } from "react";
import { apiGet, apiPost, getUser } from "../lib/authApi";

interface Template {
  id: string; name: string; label: string; description: string;
  params: { name: string; label: string; type: string; options?: string[]; default?: any }[];
}

export function AnalysisPanel() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [params, setParams] = useState<Record<string, any>>({});
  const [report, setReport] = useState<string>("");
  const [chart, setChart] = useState<string>("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet("/api/reports/templates").then((d) => setTemplates(d.templates || [])).catch(() => {});
  }, []);

  const tmpl = templates.find((t) => t.id === selected);
  const user = getUser();
  const isAdmin = user?.role === "admin";

  const handleParamChange = (name: string, value: any) => {
    setParams((p) => ({ ...p, [name]: value }));
  };

  const handleRun = async () => {
    if (!selected) return;
    setLoading(true);
    setReport("");
    setChart("");
    try {
      // 先把模板默认参数填上
      const fullParams = { ...params };
      if (tmpl) {
        for (const p of tmpl.params) {
          if (fullParams[p.name] === undefined && p.default !== undefined) {
            fullParams[p.name] = p.default;
          }
        }
      }
      const data = await apiPost("/api/reports/analyze", { template_id: selected, params: fullParams });
      setReport(data.report_md || "");
      if (data.chart_b64) setChart(`data:image/png;base64,${data.chart_b64}`);
    } catch (e: any) {
      setReport(`错误：${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-porcelain-200 bg-white px-4 py-3">
        <h2 className="text-sm font-semibold text-porcelain-900">深度分析</h2>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* 左侧模板列表 */}
        <div className="w-56 border-r border-porcelain-200 overflow-y-auto p-3 space-y-1">
          {templates.map((t) => (
            <button
              key={t.id}
              onClick={() => { setSelected(t.id); setParams({}); setReport(""); setChart(""); }}
              className={`block w-full rounded-md px-3 py-2 text-left text-xs transition ${
                selected === t.id ? "bg-porcelain-900 text-white" : "text-porcelain-600 hover:bg-porcelain-100"
              }`}
            >
              <div className="font-medium">{t.label}</div>
              <div className="mt-0.5 opacity-60">{t.description}</div>
            </button>
          ))}
        </div>

        {/* 右侧参数 + 报告 */}
        <div className="flex flex-1 flex-col min-w-0">
          {tmpl && (
            <div className="border-b border-porcelain-200 bg-porcelain-50/50 px-4 py-3 space-y-2">
              <div className="flex flex-wrap gap-3">
                {tmpl.params.map((p) => (
                  <div key={p.name} className="flex items-center gap-2">
                    <label className="text-xs font-medium text-porcelain-600 whitespace-nowrap">{p.label}</label>
                    {p.type === "select" ? (
                      <select
                        value={params[p.name] ?? p.default ?? ""}
                        onChange={(e) => handleParamChange(p.name, e.target.value)}
                        className="rounded-md border border-porcelain-300 bg-white px-2 py-1 text-xs outline-none focus:border-kinpaku"
                      >
                        {(p.options || []).map((opt: string) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={params[p.name] ?? p.default ?? ""}
                        onChange={(e) => handleParamChange(p.name, e.target.value)}
                        className="w-24 rounded-md border border-porcelain-300 bg-white px-2 py-1 text-xs outline-none focus:border-kinpaku"
                      />
                    )}
                  </div>
                ))}
              </div>
              <button
                onClick={handleRun}
                disabled={loading}
                className="rounded-md bg-porcelain-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-porcelain-800 disabled:opacity-50"
              >
                {loading ? "分析中..." : "运行分析"}
              </button>
            </div>
          )}

          {/* 报告展示 */}
          <div className="flex-1 overflow-y-auto p-4">
            {chart && <img src={chart} alt="chart" className="mb-4 max-w-full rounded-lg border border-porcelain-200" />}
            {report ? (
              <div className="prose prose-sm max-w-none text-porcelain-700">
                {report.split("\n").map((line, i) => {
                  if (line.startsWith("# ")) return <h1 key={i} className="text-lg font-semibold text-porcelain-900 mt-4 mb-2">{line.slice(2)}</h1>;
                  if (line.startsWith("## ")) return <h2 key={i} className="text-base font-semibold text-porcelain-800 mt-3 mb-1">{line.slice(3)}</h2>;
                  if (line.startsWith("| ")) return <div key={i} className="font-mono text-xs text-porcelain-600">{line}</div>;
                  if (line.startsWith("> ")) return <blockquote key={i} className="border-l-2 border-porcelain-300 pl-3 text-xs text-porcelain-500 my-1">{line.slice(2)}</blockquote>;
                  if (line.trim()) return <p key={i} className="text-xs text-porcelain-600 my-1">{line}</p>;
                  return <br key={i} />;
                })}
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-porcelain-400">
                选择模板并运行分析
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
