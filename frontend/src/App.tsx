/**
 * 前端应用主组件
 * 支持 NL2SQL（问数）和 RAG（知识库）两个 Tab
 * RAG 支持多 Session 切换与管理
 * 瓷白色设计体系
 */
import {
  Activity, BarChart3, BookOpen, Eraser, History, Leaf,
  LogOut, Server, TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnalysisPanel } from "./components/AnalysisPanel";
import { apiPost } from "./lib/authApi";
import { Composer } from "./components/Composer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { EmptyState } from "./components/EmptyState";
import { FileUpload } from "./components/FileUpload";
import { KnowledgeManager } from "./components/KnowledgeManager";
import { LoginPage } from "./components/LoginPage";
import { MessageBubble } from "./components/MessageBubble";
import { SessionList } from "./components/SessionList";
import { SessionSearch } from "./components/SessionSearch";
import { streamQuery } from "./lib/agentApi";
import { getToken, removeToken, removeUser, setOnUnauthorized, authHeaders } from "./lib/authApi";
import { streamRagQuery, listSessions, getSession, deleteSession } from "./lib/ragApi";
import { cn, summarizeResult } from "./lib/format";
import type { AgentEvent, ChatMessage, SessionListItem, StepState } from "./types/agent";

const SQL_EXAMPLES = [
  "统计 2025 年第一季度各大区的 GMV，并按 GMV 从高到低排序",
  "统计 2025 年 3 月各商品品类的销量和销售额",
  "查询华东地区 2025 年第一季度销售额最高的前 5 个商品",
  "按会员等级统计 2025 年第一季度的订单数和销售额",
];

const CHART_EXAMPLES = [
  "按品牌统计销售额（会自动生成柱状图）",
  "统计各品类月销售额趋势（会自动生成折线图）",
  "统计各地区销售占比（会自动生成饼图）",
  "对比各品类销量和销售额（会自动生成多系列图）",
];

const REPORT_EXAMPLES = [
  "总结Q1各品牌销售情况并出报告",
  "分析各品类销量对比并生成报告",
];

