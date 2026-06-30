/**
 * 共享 SSE 事件解析工具
 * 统一 agentApi.ts 和 ragApi.ts 中的 parseSseChunk 逻辑
 */
import type { AgentEvent } from "../types/agent";

export function parseSseChunk<T = AgentEvent>(chunk: string): T | null {
  const payload = chunk
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.replace(/^data:\s?/, ""))
    .join("\n")
    .trim();

  if (!payload) return null;

  try {
    return JSON.parse(payload) as T;
  } catch {
    return {
      type: "error",
      message: `无法解析后端事件：${payload}`,
    } as unknown as T;
  }
}
