"""
电商问数 Agent 使用的大模型实例
包装 LLM 以自动记录 Token 消耗，保持与 LangChain LCEL 兼容（返回 AIMessage）
"""
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from app.conf.app_config import app_config
from app.report_agent.token_counter import token_counter


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


# 统一从配置读取模型三件套，节点只复用 llm，不重复初始化模型连接
_raw_llm = init_chat_model(
    model=app_config.llm.model_name,
    model_provider="openai",
    base_url=app_config.llm.base_url,
    api_key=app_config.llm.api_key,
    temperature=0,
)

# 对外暴露包装后的 llm 实例
llm = TracedLLM(_raw_llm)

if __name__ == "__main__":
    print(llm.invoke("你好"))
