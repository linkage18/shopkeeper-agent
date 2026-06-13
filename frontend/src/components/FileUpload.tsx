/**
 * 文件上传组件
 * 拖拽或点击上传 PDF/Word/MD/TXT 到知识库
 * Impeccable 设计
 */
import { FileText, LoaderCircle, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { uploadFile } from "../lib/ragApi";
import { cn } from "../lib/format";

type UploadState = { file_name: string; status: "uploading" | "indexing" | "ready" | "error"; message?: string };

export function FileUpload() {
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = async (file: File) => {
    const name = file.name;
    setUploads((prev) => [...prev, { file_name: name, status: "uploading" }]);
    try {
      const result = await uploadFile(file);
      setUploads((prev) => prev.map((u) => u.file_name === name ? { ...u, status: "ready", message: `${result.result?.sub_chunk_count ?? 0} 个切片` } : u));
    } catch (err) {
      setUploads((prev) => prev.map((u) => u.file_name === name ? { ...u, status: "error", message: String(err) } : u));
    }
  };

  const onDrop = (e: React.DragEvent) => { e.preventDefault(); setDragOver(false); Array.from(e.dataTransfer.files).forEach(handleFile); };
  const onSelect = (e: React.ChangeEvent<HTMLInputElement>) => { Array.from(e.target.files ?? []).forEach(handleFile); e.target.value = ""; };

  return (
    <section className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 transition",
          dragOver ? "border-patina/60 bg-patina/[0.06]" : "border-gray-700 bg-white/[0.04] hover:border-patina/40",
        )}
      >
        <Upload className={cn("h-6 w-6", dragOver ? "text-patina" : "text-gray-500")} aria-hidden="true" />
        <span className="text-sm font-medium text-gray-400">拖拽文件到此处，或点击选择</span>
        <span className="text-xs text-gray-600">支持 PDF、Word、MD、TXT</span>
        <input ref={inputRef} type="file" accept=".md,.txt,.pdf,.docx" multiple className="hidden" onChange={onSelect} />
      </div>

      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((u) => (
            <div key={u.file_name} className="flex items-center gap-3 rounded border border-gray-700 bg-white/[0.06] px-3 py-2.5">
              {u.status === "ready" ? (
                <FileText className="h-4 w-4 shrink-0 text-patina" aria-hidden="true" />
              ) : u.status === "error" ? (
                <X className="h-4 w-4 shrink-0 text-red-400" aria-hidden="true" />
              ) : (
                <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-kinpaku" aria-hidden="true" />
              )}
              <span className="min-w-0 flex-1 truncate text-sm text-gray-300">{u.file_name}</span>
              <span className={cn("shrink-0 text-xs", u.status === "ready" ? "text-patina" : u.status === "error" ? "text-red-400" : "text-gray-500")}>
                {u.status === "uploading" ? "上传中..." : u.status === "indexing" ? "索引中..." : u.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
