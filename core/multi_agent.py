"""
多 Agent 协作实现
=================
提供三个专业 Agent：

1. Analyser（数据分析师）：理解数据、回答问题的 Agent，支持 Function Calling
2. Reporter（报告撰写师）：生成结构化经营分析报告
3. Critic（质量评审师）：对报告进行质量评分和改进建议

流程：Analyser（分析数据）→ Reporter（撰写报告）→ Critic（评审报告）
"""

import os
import json
import pandas as pd
import sys

# 确保能找到上层模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent_engine import call_llm, call_llm_with_functions
from config.prompts import (
    ANALYSER_SYSTEM_PROMPT,
    REPORTER_SYSTEM_PROMPT,
    REPORTER_REPORT_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    CRITIC_SCORE_PROMPT,
    FUNCTION_CALLING_TOOLS,
    PROMPT_CONFIG,
)
from modules.metrics import calculate_metrics, aggregate_by_date, aggregate_by_category, aggregate_by_platform
from modules.ai_report import generate_context_for_qa


# ============ 工具执行器（Function Calling 的后端） ============

class ToolExecutor:
    """Function Calling 的工具执行器，绑定到当前数据上下文"""

    def __init__(self, cleaned_df, field_mapping):
        self.df = cleaned_df
        self.field_mapping = field_mapping
        self._cached_cat_agg = None
        self._cached_plat_agg = None
        self._cached_metrics = None

    def execute(self, function_name, arguments):
        """执行工具调用，返回结果字符串"""
        handler = getattr(self, f"_{function_name}", None)
        if not handler:
            return json.dumps({"error": f"未知工具: {function_name}"})
        try:
            result = handler(**arguments)
            # 限制返回长度，避免 token 溢出
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 3000:
                result_str = result_str[:3000] + "...（截断）"
            return result_str
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_metric_value(self, metric_name):
        """获取指定指标的数值"""
        if self._cached_metrics is None:
            self._cached_metrics = calculate_metrics(self.df, self.field_mapping)

        # 模糊匹配指标名称
        metric_map = {
            "总销售额": "总销售额 (GMV)",
            "gmv": "总销售额 (GMV)",
            "GMV": "总销售额 (GMV)",
            "销售额": "总销售额 (GMV)",
            "总订单量": "总订单量",
            "订单量": "总订单量",
            "平均客单价": "平均客单价",
            "客单价": "平均客单价",
            "退款率": "退款率",
            "roi": "ROI (投产比)",
            "ROI": "ROI (投产比)",
            "投产比": "ROI (投产比)",
            "转化率": "转化率",
            "访客数": "总访客数 (UV)",
            "uv": "总访客数 (UV)",
            "UV": "总访客数 (UV)",
            "浏览量": "总浏览量 (PV)",
            "pv": "总浏览量 (PV)",
            "PV": "总浏览量 (PV)",
            "推广花费": "总推广花费",
            "广告费": "总推广花费",
            "退款金额": "总退款金额",
        }
        std_name = metric_map.get(metric_name, metric_name)
        value = self._cached_metrics.get(std_name)
        if value is None:
            return {"metric": metric_name, "error": f"指标「{metric_name}」在当前数据中不可用"}
        return {"metric": metric_name, "value": value}

    def _get_category_data(self, category=None):
        """获取品类销售数据"""
        cat_agg = aggregate_by_category(self.df, self.field_mapping)
        if cat_agg.empty:
            return {"error": "无品类数据"}
        cat_col = self.field_mapping.get("category")
        if category:
            filtered = cat_agg[cat_agg[cat_col] == category]
            if filtered.empty:
                return {"error": f"品类「{category}」未找到", "available_categories": cat_agg[cat_col].tolist()}
            return filtered.to_dict(orient="records")
        return cat_agg.to_dict(orient="records")

    def _get_platform_data(self, platform=None):
        """获取平台经营数据"""
        plat_agg = aggregate_by_platform(self.df, self.field_mapping)
        if plat_agg.empty:
            return {"error": "无平台数据"}
        plat_col = self.field_mapping.get("platform")
        if platform:
            filtered = plat_agg[plat_agg[plat_col] == platform]
            if filtered.empty:
                return {"error": f"平台「{platform}」未找到", "available_platforms": plat_agg[plat_col].tolist()}
            return filtered.to_dict(orient="records")
        return plat_agg.to_dict(orient="records")

    def _get_anomalies(self):
        """获取异常列表"""
        from modules.anomaly_detection import detect_anomalies
        date_agg = aggregate_by_date(self.df, self.field_mapping)
        cat_agg = aggregate_by_category(self.df, self.field_mapping)
        plat_agg = aggregate_by_platform(self.df, self.field_mapping)
        metrics = calculate_metrics(self.df, self.field_mapping)
        anomalies = detect_anomalies(
            self.df, self.field_mapping,
            {"date_agg": date_agg, "cat_agg": cat_agg, "plat_agg": plat_agg},
            metrics
        )
        return [a for a in anomalies if a["type"] != "暂无异常"]

    def _get_top_products(self, top_n=5):
        """获取 Top N 商品"""
        prod_col = self.field_mapping.get("product_name")
        gmv_col = self.field_mapping.get("gmv")
        if not prod_col or not gmv_col:
            return {"error": "缺少商品名称或销售额字段"}
        if prod_col not in self.df.columns or gmv_col not in self.df.columns:
            return {"error": "商品或销售额数据不可用"}
        top = self.df.groupby(prod_col)[gmv_col].sum().sort_values(ascending=False).head(top_n)
        return [{"product": k, "gmv": int(v)} for k, v in top.items()]


