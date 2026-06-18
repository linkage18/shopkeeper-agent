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
import { EmptyState } from "./components/EmptyState";
import { FileUpload } from "./components/FileUpload";
import { KnowledgeManager } from "./components/KnowledgeManager";
import { LoginPage } from "./components/LoginPage";
import { MessageBubble } from "./components/MessageBubble";
import { SessionList } from "./components/SessionList";
import { SessionSearch } from "./components/SessionSearch";
import { streamQuery } from "./lib/agentApi";
import { getToken, removeToken, removeUser } from "./lib/authApi";
import { streamRagQuery, listSessions, getSession, deleteSession } from "./lib/ragApi";
import { cn, summarizeResult } from "./lib/format";
import type { AgentEvent, ChatMessage, SessionListItem, StepState } from "./types/agent";

const SQL_EXAMPLES = [
  "统计 2025 年第一季度各大区的 GMV，并按 GMV 从高到低排序",
  "统计 2025 年 3 月各商品品类的销量和销售额",
  "查询华东地区 2025 年第一季度销售额最高的前 5 个商品",
  "按会员等级统计 2025 年第一季度的订单数和销售额",
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

  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>("new");
  const [loadingSession, setLoadingSession] = useState(false);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  const isStreaming = Boolean(activeController);
  const canSubmit = draft.trim().length > 0 && !isStreaming;
  const examples = activeTab === "sql" ? SQL_EXAMPLES : RAG_EXAMPLES;

  const completedCount = useMemo(
    () => messages.filter((m) => m.role === "assistant" && m.status === "done").length,
    [messages],
  );

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

  const refreshSessions = useCallback(async () => {
    try {
      const res = await listSessions();
      setSessions(res.sessions);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    if (activeTab === "rag") refreshSessions();
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
    if (!query || isStreaming) return;

    // 意图路由：自动分类用户输入
    let targetTab = activeTab;
    if (targetTab !== "analysis") {
      try {
        const intentResp = await apiPost("/api/intent/classify", { query });
        targetTab = intentResp.intent || activeTab;
      } catch { /* 分类失败则不切换 */ }
    }

    if (targetTab === "analysis") {
      setActiveTab("analysis");
      setDraft("");
      return;
    }

    setActiveTab(targetTab);
    const tab = targetTab as "sql" | "rag";

    const userMessage: ChatMessage = { id: makeId(), role: "user", content: query, createdAt: Date.now(), tab };
    const assistantId = makeId();
    const assistantMessage: ChatMessage = { id: assistantId, role: "assistant", content: "正在连接...", createdAt: Date.now(), status: "streaming", steps: [], tab };

    const controller = new AbortController();
    setActiveController(controller);
    setDraft("");
    setMessages((cur) => [...cur, userMessage, assistantMessage]);

    try {
      if (tab === "sql") {
        await streamQuery(query, {
          signal: controller.signal,
          onEvent: (event: AgentEvent) => {
            setMessages((cur) => cur.map((m) => {
              if (m.id !== assistantId) return m;
              if (event.type === "progress") return { ...m, content: event.status === "running" ? `正在执行：${event.step}` : m.content, steps: upsertStep(m.steps, event) };
              if (event.type === "result") return { ...m, status: "done" as const, content: summarizeResult(event.data), result: event.data };
              return { ...m, status: "error" as const, content: "这次查询没有成功。", error: event.message };
            }));
          },
        });
      } else {
        const sid = currentSessionId === "new" ? crypto.randomUUID?.() ?? `${Date.now()}` : currentSessionId;
        if (currentSessionId === "new") setCurrentSessionId(sid);
        await streamRagQuery(query, sid, {
          signal: controller.signal,
          onEvent: (event: any) => {
            setMessages((cur) => cur.map((m) => {
              if (m.id !== assistantId) return m;
              if (event.type === "progress") return { ...m, content: event.status === "running" ? `正在执行：${event.step}` : m.content, steps: upsertStep(m.steps, event) };
              if (event.type === "result") return { ...m, status: "done" as const, content: event.answer || "（无回答）", sources: event.sources || [] };
              return { ...m, status: "error" as const, content: "这次查询没有成功。", error: event.message };
            }));
          },
        });
        refreshSessions();
      }
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === "AbortError";
      setMessages((cur) => cur.map((m) =>
        m.id === assistantId ? { ...m, status: isAbort ? "done" as const : "error" as const, content: isAbort ? "已停止。" : "无法连接接口。", error: isAbort ? undefined : String(error) } : m,
      ));
    } finally { setActiveController(null); }
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
                    {activeTab === "sql" ? "智能问数" : activeTab === "rag" ? "知识库" : "深度分析"}
                  </div>
                  <div className="text-xs text-porcelain-400">
                    {activeTab === "sql" ? "NL2SQL" : activeTab === "rag" ? "RAG" : "报告"}
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
              分析
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
            {activeTab === "rag" && (
              <SessionSearch sessions={sessions} onSearch={(q) => {
                if (q) {
                  const found = sessions.find((s) => s.id === q);
                  if (found) handleSessionSelect(found.id);
                }
              }} />
            )}
            {activeTab === "rag" && (
              <>
                <SessionList sessions={sessions} currentId={currentSessionId} onSelect={handleSessionSelect} onNew={handleNewSession} onDelete={handleDeleteSession} />
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

            <section>
              <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.12em] text-porcelain-400">
                <History className="h-3.5 w-3.5" aria-hidden="true" />
                样例
              </div>
              <div className="space-y-1.5">
                {examples.map((example) => (
                  <button
                    key={example}
                    type="button"
                    disabled={isStreaming || loadingSession}
                    onClick={() => startQuery(example)}
                    className="w-full rounded-md border border-porcelain-200 bg-white px-3 py-2.5 text-left text-xs leading-5 text-porcelain-600 transition hover:border-kinpaku/30 hover:bg-porcelain-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </section>
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
            </div>
          </div>
        </aside>

        {/* 主区域：每次只渲染一个面板，完整挂载/卸载 */}
        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          {activeTab === "analysis" ? (
            <>
            <header className="flex h-14 shrink-0 items-center justify-between border-b border-porcelain-200 bg-white/90 px-4 backdrop-blur lg:px-6">
              <div className="flex items-center gap-3">
                <button onClick={() => setActiveTab("sql")}
                  className="rounded-md border border-porcelain-200 bg-white px-3 py-1.5 text-xs font-medium text-porcelain-600 hover:bg-porcelain-100">
                  ← 返回问数
                </button>
                <div className="text-sm font-semibold text-porcelain-900">深度分析</div>
              </div>
            </header>
            <div className="flex-1 overflow-hidden">
              <AnalysisPanel onBack={() => setActiveTab("sql")} />
            </div>
            </>
          ) : (
            <>
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
          </>
          )}
        </main>
      </div>
    </div>
    </>
  );
}
