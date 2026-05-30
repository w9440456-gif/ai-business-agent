"""AI 经营分析报告生成模块"""

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


def _build_prompt(metrics_summary, aggregates_summary, anomalies):
    """构建大模型 prompt"""
    prompt = f"""你是一位资深电商经营分析师。请基于以下数据摘要，撰写一份专业的经营分析报告。

要求：
1. 报告语言：专业、简洁的中文
2. 不要编造数据，所有结论必须基于提供的指标
3. 如果某些指标缺失，明确说明"该指标当前数据不足，无法分析"
4. 结构完整，逻辑清晰
5. 对发现的异常给出可行的改进建议
6. 报告长度建议 800-1200 字

========== 经营指标摘要 ==========
{metrics_summary}

========== 聚合数据摘要 ==========
{aggregates_summary}

========== 异常检测结果 ==========
{anomalies}

========== 报告结构要求 ==========
请按以下结构撰写：

一、整体经营概况
- 本期内整体经营表现概述
- 核心指标完成情况

二、销售趋势分析
- 本期销售整体走势
- 是否存在季节性波动或异常波动

三、品类表现分析
- 各品类销售贡献度
- 品类健康度评估

四、平台表现分析
- 各平台销售贡献
- 重点平台表现

五、推广 ROI 分析
- 投放效率评估
- 渠道优化方向

六、退款与售后风险分析
- 退款率表现
- 高风险品类提示

七、核心异常问题
- 逐条说明检测到的异常
- 影响程度评估

八、经营优化建议
- 短期可执行措施
- 中长期策略建议

九、下阶段重点关注指标
- 建议重点监控的 3-5 个指标

请开始撰写报告："""

    return prompt


def generate_ai_report(metrics_summary, aggregates_summary, anomalies):
    """
    使用 OpenAI API 生成经营分析报告。

    参数:
        metrics_summary: str — 指标摘要文本
        aggregates_summary: str — 聚合数据摘要
        anomalies: list — 异常检测结果列表

    返回:
        success: bool
        result: str — 报告文本或错误信息
    """
    # 加载 API Key
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key or api_key == "your_api_key_here":
        return False, "请先配置 OPENAI_API_KEY（在 .env 文件中），即可生成 AI 经营分析报告。"

    try:
        client = _get_client()

        prompt = _build_prompt(metrics_summary, aggregates_summary, anomalies)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一位资深的电商经营数据分析师，擅长撰写专业、结构清晰的经营分析报告。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
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
    # 获取字段映射信息
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
