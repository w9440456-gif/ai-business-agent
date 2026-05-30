"""
Agent 核心引擎
==============
支持多 Agent 协作（Analyzer → Reporter → Critic）和 Function Calling。
所有 Agent 统一通过此引擎管理 API 调用、token 预算和错误处理。
"""

import os
import json
from dotenv import load_dotenv


def _get_client():
    """获取 OpenAI 客户端，支持自定义 API 地址"""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _check_api_key():
    """检查 API Key 是否已配置"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    if not api_key or api_key == "your_api_key_here":
        return False, None, None
    return True, api_key, model


def call_llm(messages, temperature=0.2, max_tokens=2000, tools=None):
    """
    统一的 LLM 调用接口，支持普通对话和 Function Calling。

    参数:
        messages: list[dict] — 消息列表 [{"role": "system", "content": ...}, ...]
        temperature: float — 温度参数
        max_tokens: int — 最大 token 数
        tools: list[dict], optional — Function Calling 工具定义

    返回:
        success: bool
        result: str or dict — 回答文本 或 {"tool_calls": [...]}
    """
    ok, api_key, model = _check_api_key()
    if not ok:
        return False, "请先配置 API Key（在 .env 文件中）。"

    try:
        client = _get_client()
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools

        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        # 判断是否是 Function Calling 响应
        if msg.tool_calls:
            tool_results = []
            for tc in msg.tool_calls:
                tool_results.append({
                    "id": tc.id,
                    "function_name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
            return True, {"type": "tool_call", "tool_calls": tool_results}

        return True, msg.content or ""

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower():
            return False, "API Key 认证失败，请检查配置是否正确。"
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return False, "API 请求过于频繁，请稍后重试。"
        elif "insufficient_quota" in error_msg.lower():
            return False, "API 配额不足，请检查账户余额。"
        else:
            return False, f"API 调用失败：{error_msg}"


def call_llm_with_functions(messages, tools, tool_executor, temperature=0.1, max_tokens=1000, max_rounds=5):
    """
    支持多轮 Function Calling 的 LLM 调用。
    AI 可以多次调用工具，最终生成文本回答。

    参数:
        messages: list[dict] — 初始消息列表
        tools: list[dict] — Function Calling 工具定义
        tool_executor: callable — 工具执行函数，接收 (function_name, arguments) 返回结果字符串
        temperature: float
        max_tokens: int
        max_rounds: int — 最大 Function Calling 轮次，防止死循环

    返回:
        success: bool
        result: str — 最终回答文本
    """
    current_messages = list(messages)

    for round_idx in range(max_rounds):
        ok, result = call_llm(current_messages, temperature=temperature, max_tokens=max_tokens, tools=tools)

        if not ok:
            return False, result

        if isinstance(result, str):
            # 最终回答
            return True, result

        if isinstance(result, dict) and result.get("type") == "tool_call":
            # 执行工具调用
            for tc in result["tool_calls"]:
                fn_name = tc["function_name"]
                fn_args = tc.get("arguments", {})

                # 执行工具
                try:
                    tool_result = tool_executor(fn_name, fn_args)
                except Exception as e:
                    tool_result = f"工具执行错误：{str(e)}"

                # 将工具调用和结果追加到对话中
                current_messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": fn_name, "arguments": json.dumps(fn_args)},
                    }],
                })
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result,
                })

    # 超过最大轮次，强制让 AI 总结
    current_messages.append({
        "role": "user",
        "content": "请基于当前信息给出最终回答。",
    })
    ok, result = call_llm(current_messages, temperature=temperature, max_tokens=max_tokens)
    return ok, result


class AgentPipeline:
    """
    多 Agent 流水线：按顺序执行多个 Agent，前一 Agent 的输出作为后一 Agent 的输入。

    示例：
        pipeline = AgentPipeline([
            ("Analyser", analyser_agent),
            ("Reporter", reporter_agent),
            ("Critic", critic_agent),
        ])
        result = pipeline.run(initial_input)
    """

    def __init__(self, stages):
        """
        参数:
            stages: list[tuple[str, callable]] — [(名称, 函数), ...]
                函数的签名：def agent_fn(input_data: dict, stage_name: str) -> dict
        """
        self.stages = stages

    def run(self, initial_input):
        """
        运行流水线，每阶段的结果会追加到 input_data['stage_outputs'] 中。

        返回:
            success: bool
            result: dict — 包含所有阶段的输出
        """
        data = dict(initial_input)
        data.setdefault("stage_outputs", {})

        for stage_name, stage_fn in self.stages:
            try:
                output = stage_fn(data, stage_name)
                data["stage_outputs"][stage_name] = output
            except Exception as e:
                return False, {
                    "error": f"Agent [{stage_name}] 执行失败: {str(e)}",
                    "stage_outputs": data["stage_outputs"],
                }

        return True, data
