"""
Token 计数器 — 用 tiktoken 估算 LLM 调用 token 消耗
"""
import tiktoken
from typing import Any


class TokenCounter:
    """全局单例 Token 计数器"""

    def __init__(self):
        self._encoder = tiktoken.get_encoding("cl100k_base")
        self._session_tokens: dict[str, dict] = {}  # session_id → token usage

    def estimate(self, text: str) -> int:
        return len(self._encoder.encode(text or ""))

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """估算 ChatML 格式的 token 数"""
        total = 0
        for msg in messages:
            total += 4
            total += self.estimate(msg.get("content", ""))
        return total

    def record(
        self,
        session_id: str,
        input_text: str,
        output_text: str,
        input_messages: list | None = None,
        usage: dict[str, int] | None = None,
    ):
        input_tokens = None
        output_tokens = None
        if usage:
            input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
            output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
        if input_tokens is None:
            input_tokens = self.count_messages(input_messages) if input_messages else self.estimate(input_text)
        if output_tokens is None:
            output_tokens = self.estimate(output_text)
        if session_id not in self._session_tokens:
            self._session_tokens[session_id] = {"input": 0, "output": 0, "calls": 0}
        self._session_tokens[session_id]["input"] += input_tokens
        self._session_tokens[session_id]["output"] += output_tokens
        self._session_tokens[session_id]["calls"] += 1

    def get_session_usage(self, session_id: str) -> dict:
        usage = self._session_tokens.get(session_id, {"input": 0, "output": 0, "calls": 0})
        return {
            **usage,
            "total": usage["input"] + usage["output"],
        }

    def get_summary(self) -> dict:
        total_input = sum(v["input"] for v in self._session_tokens.values())
        total_output = sum(v["output"] for v in self._session_tokens.values())
        total_calls = sum(v.get("calls", 0) for v in self._session_tokens.values())
        return {
            "total_tokens": total_input + total_output,
            "total_input": total_input,
            "total_output": total_output,
            "total_calls": total_calls,
            "sessions": {k: v for k, v in sorted(
                self._session_tokens.items(),
                key=lambda x: x[1]["input"] + x[1]["output"],
                reverse=True
            )[:20]},
        }


token_counter = TokenCounter()
