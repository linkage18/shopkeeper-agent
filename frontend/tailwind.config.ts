/**
 * Tailwind CSS 主题配置
 * Impeccable 设计体系 — 金箔金 + 铜绿 + 暖黑漆器
 */
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', '"SF Pro Display"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Noto Sans SC"', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SFMono-Regular"', 'Consolas', 'monospace'],
      },
      colors: {
        lacquer: "#1a1a18",
        "lacquer-light": "#2a2a26",
        kinpaku: "#c4901a",
        patina: "#5a8a7a",
        "patina-light": "#e8f0ec",
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(0,0,0,0.04)",
        card: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        elevated: "0 4px 6px rgba(0,0,0,0.05), 0 2px 4px rgba(0,0,0,0.03)",
      },
    },
  },
  plugins: [],
} satisfies Config;
