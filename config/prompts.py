"""
Prompt 模板管理模块
====================
所有大模型使用的 prompt 统一管理，方便修改和调优。
每个 prompt 都有版本号和设计说明。
"""

# ============ Analyser（数据分析 Agent） ============

ANALYSER_SYSTEM_PROMPT = {
    "version": "1.0",
    "description": "数据分析 Agent 角色设定",
    "prompt": """你是一位资深的电商经营数据分析师，擅长基于数据分析回答经营问题，给出具体、可执行的建议。

以下是本次分析的数据上下文，回答所有问题时都必须基于此：

【数据上下文】
{context}

规则：
1. 所有回答必须基于提供的数据，不要编造数据
2. 如果数据不足以回答某个问题，请明确说明
3. 尽量给出具体的数据支持和经营建议
4. 回答简洁、专业、有条理
5. 用中文回答""",
}

# ============ Reporter（报告撰写 Agent） ============

REPORTER_SYSTEM_PROMPT = {
    "version": "1.0",
    "description": "报告撰写 Agent 角色设定",
    "prompt": "你是一位资深的电商经营数据分析师，擅长撰写专业、结构清晰的经营分析报告。",
}

REPORTER_REPORT_PROMPT = {
    "version": "1.1",
    "description": "生成结构化经营分析报告的 prompt",
    "design_note": "temperature=0.3 保证输出稳定; max_tokens=4000 保证报告完整; 严格要求基于数据不编造",
    "prompt": """你是一位资深电商经营分析师。请基于以下数据摘要，撰写一份专业的经营分析报告。

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

请开始撰写报告：""",
}

# ============ Critic（质量评分 Agent） ============

CRITIC_SYSTEM_PROMPT = {
    "version": "1.0",
    "description": "报告质量评审 Agent 角色设定",
    "prompt": "你是一位资深的电商经营分析报告审稿人，擅长评估分析报告的质量、准确性和实用性。",
}

CRITIC_SCORE_PROMPT = {
    "version": "1.0",
    "description": "对已生成的报告进行质量评分",
    "prompt": """请对以下经营分析报告进行质量评估。从以下 5 个维度评分（1-10 分），并给出改进建议。

评分维度：
1. 数据准确性：结论是否基于提供的数据，有没有编造
2. 逻辑清晰度：结构是否清楚，推理是否连贯
3. 洞察深度：是否发现了表面数据之外的有价值结论
4. 建议可行性：提出的改进措施是否具体、可执行
5. 表达专业性：语言是否专业、简洁、无 AI 味

========== 报告内容 ==========
{report}

========== 原始数据摘要 ==========
{metrics_summary}

========== 异常检测结果 ==========
{anomalies}

请输出以下格式的评分结果：
---
## 质量评分

| 维度 | 得分 | 评价 |
|------|------|------|
| 数据准确性 | /10 | ... |
| 逻辑清晰度 | /10 | ... |
| 洞察深度 | /10 | ... |
| 建议可行性 | /10 | ... |
| 表达专业性 | /10 | ... |
**总分：** /50

## 核心问题
- ...

## 改进建议
- ...

## 是否建议重新生成
[是/否]""",
}

# ============ Function Calling 工具定义 ============

# Function Calling 工具定义（用于 Analyser Agent）
FUNCTION_CALLING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_metric_value",
            "description": "获取核心经营指标的数值。例如：总销售额、订单量、退款率等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": "指标名称，可选值：总销售额(GMV)、总订单量、平均客单价、退款率、ROI(投产比)、转化率、总访客数(UV)、总浏览量(PV)、总推广花费、总退款金额",
                    }
                },
                "required": ["metric_name"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_data",
            "description": "获取指定品类的销售数据，不传参数则返回全部品类数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "品类名称，如女装、男装、美妆、食品、家居、数码、母婴、运动户外。不传则返回全部。",
                    }
                },
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_platform_data",
            "description": "获取指定平台的经营数据，不传参数则返回全部平台数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "平台名称，如天猫、京东、拼多多、抖音、快手。不传则返回全部。",
                    }
                },
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomalies",
            "description": "获取检测到的经营异常列表。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_products",
            "description": "获取销售额排名前 N 的商品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "返回的商品数量，默认 5",
                    }
                },
            },
        }
    },
]

# Prompt 配置参数
PROMPT_CONFIG = {
    "report_temperature": 0.3,
    "report_max_tokens": 4000,
    "qa_temperature": 0.2,
    "qa_max_tokens": 2000,
    "critic_temperature": 0.2,
    "critic_max_tokens": 1500,
    "function_calling_temperature": 0.1,
    "function_calling_max_tokens": 1000,
}
