/**
 * 聊天消息气泡组件
 * 组合展示用户问题、智能体回复、执行流程和结果表格/来源卡片
 * 支持 NL2SQL（result+表格）和 RAG（answer+sources）两种模式
 * [N] 引用标记可点击，滚动定位到对应来源卡片并高亮展开
 */
import { Bot, Copy, UserRound } from "lucide-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { InteractiveChart } from "./InteractiveChart";
import { ResultTable } from "./ResultTable";
import { SourceList } from "./SourceCard";
import { StepRail } from "./StepRail";
import { cn, formatTime, toClipboardText } from "../lib/format";
import type { ChatMessage } from "../types/agent";

function renderContent(text: string, onCite: (i: number) => void) {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, idx) => {
    const match = part.match(/\[(\d+)\]/);
    if (match) {
      const i = parseInt(match[1]) - 1;
      return (
        <a key={idx} href={`#source-${i}`} onClick={(e) => { e.preventDefault(); onCite(i); }}
          className="text-patina underline decoration-patina/30 hover:decoration-patina font-semibold cursor-pointer">
          {part}
        </a>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

export const MessageBubble = React.memo(function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const [chartIndex, setChartIndex] = useState(0);
  const result = message.result as any;
  const tableData = result && typeof result === "object" && Array.isArray(result.rows) && result.rows.length > 0
    ? result.rows
    : (Array.isArray(message.result) ? message.result : null);
  const bubbleRef = useRef<HTMLDivElement>(null);
  const chartWrapRef = useRef<HTMLDivElement>(null);

  // Entrance animation for new messages
  useEffect(() => {
    if (bubbleRef.current) {
      gsap.from(bubbleRef.current, { opacity: 0, y: 24, duration: 0.5, ease: "power2.out" });
    }
  }, []);

  // Animate chart container on chart switch
  useEffect(() => {
    if (chartWrapRef.current) {
      gsap.from(chartWrapRef.current, { opacity: 0, scale: 0.97, duration: 0.35, ease: "power1.out" });
    }
  }, [chartIndex]);

  const scrollToSource = useCallback((i: number) => {
    setActiveSource(i);
    document.getElementById(`source-${i}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    setTimeout(() => setActiveSource(null), 2000);
  }, []);

  const copy = async () => {
    const text = message.result ? toClipboardText(message.result) : message.content;
    await navigator.clipboard.writeText(text);
  };

  return (
    <article ref={bubbleRef} className={cn("group flex gap-3", isUser && "justify-end")}>
      {!isUser && (
        <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-lacquer text-white">
          <Bot className="h-4 w-4" aria-hidden="true" />
        </div>
      )}

      <div className={cn("max-w-[920px] flex-1", isUser && "flex max-w-[760px] justify-end")}>
        <div className={cn(
            "relative border px-5 py-4 shadow-subtle",
            isUser
              ? "border-lacquer/80 bg-lacquer text-white"
              : "border-gray-200 bg-white text-gray-900",
          )}>
          <div className="flex items-start justify-between gap-3">
            <p className="whitespace-pre-wrap text-[15px] leading-7">
              {!isUser && message.sources?.length
                ? renderContent(message.content, scrollToSource)
                : message.content}
            </p>
            {!isUser && message.status !== "streaming" && (
              <button type="button" onClick={copy}
                className="shrink-0 rounded-full p-1.5 text-gray-400 opacity-0 outline-none transition hover:bg-gray-100 hover:text-gray-600 focus:opacity-100 focus:ring-2 focus:ring-patina/40 group-hover:opacity-100"
                title="复制" aria-label="复制">
                <Copy className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>

          {message.error && (
            <div className="mt-3 border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-600">
              {message.error}
            </div>
          )}

          {!isUser && <StepRail steps={message.steps} mode={message.tab === "rag" ? "rag" : message.tab === "report" ? "report" : "sql"} />}
          {!isUser && (result?.charts?.length > 0 || result?.chart_data) && (
            <div ref={chartWrapRef} className="mt-3 rounded-lg border border-porcelain-200 bg-white">
              {/* 多图表切换按钮 */}
              {result.charts?.length > 1 && (
                <div className="flex flex-wrap gap-1 border-b border-porcelain-100 px-2 py-1.5">
                  {result.charts.map((c: any, i: number) => (
                    <button
                      key={c.chart_id || i}
                      onClick={() => setChartIndex(i)}
                      className={cn(
                        "rounded px-2 py-1 text-xs font-medium transition",
                        i === chartIndex
                          ? "bg-kinpaku text-white"
                          : "bg-porcelain-100 text-porcelain-600 hover:bg-porcelain-200",
                      )}
                    >
                      {c.chart_name || c.title || `图表 ${i + 1}`}
                    </button>
                  ))}
                </div>
              )}
              <div className="p-2">
                <InteractiveChart chartData={result.charts ? result.charts[chartIndex] : result.chart_data} />
              </div>
            </div>
          )}
          {!isUser && tableData && <ResultTable data={tableData} />}
          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceList sources={message.sources} activeIndex={activeSource} />
          )}

          <div className={cn("mt-3 text-xs", isUser ? "text-white/55" : "text-gray-400")}>
            {formatTime(message.createdAt)}
          </div>
        </div>
      </div>

      {isUser && (
        <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-patina text-white">
          <UserRound className="h-4 w-4" aria-hidden="true" />
        </div>
      )}
    </article>
  );
});
