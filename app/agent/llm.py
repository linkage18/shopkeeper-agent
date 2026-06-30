"""电商问数 Agent 使用的大模型实例

包装 LLM 以自动记录 Token 消耗，保持与 LangChain LCEL 兼容（返回 AIMessage），
并提供可注入接口，方便测试时替换为 mock。
"""

from __future__ import annotations
from contextvars import ContextVar
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from app.conf.app_config import app_config
from app.core.token_counter import token_counter


class TracedLLM(Runnable):
    """包装 LLM，每次调用自动记录 token 消耗，保持返回 AIMessage"""

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    def _get_session_id(self) -> str:
        from app.core.context import request_id_ctx_var, user_ctx_var
        user = user_ctx_var.get()
        if user and user.get("user_id"):
            return str(user["user_id"])
        rid = request_id_ctx_var.get()
        return str(rid) if rid and rid != "1" else "default"

    def _record(self, prompt: str | list, response_text: str, raw_response=None):
        sid = self._get_session_id()
        if isinstance(prompt, list):
            input_text = " ".join(str(m) for m in prompt)
        else:
            input_text = prompt
        usage = getattr(raw_response, "usage_metadata", None)
        if usage is None:
            usage = getattr(raw_response, "response_metadata", {}).get("token_usage") if raw_response is not None else None
        token_counter.record(sid, input_text, response_text, usage=usage)

    def invoke(self, prompt: Any, config: Any = None, **kwargs: Any) -> AIMessage:
        """返回 AIMessage，保持 LCEL 链兼容"""
        result = self._llm.invoke(prompt, config=config, **kwargs)
        text = result.content if hasattr(result, "content") else str(result)
        self._record(prompt, text, result)
        return result

    async def ainvoke(self, prompt: Any, config: Any = None, **kwargs: Any) -> AIMessage:
        """返回 AIMessage，保持 LCEL 链兼容"""
        result = await self._llm.ainvoke(prompt, config=config, **kwargs)
        text = result.content if hasattr(result, "content") else str(result)
        self._record(prompt, text, result)
        return result

    def __getattr__(self, name: str):
        return getattr(self._llm, name)


# ---------------------------------------------------------------------------
# 可替换的 LLM 实例
#
# 模块加载时用默认配置创建 LLM；测试时可通过 override_llm() 注入 mock，
# 无需修改任何节点代码。
# ---------------------------------------------------------------------------
_llm_var: ContextVar[TracedLLM | None] = ContextVar("traced_llm", default=None)


def _create_default_llm() -> TracedLLM:
    """根据全局配置创建 LLM 实例"""
    raw_llm = init_chat_model(
        model=app_config.llm.model_name,
        model_provider="openai",
        base_url=app_config.llm.base_url,
        api_key=app_config.llm.api_key,
        temperature=0,
    )
    return TracedLLM(raw_llm)


def get_llm() -> TracedLLM:
    """获取当前 LLM 实例

    优先返回通过 override_llm() 注入的实例，否则懒加载默认实例。
    所有使用方应调用 get_llm() 而非直接引用模块级变量。
    """
    traced = _llm_var.get()
    if traced is not None:
        return traced
    traced = _create_default_llm()
    _llm_var.set(traced)
    return traced


def override_llm(mock_llm: TracedLLM):
    """注入 mock LLM（用于测试）

    返回 token，调用方可用 reset_llm(token) 恢复。
    """
    return _llm_var.set(mock_llm)


def reset_llm(token):
    """恢复被 override 的 LLM 实例"""
    _llm_var.reset(token)


# 向后兼容 — 仍被 tests/test_llm.py 使用
llm = get_llm()
