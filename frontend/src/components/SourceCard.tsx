/**
 * 来源引用卡片组件
 * 展示回答中的文档引用来源，可折叠展开查看原文片段
 * 支持点击跳转高亮（active 控制）
 * Impeccable — 铜绿边框 + 金箔金高亮
 */
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "../lib/format";
import type { SourceRef } from "../types/agent";

export function SourceCard({ source, index, active }: { source: SourceRef; index: number; active: boolean }) {
  const [open, setOpen] = useState(active);
  const isHighScore = source.score >= 0.9;
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (active && ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
      setOpen(true);
    }
  }, [active]);

  return (
    <div
      id={`source-${index}`}
      ref={ref}
      className={cn(
        "rounded-r-md border-l-2 px-3 py-2 transition",
        active && "ring-2 ring-kinpaku/50 bg-kinpaku/[0.06]",
        !active && isHighScore ? "border-kinpaku/50 bg-kinpaku/[0.03]" : "border-patina/40 bg-white/60",
      )}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 text-left"
      >
        <span className="grid h-5 w-5 shrink-0 place-items-center rounded bg-gray-200 text-[11px] font-bold text-gray-600">
          {index + 1}
        </span>
        <FileText className={cn("h-3.5 w-3.5 shrink-0", isHighScore ? "text-kinpaku" : "text-patina")} aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate text-xs font-medium text-gray-800">{source.file_name}</span>
        <span className="shrink-0 text-[11px] text-gray-500">P{source.page_number}</span>
        <span className={cn(
          "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
          isHighScore ? "bg-kinpaku/15 text-kinpaku" : "bg-gray-100 text-gray-500",
        )}>
          {source.score.toFixed(2)}
        </span>
        {open ? <ChevronUp className="h-3 w-3 shrink-0 text-gray-300" /> : <ChevronDown className="h-3 w-3 shrink-0 text-gray-300" />}
      </button>
      {open && (
        <p className="mt-2 border-t border-gray-100 pt-2 text-[13px] leading-6 text-gray-700">
          {source.snippet}
        </p>
      )}
    </div>
  );
}

export function SourceList({ sources, activeIndex }: { sources: SourceRef[]; activeIndex: number | null }) {
  if (!sources || sources.length === 0) return null;
  return (
    <section className="mt-4 space-y-2">
      <div className="text-xs font-semibold uppercase tracking-[0.1em] text-gray-500">来源引用</div>
      <div className="space-y-1.5">
        {sources.map((s, i) => (
          <SourceCard key={`${s.file_name}-${s.page_number}-${i}`} source={s} index={i} active={activeIndex === i} />
        ))}
      </div>
    </section>
  );
}
