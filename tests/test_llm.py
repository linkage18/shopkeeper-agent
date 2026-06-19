"""Test TracedLLM returns proper types"""
import sys; sys.path.insert(0, ".")
from app.agent.llm import llm
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
import asyncio

result = llm.invoke("简短回复：你好")
assert isinstance(result, AIMessage), f"Expected AIMessage, got {type(result)}"
print(f"[PASS] invoke returns AIMessage: {result.content[:30]}")


async def test():
    result = await llm.ainvoke("简短回复：世界")
    assert isinstance(result, AIMessage), f"Expected AIMessage, got {type(result)}"
    print(f"[PASS] ainvoke returns AIMessage: {result.content[:30]}")

    chain = PromptTemplate.from_template("回复：{q}") | llm | StrOutputParser()
    text = await chain.ainvoke({"q": "你好"})
    assert isinstance(text, str), f"Expected str, got {type(text)}"
    print(f"[PASS] StrOutputParser chain OK")

    # Verify token was recorded
    from app.report_agent.token_counter import token_counter
    summary = token_counter.get_summary()
    assert summary["total_calls"] > 0, "No tokens recorded"
    print(f"[PASS] Token recorded: {summary['total_calls']} calls, {summary['total_tokens']} tokens")

asyncio.run(test())
print("\nALL PASS")
