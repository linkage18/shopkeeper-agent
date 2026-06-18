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
        f"判断以下用户问题的意图，只返回一个词：sql、rag、analysis。\n\n"
        f"规则：\n"
        f"- sql：用户要查数据、查报表、统计、查询数据库（如销售额、GMV、订单量）\n"
        f"- rag：用户要问文档、制度、规范、知识类问题（如年假多少天、技术栈是什么）\n"
        f"- analysis：用户要分析、深度分析、出报告、图表、报表分析（如分析趋势、对比数据）\n\n"
        f"问题：{req.query}\n\n"
        f"意图："
    )
    resp = await llm.ainvoke(prompt)
    intent = resp.content.strip().lower()
    if intent not in ("sql", "rag", "analysis"):
        intent = "sql"
    return {"intent": intent}
