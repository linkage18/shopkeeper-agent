"""
RAG 指标采集器

线程安全的内存计数器，采集运行时指标。
每次 RAG 问答请求自动记录，通过 /api/rag/metrics 暴露。

不依赖数据库，重启后重置。后续可对接 Prometheus 等监控系统。
"""
import time
import threading
from collections import defaultdict
from typing import Any


class RagMetrics:
    """RAG 运行时指标采集器"""

    def __init__(self):
        self._lock = threading.Lock()

        # 节点级指标
        self.node_calls = defaultdict(int)        # 节点调用次数
        self.node_success = defaultdict(int)      # 节点成功次数
        self.node_failures = defaultdict(int)     # 节点失败次数
        self.node_latency: dict[str, list[float]] = defaultdict(list)  # 节点耗时 ms

        # 检索指标
        self.total_queries = 0                    # 总查询次数
        self.hit_queries = 0                      # 命中上下文（非空）的查询次数
        self.empty_queries = 0                    # 未命中上下文（空）的查询次数
        self.qdrant_hits: list[int] = []          # 每次 Qdrant 召回数
        self.es_hits: list[int] = []              # 每次 ES 召回数
        self.context_chunks: list[int] = []       # 每次拼入上下文的父块数
        self.context_chars: list[int] = []        # 每次上下文字符数
        self.source_counts: list[int] = []        # 每次引用的来源数
        self.answer_lengths: list[int] = []       # 每次回答长度

        # 安全指标
        self.injection_attempts = 0               # 注入攻击尝试次数
        self.last_injection_time: float | None = None

        # 延迟指标
        self.total_latency: list[float] = []      # 端到端耗时 ms

        # 正在运行的节点（用于计算耗时）
        self._running_nodes: dict[str, float] = {}
        self._query_start: float | None = None

        # 熔断状态：每路连续失败 3 次后熔断
        self._circuit_breaker: dict[str, dict] = {
            "qdrant": {"failures": 0, "open": False},
            "es": {"failures": 0, "open": False},
        }

    # ── 节点级采集 ──

    def on_node_start(self, step: str):
        """节点开始：记录开始时间"""
        with self._lock:
            self._running_nodes[step] = time.perf_counter()
            self.node_calls[step] += 1

    def on_node_end(self, step: str, status: str):
        """节点结束：记录耗时和状态"""
        with self._lock:
            start = self._running_nodes.pop(step, None)
            if start:
                elapsed = (time.perf_counter() - start) * 1000
                self.node_latency[step].append(elapsed)

            if status == "success":
                self.node_success[step] += 1
            else:
                self.node_failures[step] += 1

    # ── 查询级采集 ──

    def on_query_start(self):
        """查询开始"""
        with self._lock:
            self._query_start = time.perf_counter()
            self.total_queries += 1

    def on_query_end(self):
        """查询结束：记录总耗时"""
        with self._lock:
            if self._query_start:
                elapsed = (time.perf_counter() - self._query_start) * 1000
                self.total_latency.append(elapsed)
                self._query_start = None

    def on_recall_result(self, qdrant_count: int, es_count: int):
        """召回结果"""
        with self._lock:
            self.qdrant_hits.append(qdrant_count)
            self.es_hits.append(es_count)

    def on_context_assembled(self, chunk_count: int, char_count: int):
        """上下文组装结果"""
        with self._lock:
            self.context_chunks.append(chunk_count)
            self.context_chars.append(char_count)
            if chunk_count > 0:
                self.hit_queries += 1
            else:
                self.empty_queries += 1

    def on_answer_generated(self, answer: str, source_count: int):
        """回答生成结果"""
        with self._lock:
            self.answer_lengths.append(len(answer))
            self.source_counts.append(source_count)

    def on_injection_detected(self):
        """注入攻击检测"""
        with self._lock:
            self.injection_attempts += 1
            self.last_injection_time = time.time()

    # ── 熔断降级 ──

    def record_recall_failure(self, source: str):
        """记录单路召回失败，连续 3 次后熔断"""
        with self._lock:
            cb = self._circuit_breaker.get(source)
            if cb:
                cb["failures"] += 1
                if cb["failures"] >= 3:
                    cb["open"] = True
                    logger.warning(f"[CIRCUIT] {source} 熔断激活（连续 {cb['failures']} 次失败）")

    def record_recall_success(self, source: str):
        """记录单路召回成功，关闭熔断"""
        with self._lock:
            cb = self._circuit_breaker.get(source)
            if cb:
                cb["failures"] = 0
                cb["open"] = False

    def is_circuit_open(self, source: str) -> bool:
        """检查指定通道是否处于熔断状态"""
        cb = self._circuit_breaker.get(source)
        return cb["open"] if cb else False

    # ── 聚合统计 ──

    def snapshot(self) -> dict[str, Any]:
        """生成当前快照"""
        with self._lock:
            n = self.total_queries or 1  # 防止除零

            def _p50(vals: list[float]) -> float:
                if not vals:
                    return 0.0
                sorted_vals = sorted(vals)
                return sorted_vals[len(sorted_vals) // 2]

            def _p90(vals: list[float]) -> float:
                if not vals:
                    return 0.0
                sorted_vals = sorted(vals)
                idx = int(len(sorted_vals) * 0.9)
                return sorted_vals[min(idx, len(sorted_vals) - 1)]

            def _p99(vals: list[float]) -> float:
                if not vals:
                    return 0.0
                sorted_vals = sorted(vals)
                idx = int(len(sorted_vals) * 0.99)
                return sorted_vals[min(idx, len(sorted_vals) - 1)]

            # 节点指标
            nodes = {}
            for step in sorted(set(list(self.node_calls.keys()))):
                calls = self.node_calls[step]
                succ = self.node_success[step]
                fail = self.node_failures[step]
                lat = self.node_latency.get(step, [])
                nodes[step] = {
                    "calls": calls,
                    "success": succ,
                    "failures": fail,
                    "success_rate": round(succ / max(calls, 1), 3),
                    "latency_ms_p50": round(_p50(lat), 1),
                    "latency_ms_p90": round(_p90(lat), 1),
                    "latency_ms_p99": round(_p99(lat), 1),
                }

            return {
                "summary": {
                    "total_queries": self.total_queries,
                    "hit_rate": round(self.hit_queries / n, 3),
                    "empty_rate": round(self.empty_queries / n, 3),
                    "injection_attempts": self.injection_attempts,
                },
                "latency": {
                    "total_ms_p50": round(_p50(self.total_latency), 1),
                    "total_ms_p90": round(_p90(self.total_latency), 1),
                    "total_ms_p99": round(_p99(self.total_latency), 1),
                },
                "retrieval": {
                    "qdrant_avg": round(sum(self.qdrant_hits) / max(len(self.qdrant_hits), 1), 1),
                    "es_avg": round(sum(self.es_hits) / max(len(self.es_hits), 1), 1),
                    "context_chunks_avg": round(
                        sum(self.context_chunks) / max(len(self.context_chunks), 1), 1
                    ),
                    "context_chars_avg": round(
                        sum(self.context_chars) / max(len(self.context_chars), 1), 1
                    ),
                },
                "generation": {
                    "answer_len_avg": round(sum(self.answer_lengths) / max(len(self.answer_lengths), 1), 1),
                    "sources_avg": round(sum(self.source_counts) / max(len(self.source_counts), 1), 1),
                },
                "nodes": nodes,
            }


# 全局单例
rag_metrics = RagMetrics()
