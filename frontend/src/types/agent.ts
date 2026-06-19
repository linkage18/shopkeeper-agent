/**
 * 智能体类型定义
 * 定义问数智能体前端使用的 SSE 事件、流程步骤和聊天消息类型
 */
export type ProgressStatus = "running" | "success" | "error";

export type ProgressEvent = {
  type: "progress";
  step: string;
  status: ProgressStatus;
};

export type ResultEvent = {
  type: "result";
  data: unknown;
};

export type ErrorEvent = {
  type: "error";
  message: string;
};

export type AgentEvent = ProgressEvent | ResultEvent | ErrorEvent;

export type StepState = {
  step: string;
  status: ProgressStatus;
  updatedAt: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  status?: "streaming" | "done" | "error";
  steps?: StepState[];
  result?: unknown;
  error?: string;
  tab?: "sql" | "rag" | "report";      // 所属流程
  sources?: SourceRef[];     // RAG 问答的溯源引用
};

// ── RAG 专属类型 ──────────────────────────────────────────────────

export type SourceRef = {
  file_name: string;
  page_number: number;
  snippet: string;
  score: number;
};

export type RagResultEvent = {
  type: "result";
  answer: string;
  sources: SourceRef[];
};

// ── Session 会话管理类型 ─────────────────────────────────────────

export type SessionListItem = {
  id: string;
  created_at: number;
  query_count: number;
  first_query: string;
  summary: string;
};

export type SessionRecord = {
  timestamp: number;
  query: string;
  answer: string;
  sources: SourceRef[];
  summary: string;
};

export type SessionDetail = {
  session_id: string;
  history: SessionRecord[];
};
