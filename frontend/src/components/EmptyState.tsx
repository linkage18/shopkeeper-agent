/**
 * 首页空状态组件
 * 展示产品入口信息和可点击的示例问数问题
 */
import React from "react";
import { LineChart, Search, ShoppingBag, Sparkles } from "lucide-react";
import { cn } from "../lib/format";

type EmptyStateProps = {
  examples: string[];
  onUseExample: (example: string) => void;
};

const highlights = [
  { label: "混合检索", icon: Search },
  { label: "SQL 闭环", icon: LineChart },
  { label: "音乐数仓", icon: ShoppingBag },
];

export const EmptyState = React.memo(function EmptyState({ examples, onUseExample }: EmptyStateProps) {
  return (
    <div className="mx-auto flex flex-col justify-center px-4 py-12">
      <div className="mb-10 max-w-3xl">
        <div className="mb-5 inline-flex items-center gap-2 border border-kinpaku/20 bg-kinpaku/[0.06] px-3 py-1.5 text-sm font-semibold text-kinpaku">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Data Agent
        </div>
        <h1 className="text-balance text-4xl font-semibold leading-tight text-gray-900 sm:text-6xl">
          数据双引擎
        </h1>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {highlights.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="border border-gray-200 bg-white/55 px-4 py-4 shadow-subtle">
              <Icon className="mb-5 h-5 w-5 text-kinpaku" aria-hidden="true" />
              <div className="text-sm font-semibold text-gray-900">{item.label}</div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {examples.filter(e => e !== "---").slice(0, 8).map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => onUseExample(example)}
            className={cn(
              "min-h-20 border px-4 py-4 text-left text-[15px] leading-6 shadow-subtle transition",
              "border-gray-200 bg-white text-gray-700",
              "hover:-translate-y-0.5 hover:border-patina/30 hover:bg-white focus:outline-none focus:ring-2 focus:ring-patina/30",
            )}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
});
