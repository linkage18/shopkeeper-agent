"""
后处理 Hook 管道

在 LLM 生成回答后异步执行：质量检查、状态更新、持久化。
每个 hook 独立 try/except，不阻塞主流程。
"""
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from app.conf.app_config import app_config
from app.core.log import logger


async def execute_post_hooks(state: dict, answer: str, sources: list) -> dict:
    """执行所有后处理 hook，返回更新后的 state"""
    
    hooks = []
    
    # Hook 1: 会话历史更新
    hooks.append(_update_conversation_history(state, answer, sources))
    
    # Hook 2: 会话摘要（每 3 轮触发）
    history = state.get("conversation_history", [])
    if len(history) > 0 and len(history) % 3 == 0:
        hooks.append(_update_session_summary(state))
    
    # Hook 3: 记忆持久化
    hooks.append(_persist_session(state, answer, sources))
    
    if hooks:
        results = await asyncio.gather(*hooks, return_exceptions=True)
        for r in results:
            if isinstance(r, dict) and "session_summary" in r:
                state["session_summary"] = r["session_summary"]
    
    return state


async def _update_conversation_history(state: dict, answer: str, sources: list):
    """追加本轮对话到历史"""
    history = list(state.get("conversation_history", []))
    history.append({"role": "user", "content": state.get("query", "")})
    history.append({"role": "assistant", "content": answer, "sources": sources})
    max_rounds = app_config.rag.memory.short_term_rounds
    if len(history) > max_rounds * 2:
        history = history[-(max_rounds * 2):]
    state["conversation_history"] = history


async def _update_session_summary(state: dict) -> dict:
    """每 3 轮用 LLM 压缩历史对话为摘要"""
    from app.agent.llm import get_llm
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    
    history = list(state.get("conversation_history", []))
    if not history:
        return {}
    
    recent = history[-6:]
    lines = []
    for msg in recent:
        role = "用户" if msg.get("role") == "user" else "助手"
        content = str(msg.get("content", ""))[:200]
        lines.append(f"{role}: {content}")
    dialog_text = "\n".join(lines)
    
    prompt = PromptTemplate(
        template="请用一句话总结以下对话的核心内容（保留关键信息）：\n\n{dialog}",
        input_variables=["dialog"],
    )
    chain = prompt | shared_llm | StrOutputParser()
    
    try:
        summary = await chain.ainvoke({"dialog": dialog_text})
        old_summary = state.get("session_summary", "") or ""
        new_summary = f"{old_summary}\n- {summary.strip()}" if old_summary else f"- {summary.strip()}"
        logger.info(f"[HOOK] 会话摘要更新: {summary[:60]}")
        return {"session_summary": new_summary}
    except Exception as e:
        logger.error(f"[HOOK] 摘要生成失败: {e}")
        return {}


async def _persist_session(state: dict, answer: str, sources: list):
    """每轮保存 session 到 JSONL 文件"""
    session_id = state.get("session_id", "unknown")
    log_dir = Path("data/sessions")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    src_list = []
    for s in (sources or []):
        if hasattr(s, "__dict__"):
            src_list.append(s.__dict__)
        elif isinstance(s, dict):
            src_list.append(s)
        else:
            src_list.append({"file_name": str(s)})
    
    record = {
        "timestamp": time.time(),
        "session_id": session_id,
        "query": state.get("query", ""),
        "answer": answer,
        "sources": src_list,
        "summary": state.get("session_summary", ""),
    }
    
    file_path = log_dir / f"{session_id}.jsonl"
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