const RAG_EXAMPLES = [
  "项目使用什么技术栈？",
  "服务器如何查看日志？",
  "合同审批流程是怎样的？",
  "销售人员的 KPI 有哪些？",
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "Vite /api proxy";

function makeId() {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function upsertStep(steps: StepState[] = [], event: Extract<AgentEvent, { type: "progress" }>) {
  const next = steps.filter((item) => item.step !== event.step);
  next.push({ step: event.step, status: event.status, updatedAt: Date.now() });
  return next;
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!getToken());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [activeController, setActiveController] = useState<AbortController | null>(null);
  const [activeTab, setActiveTab] = useState<"sql" | "rag" | "analysis">("sql");
  const [tokenUsage, setTokenUsage] = useState<{ total: number; input: number; output: number; calls: number } | null>(null);

  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>("new");
  const [loadingSession, setLoadingSession] = useState(false);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const pendingQueryRef = useRef<string>("");

  const isStreaming = Boolean(activeController);
  const canSubmit = draft.trim().length > 0 && !isStreaming;
  const examples = activeTab === "sql"
    ? [...SQL_EXAMPLES, "---", ...CHART_EXAMPLES, "---", ...REPORT_EXAMPLES]
    : RAG_EXAMPLES;

  const completedCount = useMemo(
    () => messages.filter((m) => m.role === "assistant" && m.status === "done").length,
    [messages],
  );

  const refreshTokenUsage = useCallback(async () => {
    try {
      const usage = await apiGet("/api/token/summary");
      setTokenUsage({
        total: usage.total_tokens ?? 0,
        input: usage.total_input ?? 0,
        output: usage.total_output ?? 0,
        calls: usage.total_calls ?? 0,
      });
    } catch { /* silent */ }
  }, []);

  const handleLogout = () => {
    removeToken();
    removeUser();
    setMessages([]);
    setDraft("");
    setActiveController(null);
    setActiveTab("sql");
    setCurrentSessionId("new");
    setSessions([]);
    setLoggedIn(false);
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // 401 自动登出
  useEffect(() => {
    setOnUnauthorized(() => {
      setMessages([]);
      setSessions([]);
      setLoggedIn(false);
    });
    return () => setOnUnauthorized(null);
  }, []);

  useEffect(() => {
    if (loggedIn) refreshTokenUsage();
  }, [loggedIn, refreshTokenUsage]);

  const refreshSessions = useCallback(async () => {
    try {
      const res = await listSessions();
      setSessions(res.sessions);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    if (activeTab === "rag" || activeTab === "sql") refreshSessions();
  }, [activeTab, refreshSessions]);

  const handleSessionSelect = useCallback(async (id: string) => {
    if (isStreaming || loadingSession) return;
    setLoadingSession(true);
    setCurrentSessionId(id);
    try {
      const detail = await getSession(id);
      const restored: ChatMessage[] = [];
      for (const record of detail.history) {
        restored.push({ id: makeId(), role: "user", content: record.query, createdAt: (record.timestamp || 0) * 1000, tab: "rag" });
        restored.push({ id: makeId(), role: "assistant", content: record.answer, sources: record.sources, createdAt: (record.timestamp || 0) * 1000, status: "done", tab: "rag" });
      }
      setMessages(restored);
    } catch { setMessages([]); }
    finally { setLoadingSession(false); }
  }, [isStreaming, loadingSession]);

  const handleNewSession = useCallback(() => {
    if (isStreaming) return;
    setCurrentSessionId("new");
    setMessages([]);
    setDraft("");
  }, [isStreaming]);

  const handleDeleteSession = useCallback(async (id: string) => {
    try {
      await deleteSession(id);
      if (currentSessionId === id) handleNewSession();
      refreshSessions();
    } catch { /* silent */ }
  }, [currentSessionId, handleNewSession, refreshSessions]);

  const startQuery = async (rawQuery = draft) => {
    const query = rawQuery.trim();
    if (!query) return;
    // 正在流式处理时，加入队列等当前完成后再自动执行
    if (isStreaming) {
      pendingQueryRef.current = query;
      return;
    }
    pendingQueryRef.current = "";

    // ── 意图路由：分类意图决定走哪个管线（LLM 上下文感知） ──
    let pipeline = activeTab as string;
    let reportIntent = false;
    if (activeTab !== "analysis") {
      // 传最近 20 轮对话给 LLM 做上下文感知意图分类
      const recentMessages = messages.slice(-40);
      const historyText = recentMessages
        .map((m) => `${m.role === "user" ? "用户" : "助手"}: ${m.content.slice(0, 100)}`)
        .join("\n");
      try {
        const intentResp = await apiPost("/api/intent/classify", { query, history: historyText });
        if (intentResp.intent === "report") {
          reportIntent = true;
        } else if (intentResp.intent === "sql" || intentResp.intent === "rag") {
          pipeline = intentResp.intent;
        }
      } catch { /* 忽略 */ }
    }

    // 消息 tab 字段用于 StepRail 显示正确流程图
    const msgTab = reportIntent ? "report" : (pipeline as "sql" | "rag");

    const userMessage: ChatMessage = { id: makeId(), role: "user", content: query, createdAt: Date.now(), tab: msgTab };
    const assistantId = makeId();
    const assistantMessage: ChatMessage = { id: assistantId, role: "assistant", content: "正在连接...", createdAt: Date.now(), status: "streaming", steps: [], tab: msgTab };

    const controller = new AbortController();
    setActiveController(controller);
    setDraft("");
    setMessages((cur) => [...cur, userMessage, assistantMessage]);

    const handleEvent = (updater: (m: ChatMessage) => ChatMessage) => {
      setMessages((cur) => cur.map((m) => (m.id !== assistantId ? m : updater(m))));
    };

    try {
      if (reportIntent) {
        // ═══ 报告生成管线 ═══
        const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
        const resp = await fetch(`${API_BASE}/api/report/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ query }),
          signal: controller.signal,
        });
        if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);
        const reader = resp.body!.getReader();
        const decoder = new TextDecoder("utf-8");
        let buf = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const chunks = buf.split("\n\n");
          buf = chunks.pop() ?? "";
          for (const chunk of chunks) {
            const pd = chunk.replace(/^data:\s?/, "").trim();
            if (!pd) continue;
            try {
              const ev = JSON.parse(pd);
              handleEvent((m) => {
                if (ev.type === "progress") {
                  return { ...m, steps: upsertStep(m.steps || [], { type: "progress", step: ev.step, status: ev.status }) };
                }
                if (ev.type === "result") {
                  const result = m.result as any || {};
                  if (ev.report_md) {
                    return { ...m, status: "done" as const, content: ev.report_md, result: { ...result, report_md: ev.report_md } };
                  }
                  if (ev.chart_data) {
                    return { ...m, result: { ...result, chart_data: ev.chart_data } };
                  }
                }
                if (ev.type === "ask_user") {
                  const hints = (ev.suggestions || []).join("\n• ");
                  return {
                    ...m, status: "done" as const,
                    content: `⚠️ ${ev.message}\n\n可能的原因：\n• ${hints}\n\n${ev.detail ? `\n错误详情：${ev.detail}` : ""}\n\n💡 请修改问题后重新提交，例如指定正确的年份或字段名。`,
                    result: { ...(m.result || {}), ask_user: ev },
                  };
                }
                if (ev.type === "error") {
                  return { ...m, status: "error" as const, content: ev.message || "报告生成失败" };
                }
                return m;
              });
            } catch { /* skip */ }
          }
        }
        handleEvent((m) => m.status !== "done" ? { ...m, status: "done" as const } : m);
      } else if (pipeline === "sql") {
        // ═══ NL2SQL 管线 ═══
        let sqlResult: any = null;
        await streamQuery(query, {
          signal: controller.signal,
          onEvent: (event: AgentEvent) => {
            handleEvent((m) => {
              if (event.type === "progress") return { ...m, steps: upsertStep(m.steps, event) };
              if (event.type === "result") {
                sqlResult = event.data;
                return { ...m, status: "done" as const, content: summarizeResult(event.data), result: event.data };
              }
              return { ...m, status: "error" as const, content: "这次查询没有成功。", error: event.message };
            });
          },
        });
        // 保存到后端会话文件（和 RAG 同一套 session 系统）
        if (sqlResult) {
          try {
            await apiPost("/api/session/save", {
              query, answer: JSON.stringify(sqlResult).slice(0, 500),
              summary: `SQL: ${query.slice(0, 40)}`, type: "sql",
            });
            refreshSessions();
          } catch { /* ignore */ }
        }
      } else {
        // ═══ RAG 管线 ═══
        const sid = currentSessionId === "new" ? crypto.randomUUID?.() ?? `${Date.now()}` : currentSessionId;
        if (currentSessionId === "new") setCurrentSessionId(sid);
        await streamRagQuery(query, sid, {
          signal: controller.signal,
          onEvent: (event: any) => {
            handleEvent((m) => {
              if (event.type === "progress") return { ...m, steps: upsertStep(m.steps, event) };
              if (event.type === "result") return { ...m, status: "done" as const, content: event.answer || "（无回答）", sources: event.sources || [] };
              return { ...m, status: "error" as const, content: "这次查询没有成功。", error: event.message };
            });
          },
        });
        refreshSessions();
      }
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === "AbortError";
      setMessages((cur) => cur.map((m) =>
        m.id === assistantId ? { ...m, status: isAbort ? "done" as const : "error" as const, content: isAbort ? "已停止。" : "无法连接接口。", error: isAbort ? undefined : String(error) } : m,
      ));
    } finally {
      setActiveController(null);
      refreshTokenUsage();
      // 如果有待处理查询，自动执行
      const next = pendingQueryRef.current;
      pendingQueryRef.current = "";
      if (next) {
        setDraft(next);
        setTimeout(() => startQuery(next), 100);
      }
    }
  };

  const stopQuery = () => activeController?.abort();
  const clearConversation = () => { if (!isStreaming) { setMessages([]); setDraft(""); } };

  return (
    <>
    {/* 登录页始终渲染，未登录时显示 */}
    <div style={{ display: loggedIn ? "none" : "" }}>
      <LoginPage onLogin={() => { setLoggedIn(true); }} />
    </div>
    {/* 主应用始终渲染，登录后显示 */}
    <div style={{ display: loggedIn ? "" : "none" }} className="h-dvh overflow-hidden bg-porcelain-50 text-porcelain-900">
      <div className="relative grid h-full min-h-0 overflow-hidden lg:grid-cols-[300px_minmax(0,1fr)]">
        {/* 侧边栏 — 瓷白色 */}
        <aside className="hidden min-h-0 border-r border-porcelain-200 bg-white lg:flex lg:flex-col">
          <div className="border-b border-porcelain-200 px-5 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="grid h-9 w-9 place-items-center rounded-lg bg-porcelain-100 text-kinpaku">
                  {activeTab === "sql" ? <BarChart3 className="h-4 w-4" /> : activeTab === "rag" ? <BookOpen className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
                </div>
                <div>
                  <div className="text-sm font-semibold text-porcelain-900">
                    {activeTab === "sql" ? "智能问数" : activeTab === "rag" ? "知识库" : "多维可视化"}
                  </div>
                  <div className="text-xs text-porcelain-400">
                    {activeTab === "sql" ? "NL2SQL" : activeTab === "rag" ? "RAG" : "可视化"}
                  </div>
                </div>
              </div>
              <button onClick={handleLogout} className="rounded p-1 text-porcelain-400 hover:text-porcelain-600" title="退出登录">
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs text-porcelain-500">
              <span className="rounded bg-porcelain-100 px-1.5 py-0.5">已登录</span>
            </div>
          </div>

          {/* Tab 切换 */}
          <div className="flex border-b border-porcelain-200">
            <button
              type="button"
              onClick={() => { setActiveTab("sql"); clearConversation(); }}
              className={cn(
                "flex-1 py-2.5 text-center text-xs font-semibold uppercase tracking-[0.1em] transition",
                activeTab === "sql" ? "border-b-2 border-kinpaku text-kinpaku" : "text-porcelain-400 hover:text-porcelain-600",
              )}
            >
              问数
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab("rag"); clearConversation(); handleNewSession(); }}
              className={cn(
                "flex-1 py-2.5 text-center text-xs font-semibold uppercase tracking-[0.1em] transition",
                activeTab === "rag" ? "border-b-2 border-kinpaku text-kinpaku" : "text-porcelain-400 hover:text-porcelain-600",
              )}
            >
              知识库
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab("analysis"); }}
              className={cn(
                "flex-1 py-2.5 text-center text-xs font-semibold uppercase tracking-[0.1em] transition",
                activeTab === "analysis" ? "border-b-2 border-kinpaku text-kinpaku" : "text-porcelain-400 hover:text-porcelain-600",
              )}
            >
              可视化
            </button>
            {activeTab === "analysis" && (
              <button
                type="button"
                onClick={() => setActiveTab("sql")}
                className="absolute right-3 top-3 rounded p-1 text-porcelain-400 hover:text-porcelain-600"
              >
                ✕
              </button>
            )}
          </div>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-3">
            {activeTab !== "analysis" && (
              <SessionSearch sessions={sessions} onSearch={(q) => {
                if (q) {
                  const found = sessions.find((s) => s.id === q);
                  if (found) handleSessionSelect(found.id);
                }
              }} />
            )}
            {activeTab !== "analysis" && (
              <SessionList sessions={sessions} currentId={currentSessionId} onSelect={handleSessionSelect} onNew={handleNewSession} onDelete={handleDeleteSession} />
            )}
            {activeTab === "rag" && (
              <>
                <FileUpload />
                <KnowledgeManager />
              </>
            )}

            {activeTab === "sql" && (
              <button
                type="button"
                onClick={clearConversation}
                disabled={isStreaming}
                className="flex h-10 w-full items-center justify-center gap-2 rounded-md border border-porcelain-200 bg-white text-sm font-medium text-porcelain-600 transition hover:bg-porcelain-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <History className="h-4 w-4" aria-hidden="true" />
                新查询
              </button>
            )}

            {activeTab !== "analysis" && (
            <section>
              <details className="group" open>
                <summary className="mb-2 flex cursor-pointer items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.12em] text-porcelain-400 hover:text-porcelain-600">
                  <History className="h-3.5 w-3.5" aria-hidden="true" />
                  样例
                  <span className="ml-auto text-[10px] opacity-50 group-open:hidden">展开</span>
                  <span className="ml-auto text-[10px] opacity-50 hidden group-open:inline">收起</span>
                </summary>
                <div className="space-y-1.5">
                  {examples.map((example, idx) =>
                    example === "---" ? (
                      <div key={`sep-${idx}`} className="border-t border-porcelain-200 my-2" />
                    ) : (
                      <button
                        key={example}
                        type="button"
                        disabled={isStreaming || loadingSession}
                        onClick={() => { setDraft(example); }}
                        className="w-full rounded-md border border-porcelain-200 bg-white px-3 py-2.5 text-left text-xs leading-5 text-porcelain-600 transition hover:border-kinpaku/30 hover:bg-porcelain-50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {example}
                      </button>
                    )
                  )}
                </div>
              </details>
            </section>
            )}
          </div>

          <div className="border-t border-porcelain-200 px-4 py-3">
            <div className="grid gap-1 text-xs text-porcelain-400">
              <div className="flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2"><Server className="h-3.5 w-3.5" aria-hidden="true" />API</span>
                <span className="truncate font-mono">{API_BASE_URL}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2"><Activity className="h-3.5 w-3.5" aria-hidden="true" />完成</span>
                <span>{completedCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Token</span>
                <span>{tokenUsage ? `${tokenUsage.total} / ${tokenUsage.calls}次` : "0"}</span>
              </div>
            </div>
          </div>
        </aside>

        {/* 主区域 — 双面板同时渲染，CSS 显隐切换 */}
        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          {/* ═══ 分析面板 ═══ */}
          <div className={activeTab === "analysis" ? "flex flex-col flex-1 min-h-0" : "hidden"}>
            <header className="flex h-14 shrink-0 items-center justify-between border-b border-porcelain-200 bg-white/90 px-4 backdrop-blur lg:px-6">
              <div className="flex items-center gap-3">
                <button onClick={() => setActiveTab("sql")}
                  className="rounded-md border border-porcelain-200 bg-white px-3 py-1.5 text-xs font-medium text-porcelain-600 hover:bg-porcelain-100">
                  ← 返回问数
                </button>
                <div className="text-sm font-semibold text-porcelain-900">多维可视化</div>
              </div>
            </header>
            <div className="flex-1 overflow-hidden">
              <AnalysisPanel onBack={() => setActiveTab("sql")} />
            </div>
          </div>

          {/* ═══ 聊天面板（SQL + RAG）═══ */}
          <div className={activeTab !== "analysis" ? "flex flex-col flex-1 min-h-0" : "hidden"}>
          <header className="flex h-14 shrink-0 items-center justify-between border-b border-porcelain-200 bg-white/90 px-4 backdrop-blur lg:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <div className={cn(
                "grid h-8 w-8 shrink-0 place-items-center rounded-lg text-white lg:hidden",
                activeTab === "sql" ? "bg-porcelain-900" : "bg-porcelain-600",
              )}>
                {activeTab === "sql" ? <BarChart3 className="h-4 w-4" /> : <BookOpen className="h-4 w-4" />}
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-porcelain-900">
                  {activeTab === "sql" ? "智能问数" : "知识库问答"}
                </div>
                <div className="truncate text-xs text-porcelain-400">
                  {activeTab === "sql" ? "NL2SQL / LangGraph" : "RAG / 多路召回 / 溯源"}
                  {currentSessionId !== "new" && " · 会话中"}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={clearConversation}
              disabled={messages.length === 0 || isStreaming}
              className="grid h-8 w-8 place-items-center rounded-full text-porcelain-400 transition hover:bg-porcelain-100 hover:text-porcelain-600 disabled:cursor-not-allowed disabled:opacity-35"
              title="清空" aria-label="清空"
            >
              <Eraser className="h-4 w-4" aria-hidden="true" />
            </button>
          </header>

          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {loadingSession ? (
              <div className="flex h-full items-center justify-center text-sm text-porcelain-400">加载中...</div>
            ) : messages.length === 0 ? (
              <EmptyState examples={examples} onUseExample={(ex) => setDraft(ex)} />
            ) : (
              <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-5 lg:px-8">
                {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
              </div>
            )}
          </div>

          <div className="border-t border-porcelain-200 bg-porcelain-50/80 px-4 py-1.5 text-center text-xs text-porcelain-400">
            <span className="inline-flex items-center gap-2">
              <Leaf className="h-3.5 w-3.5 text-kinpaku/60" aria-hidden="true" />
              {isStreaming ? "运行中" : loadingSession ? "加载中" : "就绪"}
            </span>
          </div>
          <Composer
            value={draft}
            disabled={!canSubmit || loadingSession}
            isStreaming={isStreaming}
            onChange={setDraft}
            onSubmit={() => startQuery()}
            onStop={stopQuery}
          />
          </div>
        </main>
      </div>
    </div>
    </>
  );
}
