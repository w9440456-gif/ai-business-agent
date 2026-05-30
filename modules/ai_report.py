"""
AI 经营分析报告生成模块
========================
通过 Reporter Agent 生成结构化经营分析报告。
prompt 管理统一在 config/prompts.py 中。
"""

import os
from dotenv import load_dotenv
from config.prompts import REPORTER_SYSTEM_PROMPT, REPORTER_REPORT_PROMPT, PROMPT_CONFIG


def _get_client():
    """获取 OpenAI 客户端，支持自定义 API 地址"""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def generate_ai_report(metrics_summary, aggregates_summary, anomalies):
    """
    使用 Reporter Agent 生成经营分析报告。

    参数:
        metrics_summary: str — 指标摘要文本
        aggregates_summary: str — 聚合数据摘要
        anomalies: list — 异常检测结果列表

    返回:
        success: bool
        result: str — 报告文本或错误信息
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "deepseek-chat")

    if not api_key or api_key == "your_api_key_here":
        return False, "请先配置 API Key（在 .env 文件中），即可生成 AI 经营分析报告。"

    # 将异常列表转为文本
    if isinstance(anomalies, list):
        anomalies_text = "\n".join(
            [f"- [{a.get('severity', '未知')}] {a.get('type', '未知')}: {a.get('description', '')}"
             for a in anomalies]
        )
    else:
        anomalies_text = str(anomalies)

    # 从配置文件读取 prompt
    prompt = REPORTER_REPORT_PROMPT["prompt"].format(
        metrics_summary=metrics_summary,
        aggregates_summary=aggregates_summary,
        anomalies=anomalies_text,
    )

    try:
        client = _get_client()
        config = PROMPT_CONFIG

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": REPORTER_SYSTEM_PROMPT["prompt"]},
                {"role": "user", "content": prompt},
            ],
            temperature=config["report_temperature"],
            max_tokens=config["report_max_tokens"],
        )

        report = response.choices[0].message.content
        return True, report

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower():
            return False, "API Key 认证失败，请检查 OPENAI_API_KEY 是否正确配置。"
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return False, "API 请求过于频繁，请稍后重试。"
        elif "insufficient_quota" in error_msg.lower():
            return False, "API 配额不足，请检查账户余额。"
        else:
            return False, f"AI 报告生成失败：{error_msg}"


def generate_context_for_qa(metrics_summary, aggregates_summary, anomalies, field_mapping):
    """为问数助手构建上下文"""
    field_info = {}
    for std_field, original_col in field_mapping.items():
        if original_col:
            field_info[std_field] = original_col

    context = f"""
【数据字段信息】
数据中包含以下字段：{', '.join([f'{k}({v})' for k, v in field_info.items()])}

【经营指标摘要】
{metrics_summary}

【聚合数据摘要】
{aggregates_summary}

【异常检测结果】
{anomalies}
"""
    return context
