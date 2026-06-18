"""
电商问数 Agent 使用的大模型实例
包装 LLM 以自动记录 Token 消耗
"""
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.conf.app_config import app_config
from app.report_agent.token_counter import token_counter


class TracedLLM:
    """包装 LLM，每次调用自动记录 token 消耗"""

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    def _get_session_id(self) -> str:
        from app.core.context import request_id_ctx_var
        rid = request_id_ctx_var.get()
        # 使用 request_id 作为临时的 session 标识
        return rid if rid and rid != "1" else "default"

    def _record(self, prompt: str | list, response: str):
        sid = self._get_session_id()
        if isinstance(prompt, list):
            input_text = " ".join(str(m) for m in prompt)
        else:
            input_text = prompt
        token_counter.record(sid, input_text, response)

    def invoke(self, prompt: str | list) -> str:
        if isinstance(prompt, str):
            from langchain_core.prompts import PromptTemplate
            result = self._llm.invoke(prompt)
        elif isinstance(prompt, list):
            result = self._llm.invoke(prompt)
        else:
            result = prompt
        text = result.content if hasattr(result, "content") else str(result)
        self._record(prompt, text)
        return text

    async def ainvoke(self, prompt: str | list) -> str:
        if isinstance(prompt, str):
            from langchain_core.prompts import PromptTemplate
            result = await self._llm.ainvoke(prompt)
        elif isinstance(prompt, list):
            result = await self._llm.ainvoke(prompt)
        else:
            result = prompt
        text = result.content if hasattr(result, "content") else str(result)
        self._record(prompt, text)
        return text

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
