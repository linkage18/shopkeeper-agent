/**
 * Vite 开发与构建配置
 * 包含 React 插件和后端 API 开发代理
 */
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.VITE_DEV_PROXY_TARGET || env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          target: backend,
          changeOrigin: true,
          // 连接失败时自动尝试其他端口
          configure: (proxy) => {
            proxy.on("error", (err) => {
              if ((err as any).code === "ECONNREFUSED") {
                console.warn(`[proxy] 后端 ${backend} 连接失败，请确认后端已启动`);
              }
            });
          },
        },
      },
    },
  };
});
