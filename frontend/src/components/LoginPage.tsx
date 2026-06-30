import { useState } from "react";
import { apiPost, setToken, setUser } from "../lib/authApi";

interface Props {
  onLogin: () => void;
}

export function LoginPage({ onLogin }: Props) {
  const [tab, setTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const endpoint = tab === "login" ? "/api/auth/login" : "/api/auth/register";
      const data = await apiPost(endpoint, { username, password });
      setToken(data.token);
      setUser(data.user);
      onLogin();
    } catch (err: any) {
      setError(err.message || "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-dvh items-center justify-center bg-porcelain-50">
      <div className="w-full max-w-sm rounded-lg border border-porcelain-200 bg-white px-8 py-10 shadow-elevated">
        <h1 className="mb-2 text-center text-2xl font-semibold text-porcelain-900">Shopkeeper Agent</h1>
        <p className="mb-8 text-center text-sm text-porcelain-600">音乐商店智能问数助手</p>

        <div className="mb-6 flex rounded-md border border-porcelain-200 p-0.5">
          <button
            onClick={() => setTab("login")}
            className={`flex-1 rounded px-4 py-2 text-sm font-medium transition ${tab === "login" ? "bg-porcelain-900 text-white" : "text-porcelain-600 hover:text-porcelain-900"}`}
          >
            登录
          </button>
          <button
            onClick={() => setTab("register")}
            className={`flex-1 rounded px-4 py-2 text-sm font-medium transition ${tab === "register" ? "bg-porcelain-900 text-white" : "text-porcelain-600 hover:text-porcelain-900"}`}
          >
            注册
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-porcelain-700">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-md border border-porcelain-300 px-3 py-2 text-sm outline-none focus:border-kinpaku focus:ring-1 focus:ring-kinpaku"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-porcelain-700">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-porcelain-300 px-3 py-2 text-sm outline-none focus:border-kinpaku focus:ring-1 focus:ring-kinpaku"
              required
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-porcelain-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-porcelain-800 disabled:opacity-50"
          >
            {loading ? "处理中..." : tab === "login" ? "登录" : "注册"}
          </button>
        </form>
      </div>
    </div>
  );
}
