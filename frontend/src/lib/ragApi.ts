/**
 * RAG 知识库接口客户端
 * 封装 /api/rag/query SSE 流式 + /api/rag/upload 文件上传
 */
import type { AgentEvent, RagResultEvent, SourceRef } from "../types/agent";
import { authHeaders } from "./authApi";
import { parseSseChunk } from "./sse";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

type QueryOptions = {
  signal?: AbortSignal;
  onEvent: (event: AgentEvent | RagResultEvent) => void;
};

export async function streamRagQuery(query: string, sessionId: string, options: QueryOptions) {
  const response = await fetch(`${API_BASE_URL}/api/rag/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...authHeaders(),
    },
    body: JSON.stringify({ query, session_id: sessionId }),
    signal: options.signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => `HTTP ${response.status}`);
    throw new Error(text);
  }

  if (!response.body) {
    throw new Error("浏览器未返回可读取的流式响应。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split(/\n\n/);
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const event = parseSseChunk<AgentEvent | RagResultEvent>(chunk);
      if (event) {
        options.onEvent(event);
      }
    }
  }
}


export async function uploadFile(file: File): Promise<{ status: string; result: Record<string, unknown> }> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/rag/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => `HTTP ${response.status}`);
    throw new Error(text);
  }

  return response.json();
}

// ── Session 会话管理 ──────────────────────────────────────────────

import type { SessionListItem, SessionDetail } from "../types/agent";

export async function listSessions(): Promise<{ sessions: SessionListItem[] }> {
  const resp = await fetch(`${API_BASE_URL}/api/rag/sessions`, { headers: authHeaders() });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

export async function getSession(id: string): Promise<SessionDetail> {
  const resp = await fetch(`${API_BASE_URL}/api/rag/sessions/${id}`, { headers: authHeaders() });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`${API_BASE_URL}/api/rag/sessions/${id}`, { method: "DELETE", headers: authHeaders() });
}
