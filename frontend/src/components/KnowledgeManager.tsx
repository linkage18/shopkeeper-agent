import { BookOpen, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { apiGet, apiPost, apiDelete, getUser } from "../lib/authApi";

export function KnowledgeManager() {
  const [items, setItems] = useState<any[]>([]);
  const [showEditor, setShowEditor] = useState(false);
  const [title, setTitle] = useState("");
  const [definition, setDefinition] = useState("");
  const user = getUser();
  const isAdmin = user?.role === "admin";

  const load = async () => {
    try {
      const data = await apiGet("/api/knowledge/list");
      setItems(data.items || []);
    } catch { }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    try {
      await apiPost("/api/knowledge/save", {
        title,
        definition,
        tables: [],
        example_sql: "",
        tags: [],
        scope: "shared",
      });
      setShowEditor(false);
      setTitle("");
      setDefinition("");
      load();
    } catch (e: any) { alert(e.message); }
  };

  const handleDelete = async (t: string) => {
    if (!confirm(`删除"${t}"？`)) return;
    try {
      await apiDelete(`/api/knowledge/delete/${encodeURIComponent(t)}`, { scope: "shared" });
      load();
    } catch (e: any) { alert(e.message); }
  };

  if (!isAdmin) return null;

  return (
    <div className="border-t border-porcelain-200 px-3 py-2">
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-medium text-porcelain-600">
          <BookOpen className="h-3.5 w-3.5" /> 知识管理
        </div>
        <button onClick={() => setShowEditor(true)} className="rounded p-0.5 text-porcelain-600 hover:text-kinpaku">
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="max-h-32 space-y-0.5 overflow-y-auto">
        {items.filter((i) => i.scope === "shared").map((item) => (
          <div key={item.id} className="group flex items-center justify-between rounded px-1.5 py-0.5 text-xs text-porcelain-600 hover:bg-porcelain-100">
            <span className="truncate">{item.title}</span>
            <button onClick={() => handleDelete(item.id)} className="hidden p-0.5 text-porcelain-600 hover:text-red-500 group-hover:block">
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-lg border border-porcelain-200 bg-white p-6 shadow-elevated">
            <h3 className="mb-4 text-base font-medium text-porcelain-900">新增知识</h3>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-porcelain-600">标题</label>
                <input value={title} onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded-md border border-porcelain-300 px-3 py-2 text-sm outline-none focus:border-kinpaku" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-porcelain-600">定义</label>
                <textarea value={definition} onChange={(e) => setDefinition(e.target.value)} rows={4}
                  className="w-full rounded-md border border-porcelain-300 px-3 py-2 text-sm outline-none focus:border-kinpaku" />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowEditor(false)}
                className="rounded-md border border-porcelain-300 px-4 py-1.5 text-sm text-porcelain-600 hover:bg-porcelain-50">取消</button>
              <button onClick={handleSave}
                className="rounded-md bg-porcelain-900 px-4 py-1.5 text-sm text-white hover:bg-porcelain-800">保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
