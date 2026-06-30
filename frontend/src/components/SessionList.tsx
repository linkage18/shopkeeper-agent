/**
 * 会话列表组件
 * 显示当前和历史对话，支持切换、删除、新建
 * Impeccable 设计 — 金箔金/铜绿/暖黑漆器
 */
import React from "react";
import { MessageSquarePlus, MessageSquare, Trash2 } from "lucide-react";
import { cn } from "../lib/format";
import type { SessionListItem } from "../types/agent";

type SessionListProps = {
  sessions: SessionListItem[];
  currentId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
};

export function SessionList({ sessions, currentId, onSelect, onNew, onDelete }: SessionListProps) {
  return (
    <section className="space-y-3">
      <button
        type="button"
        onClick={onNew}
        className={cn(
          "flex h-10 w-full items-center justify-center gap-2 border text-sm font-semibold transition",
          currentId === "new"
            ? "border-kinpaku/60 bg-kinpaku/[0.10] text-kinpaku"
            : "border-gray-700 bg-white/[0.06] text-gray-400 hover:border-patina/40 hover:bg-white/[0.10]",
        )}
      >
        <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
        新对话
      </button>

      {sessions.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
            历史对话
          </div>
          <div className="space-y-1.5">
            {sessions.map((s) => (
              <SessionRow key={s.id} session={s} isActive={currentId === s.id} onSelect={() => onSelect(s.id)} onDelete={() => onDelete(s.id)} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

const SessionRow = React.memo(function SessionRow({ session, isActive, onSelect, onDelete }: {
  session: SessionListItem; isActive: boolean; onSelect: () => void; onDelete: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); } }}
      className={cn(
        "group flex cursor-pointer items-center border-l-2 px-3 py-2.5 text-left transition",
        isActive
          ? "border-kinpaku bg-kinpaku/[0.08]"
          : "border-transparent bg-white/[0.04] hover:border-patina/30 hover:bg-white/[0.08]",
      )}
      onClick={onSelect}
    >
      <div className="min-w-0 flex-1">
        <div className={cn("truncate text-sm font-medium", isActive ? "text-gray-100" : "text-gray-400")}>
          {session.first_query || "（空）"}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <span>{session.query_count} 轮</span>
          {session.query_count > 0 && <span>{Math.round((Date.now() / 1000 - session.created_at) / 60)} 分钟前</span>}
        </div>
        {session.summary && (
          <div className="mt-0.5 truncate text-[11px] italic text-gray-600">
            {session.summary.replace(/^- /, "").slice(0, 50)}
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="shrink-0 rounded-full p-1.5 text-gray-600 opacity-0 transition hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"
        title="删除" aria-label="删除"
      >
        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  );
});
