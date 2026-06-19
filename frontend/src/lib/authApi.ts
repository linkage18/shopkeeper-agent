const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const DEFAULT_TIMEOUT_MS = 8000;

export function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function removeToken() {
  localStorage.removeItem("token");
}

export function getUser(): { id: string; username: string; role: string } | null {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

export function setUser(user: { id: string; username: string; role: string }) {
  localStorage.setItem("user", JSON.stringify(user));
}

export function removeUser() {
  localStorage.removeItem("user");
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

async function readError(res: Response) {
  try {
    const data = await res.json();
    return data.detail || data.message || "请求失败";
  } catch {
    return await res.text().catch(() => "请求失败");
  }
}

async function withTimeout<T>(fn: (signal: AbortSignal) => Promise<T>, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fn(controller.signal);
  } catch (e: any) {
    if (e?.name === "AbortError") {
      throw new Error("请求超时，请检查后端服务或数据库连接");
    }
    throw e;
  } finally {
    window.clearTimeout(timer);
  }
}

let _onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(cb: () => void) {
  _onUnauthorized = cb;
}

async function checkResponse(res: Response) {
  if (res.status === 401) {
    removeToken();
    removeUser();
    if (_onUnauthorized) _onUnauthorized();
    throw new Error("登录已过期，请重新登录");
  }
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function apiPost(path: string, body: any) {
  const res = await withTimeout((signal) => fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
    signal,
  }));
  return checkResponse(res);
}

export async function apiGet(path: string) {
  const res = await withTimeout((signal) => fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
    signal,
  }));
  return checkResponse(res);
}

export async function apiDelete(path: string, body?: any) {
  const res = await withTimeout((signal) => fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  }));
  return checkResponse(res);
}
