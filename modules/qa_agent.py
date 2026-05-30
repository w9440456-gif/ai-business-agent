"""
AI 问数助手模块（支持多轮对话 + Function Calling）
==================================================
底层使用 core/agent_engine.py 的统一 LLM 调用接口。
"""

from core.agent_engine import call_llm
from config.prompts import ANALYSER_SYSTEM_PROMPT, PROMPT_CONFIG
from modules.ai_report import generate_context_for_qa


def answer_business_question(question, context, history=None):
    """
    使用 Analyser Agent 回答用户的经营分析问题（支持多轮对话）。

    参数:
        question: str — 用户当前问题
        context: str — 数据上下文（指标、聚合、异常等）
        history: list[dict], optional — 历史对话记录

    返回:
        success: bool
        result: str — 回答或错误信息
    """
    system_prompt = ANALYSER_SYSTEM_PROMPT["prompt"].format(context=context)
    config = PROMPT_CONFIG

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    return call_llm(
        messages,
        temperature=config["qa_temperature"],
        max_tokens=config["qa_max_tokens"],
    )
