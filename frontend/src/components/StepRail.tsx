/**
 * 智能体执行流程图组件
 * 支持 NL2SQL（复杂拓扑）和 RAG（线性流程）两种模式
 * Impeccable 设计 — 金箔金/铜绿/暖黑漆器
 */
import { Check, Circle, LoaderCircle, X } from "lucide-react";
import { cn } from "../lib/format";
import type { ProgressStatus, StepState } from "../types/agent";

type FlowStatus = ProgressStatus | "pending";

export type FlowNode = { step: string; x: number; y: number; w?: number };

const SQL_NODES: FlowNode[] = [
  { step: "抽取关键词", x: 410, y: 20 },
  { step: "召回字段信息", x: 150, y: 112 },
  { step: "召回指标信息", x: 410, y: 112 },
  { step: "召回字段取值", x: 670, y: 112 },
  { step: "合并召回信息", x: 410, y: 214 },
  { step: "过滤指标信息", x: 290, y: 318 },
  { step: "过滤表信息", x: 530, y: 318 },
  { step: "添加额外上下文", x: 410, y: 422, w: 176 },
  { step: "生成SQL", x: 410, y: 526 },
  { step: "校验SQL", x: 410, y: 630 },
  { step: "校正SQL", x: 670, y: 630 },
  { step: "执行SQL", x: 410, y: 724 },
];

const SQL_CONNECTORS = [
  "M410 60 L410 84 L150 84 L150 106", "M410 60 L410 106", "M410 60 L410 84 L670 84 L670 106",
  "M150 152 L150 178 L410 178 L410 208", "M410 152 L410 208", "M670 152 L670 178 L410 178 L410 208",
  "M410 254 L410 282 L290 282 L290 312", "M410 254 L410 282 L530 282 L530 312",
  "M290 358 L290 386 L410 386 L410 416", "M530 358 L530 386 L410 386 L410 416",
  "M410 462 L410 520", "M410 566 L410 624",
  "M410 670 L410 718", "M488 650 L586 650",
  "M670 670 L670 606 L514 606 L514 624",
];

const BRANCH_LABELS = [
  { text: "有误", x: 530, y: 644 },
  { text: "无误", x: 366, y: 704 },
  { text: "回环修正", x: 556, y: 608, fs: 11 },
];

function getStatusMap(steps: StepState[]) {
  return steps.reduce<Record<string, StepState>>((map, item) => { map[item.step] = item; return map; }, {});
}

function statusFor(step: string, map: Record<string, StepState>): FlowStatus {
  return map[step]?.status ?? "pending";
}

function NodeIcon({ status }: { status: FlowStatus }) {
  if (status === "running") return <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />;
  if (status === "success") return <Check className="h-3.5 w-3.5" aria-hidden="true" />;
  if (status === "error") return <X className="h-3.5 w-3.5" aria-hidden="true" />;
  return <Circle className="h-3.5 w-3.5" aria-hidden="true" />;
}

function FlowNodeCard({ node, status }: { node: FlowNode; status: FlowStatus }) {
  const width = node.w ?? 156;
  return (
    <div className="absolute -translate-x-1/2" style={{ left: node.x, top: node.y, width }}>
      <div className={cn(
        "flex h-10 items-center gap-2 border px-3 text-sm font-semibold shadow-subtle transition",
        status === "pending" && "border-gray-200 bg-white/55 text-gray-400",
        status === "running" && "border-kinpaku/40 bg-kinpaku/[0.08] text-gray-900",
        status === "success" && "border-patina/30 bg-patina/[0.08] text-gray-900",
        status === "error" && "border-red-300 bg-red-50 text-red-600",
      )}>
        <span className={cn(
          "grid h-6 w-6 shrink-0 place-items-center rounded-full",
          status === "pending" && "bg-gray-100 text-gray-300",
          status === "running" && "bg-kinpaku/15 text-kinpaku",
          status === "success" && "bg-patina/15 text-patina",
          status === "error" && "bg-red-100 text-red-500",
        )}>
          <NodeIcon status={status} />
        </span>
        <span className="min-w-0 flex-1 truncate">{node.step}</span>
      </div>
    </div>
  );
}

const REPORT_STEPS = ["读取 Schema", "规划报告", "执行 SQL", "数据处理", "构建图表", "生成报告", "完成"];

type StepRailProps = { steps?: StepState[]; mode?: "sql" | "rag" | "report" };

export function StepRail({ steps = [], mode = "sql" }: StepRailProps) {
  if (steps.length === 0) return null;
  const statusMap = getStatusMap(steps);

  if (mode === "rag" || mode === "report") {
    const flowSteps = mode === "rag"
      ? ["抽取关键词", "召回文档", "组装上下文", "生成答案"]
      : REPORT_STEPS;
    return (
      <section className="mt-4 rounded-lg border border-gray-200 bg-white/40 px-3 py-4 shadow-subtle">
        <div className="mb-3 flex items-center justify-between gap-3 px-1">
          <div className="text-sm font-semibold text-gray-900">执行流程</div>
          <div className="text-xs text-gray-400">{mode === "rag" ? "RAG Agent" : "Report Agent"}</div>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {flowSteps.map((step) => {
            const st = statusMap[step];
            const flowStatus: "pending" | "running" | "success" | "error" = st ? st.status : "pending";
            return (
              <div key={step} className="flex items-center gap-3">
                <div className={cn(
                  "flex h-10 items-center gap-2 border px-4 text-sm font-semibold shadow-subtle transition",
                  flowStatus === "pending" && "border-gray-200 bg-white/55 text-gray-400",
                  flowStatus === "running" && "border-kinpaku/40 bg-kinpaku/[0.08] text-gray-900",
                  flowStatus === "success" && "border-patina/30 bg-patina/[0.08] text-gray-900",
                  flowStatus === "error" && "border-red-300 bg-red-50 text-red-600",
                )}>
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-gray-100 text-gray-300">
                    <NodeIcon status={flowStatus} />
                  </span>
                  <span className="min-w-0 flex-1 truncate">{step}</span>
                </div>
                {step !== flowSteps[flowSteps.length - 1] && <span className="text-lg text-gray-300">→</span>}
              </div>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <section className="mt-4 rounded-lg border border-gray-200 bg-white/40 px-3 py-4 shadow-subtle">
      <div className="mb-3 flex items-center justify-between gap-3 px-1">
        <div className="text-sm font-semibold text-gray-900">执行流程</div>
        <div className="text-xs text-gray-400">LangGraph</div>
      </div>
      <div className="overflow-x-auto">
        <div className="relative mx-auto h-[780px] w-[820px]">
          <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 820 780" fill="none" aria-hidden="true">
            <defs>
              <marker id="flow-arrow" markerHeight="8" markerWidth="8" orient="auto" refX="6" refY="4">
                <path d="M0 0 L8 4 L0 8 Z" fill="rgba(90,138,122,0.6)" />
              </marker>
            </defs>
            {SQL_CONNECTORS.map((path) => (
              <path key={path} d={path} stroke="rgba(90,138,122,0.4)" strokeWidth="1.5" markerEnd="url(#flow-arrow)" />
            ))}
            {BRANCH_LABELS.map((label) => (
              <text key={label.text} x={label.x} y={label.y} fill="rgba(90,138,122,0.5)" fontSize={label.fs ?? 13} fontWeight="600">{label.text}</text>
            ))}
          </svg>
          {SQL_NODES.map((node) => (
            <FlowNodeCard key={node.step} node={node} status={statusFor(node.step, statusMap)} />
          ))}
        </div>
      </div>
    </section>
  );
}