# ============ Analyser Agent ============

def analyser_agent(data, stage_name="Analyser"):
    """
    Analyser Agent：数据分析师，支持 Function Calling。
    用户可以问经营数据相关问题，Agent 可以通过工具获取数据。

    参数:
        data: dict — 需包含 df, field_mapping

    返回:
        dict — 分析结果
    """
    df = data.get("df")
    field_mapping = data.get("field_mapping")
    user_question = data.get("question", "请分析整体经营情况")
    history = data.get("history", [])

    # 构建系统消息
    metrics = calculate_metrics(df, field_mapping)
    date_agg = aggregate_by_date(df, field_mapping)
    cat_agg = aggregate_by_category(df, field_mapping)
    plat_agg = aggregate_by_platform(df, field_mapping)
    from modules.anomaly_detection import detect_anomalies
    anomalies = detect_anomalies(df, field_mapping, {"date_agg": date_agg, "cat_agg": cat_agg, "plat_agg": plat_agg}, metrics)

    metrics_text = "\n".join([f"- {k}: {v}" for k, v in metrics.items() if not k.startswith("_")])
    agg_text = f"日期数据行数: {len(date_agg)}\n品类数据: {cat_agg.to_dict() if not cat_agg.empty else '无'}\n平台数据: {plat_agg.to_dict() if not plat_agg.empty else '无'}"
    anomalies_text = "\n".join([f"- [{a['severity']}] {a['type']}: {a['description']}" for a in anomalies])
    context = generate_context_for_qa(metrics_text, agg_text, anomalies_text, field_mapping)

    system_prompt = ANALYSER_SYSTEM_PROMPT["prompt"].format(context=context)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_question})

    # 用 Function Calling 模式处理
    executor = ToolExecutor(df, field_mapping)
    config = PROMPT_CONFIG
    ok, answer = call_llm_with_functions(
        messages,
        tools=FUNCTION_CALLING_TOOLS,
        tool_executor=executor.execute,
        temperature=config["function_calling_temperature"],
        max_tokens=config["qa_max_tokens"],
    )

    return {
        "success": ok,
        "answer": answer if ok else f"分析失败：{answer}",
    }


# ============ Reporter Agent ============

def reporter_agent(data, stage_name="Reporter"):
    """
    Reporter Agent：报告撰写师。
    基于指标和异常结果，生成结构化经营分析报告。

    参数:
        data: dict — 需包含 metrics_text, agg_text, anomalies_text

    返回:
        dict — 生成的报告
    """
    metrics_text = data.get("metrics_summary", "无指标数据")
    agg_text = data.get("aggregates_summary", "无聚合数据")
    anomalies = data.get("anomalies", [])

    # 将异常列表转为文本
    if isinstance(anomalies, list):
        anomalies_text = "\n".join(
            [f"- [{a.get('severity', '未知')}] {a.get('type', '未知')}: {a.get('description', '')}"
             for a in anomalies]
        )
    else:
        anomalies_text = str(anomalies)

    prompt = REPORTER_REPORT_PROMPT["prompt"].format(
        metrics_summary=metrics_text,
        aggregates_summary=agg_text,
        anomalies=anomalies_text,
    )

    config = PROMPT_CONFIG
    ok, result = call_llm(
        messages=[
            {"role": "system", "content": REPORTER_SYSTEM_PROMPT["prompt"]},
            {"role": "user", "content": prompt},
        ],
        temperature=config["report_temperature"],
        max_tokens=config["report_max_tokens"],
    )

    return {
        "success": ok,
        "report": result if ok else f"报告生成失败：{result}",
    }


# ============ Critic Agent ============

