"""Intent routing for user queries"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.agent.llm import llm

intent_router = APIRouter(prefix="/api/intent", tags=["intent"])


class IntentReq(BaseModel):
    query: str


@intent_router.post("/classify")
async def classify_intent(req: IntentReq):
    prompt = (
        f"判断以下用户问题的意图，只返回一个词：sql、rag、report。\n\n"
        f"规则：\n"
        f"- sql：用户要查具体数据、查报表、查数字（如上个月GMV、华东区销售额）\n"
        f"- rag：用户要问文档、制度、规范、知识类问题（如年假多少天、技术栈是什么）\n"
        f"- report：用户要分析、总结、出报告、深度分析、对比分析、趋势分析（如总结Q1销售情况、分析各品牌表现、出报告）\n\n"
        f"问题：{req.query}\n\n"
        f"意图："
    )
    resp = await llm.ainvoke(prompt)
    intent = resp.content.strip().lower()
    if intent not in ("sql", "rag", "report"):
        intent = "sql"
    return {"intent": intent}
