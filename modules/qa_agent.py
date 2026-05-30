"""AI 问数助手模块（支持多轮对话）"""

import os
from dotenv import load_dotenv


def _get_client():
    """获取 OpenAI 客户端，支持自定义 API 地址"""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _build_system_prompt(context):
    """
    构建 system prompt，注入数据上下文。
    context 不随对话改变，保证所有轮次都基于同一份数据。
    """
    return f"""你是一位资深的电商经营数据分析师，擅长基于数据分析回答经营问题，给出具体、可执行的建议。

以下是本次分析的数据上下文，回答所有问题时都必须基于此：

【数据上下文】
{context}

规则：
1. 所有回答必须基于提供的数据，不要编造数据
2. 如果数据不足以回答某个问题，请明确说明
3. 尽量给出具体的数据支持和经营建议
4. 回答简洁、专业、有条理
5. 用中文回答"""


def answer_business_question(question, context, history=None):
    """
    使用 OpenAI API 回答用户的经营分析问题（支持多轮对话）。

    参数:
        question: str — 用户当前问题
        context: str — 数据上下文（指标、聚合、异常等），不会随对话改变
        history: list[dict], optional — 历史对话记录
            每个元素格式为 {"role": "user"|"assistant", "content": str}

    返回:
        success: bool
        result: str — 回答或错误信息
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key or api_key == "your_api_key_here":
        return False, "请先配置 API Key（在 .env 文件中），即可使用 AI 问数助手。"

    try:
        client = _get_client()

        # 构建 messages 列表：system prompt（含数据上下文）+ 历史 + 当前问题
        messages = [
            {"role": "system", "content": _build_system_prompt(context)},
        ]

        # 插入历史对话（保留上下文连贯性）
        if history:
            messages.extend(history)

        # 追加当前问题
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )

        answer = response.choices[0].message.content
        return True, answer

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower():
            return False, "API Key 认证失败，请检查配置是否正确。"
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return False, "API 请求过于频繁，请稍后重试。"
        else:
            return False, f"AI 回答生成失败：{error_msg}"