def critic_agent(data, stage_name="Critic"):
    """
    Critic Agent：报告质量评审师。
    评估已生成报告的质量，给出评分和改进建议。

    参数:
        data: dict — 需包含 report, metrics_summary, anomalies

    返回:
        dict — 评分结果
    """
    report = data.get("report", "")
    metrics_summary = data.get("metrics_summary", "无")
    anomalies = data.get("anomalies", [])

    if isinstance(anomalies, list):
        anomalies_text = "\n".join(
            [f"- [{a.get('severity', '未知')}] {a.get('type', '未知')}" for a in anomalies]
        )
    else:
        anomalies_text = str(anomalies)

    prompt = CRITIC_SCORE_PROMPT["prompt"].format(
        report=report,
        metrics_summary=metrics_summary,
        anomalies=anomalies_text,
    )

    config = PROMPT_CONFIG
    ok, result = call_llm(
        messages=[
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT["prompt"]},
            {"role": "user", "content": prompt},
        ],
        temperature=config["critic_temperature"],
        max_tokens=config["critic_max_tokens"],
    )

    return {
        "success": ok,
        "critique": result if ok else f"评审失败：{result}",
    }


# ============ 完整流水线 ============

def run_multi_agent_pipeline(df, field_mapping, user_question="请分析整体经营情况", history=None):
    """
    运行完整的多 Agent 流水线：Analyser → Reporter → Critic。

    参数:
        df: DataFrame — 清洗后的数据
        field_mapping: dict — 字段映射
        user_question: str — 用户问题
        history: list[dict], optional — 历史对话

    返回:
        success: bool
        result: dict — 包含所有 Agent 的输出
    """
    from core.agent_engine import AgentPipeline
    from modules.metrics import calculate_metrics, aggregate_by_date, aggregate_by_category, aggregate_by_platform
    from modules.anomaly_detection import detect_anomalies

    # 准备指标摘要
    metrics = calculate_metrics(df, field_mapping)
    date_agg = aggregate_by_date(df, field_mapping)
    cat_agg = aggregate_by_category(df, field_mapping)
    plat_agg = aggregate_by_platform(df, field_mapping)
    anomalies = detect_anomalies(df, field_mapping, {"date_agg": date_agg, "cat_agg": cat_agg, "plat_agg": plat_agg}, metrics)

    metrics_text = "\n".join([f"- {k}: {v}" for k, v in metrics.items() if not k.startswith("_")])
    agg_text = f"日期数据行数: {len(date_agg)}"

    pipeline = AgentPipeline([
        ("Analyser", analyser_agent),
        ("Reporter", reporter_agent),
        ("Critic", critic_agent),
    ])

    # 自定义 data flow hook：每阶段结束后将上一阶段的关键输出注入下一阶段
    def _stage_hook(stage_name, output, current_data):
        """在每阶段执行后调用，传递数据到下一阶段"""
        if stage_name == "Analyser":
            # 将 Analyser 的分析结果注入，供 Reporter 生成报告
            current_data["analyser_output"] = output.get("answer", "")
            # 也更新 metrics_summary 以包含分析中的新发现
            if output.get("success"):
                current_data["metrics_summary"] += f"\n\nAnalyser 补充分析：\n{output['answer'][:1500]}"
        elif stage_name == "Reporter":
            # 将 Reporter 生成的报告文本放入 data，供 Critic 使用
            current_data["report"] = output.get("report", "")

    initial_data = {
        "df": df,
        "field_mapping": field_mapping,
        "question": user_question,
        "history": history,
        "metrics_summary": metrics_text,
        "aggregates_summary": agg_text,
        "anomalies": anomalies,
        "metrics": metrics,
        "_stage_hook": _stage_hook,
    }

    # 自定义 pipeline 带 hook
    from core.agent_engine import AgentPipeline
    class HookedPipeline(AgentPipeline):
        def run(self, initial_input):
            data = dict(initial_input)
            data.setdefault("stage_outputs", {})
            for stage_name, stage_fn in self.stages:
                try:
                    output = stage_fn(data, stage_name)
                    data["stage_outputs"][stage_name] = output
                    # 调用 hook
                    hook = data.get("_stage_hook")
                    if hook:
                        hook(stage_name, output, data)
                except Exception as e:
                    return False, {
                        "error": f"Agent [{stage_name}] 执行失败: {str(e)}",
                        "stage_outputs": data["stage_outputs"],
                    }
            return True, data

    pipeline = HookedPipeline([
        ("Analyser", analyser_agent),
        ("Reporter", reporter_agent),
        ("Critic", critic_agent),
    ])

    success, result_data = pipeline.run(initial_data)
    return success, result_data
