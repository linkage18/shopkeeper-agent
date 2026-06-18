"""
Token 计数器 — 用 tiktoken 估算 LLM 调用 token 消耗
"""
import tiktoken
from typing import Any


class TokenCounter:
    """全局单例 Token 计数器"""

    def __init__(self):
        self._encoder = tiktoken.get_encoding("cl100k_base")
        self._session_tokens: dict[str, dict] = {}  # session_id → {"input": N, "output": N}

    def estimate(self, text: str) -> int:
        return len(self._encoder.encode(text or ""))

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """估算 ChatML 格式的 token 数"""
        total = 0
        for msg in messages:
            total += 4
            total += self.estimate(msg.get("content", ""))
        return total

    def record(self, session_id: str, input_text: str, output_text: str, input_messages: list | None = None):
        input_tokens = self.count_messages(input_messages) if input_messages else self.estimate(input_text)
        output_tokens = self.estimate(output_text)
        if session_id not in self._session_tokens:
            self._session_tokens[session_id] = {"input": 0, "output": 0}
        self._session_tokens[session_id]["input"] += input_tokens
        self._session_tokens[session_id]["output"] += output_tokens

    def get_session_usage(self, session_id: str) -> dict:
        return self._session_tokens.get(session_id, {"input": 0, "output": 0})

    def get_summary(self) -> dict:
        total_input = sum(v["input"] for v in self._session_tokens.values())
        total_output = sum(v["output"] for v in self._session_tokens.values())
        return {
            "total_tokens": total_input + total_output,
            "total_input": total_input,
            "total_output": total_output,
            "sessions": {k: v for k, v in sorted(
                self._session_tokens.items(),
                key=lambda x: x[1]["input"] + x[1]["output"],
                reverse=True
            )[:20]},
        }


token_counter = TokenCounter()
