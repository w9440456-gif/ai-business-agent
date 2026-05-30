"""工具函数"""

import streamlit as st


def safe_divide(numerator, denominator, default=0):
    """安全除法，分母为 0 时返回默认值"""
    try:
        if denominator is None or denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def format_number(value, decimal=0):
    """格式化数字，添加千分位"""
    if value is None or (isinstance(value, float) and (value != value)):  # NaN check
        return "—"
    try:
        if decimal > 0:
            return f"{value:,.{decimal}f}"
        return f"{value:,.0f}"
    except (ValueError, TypeError):
        return "—"


def format_percent(value, decimal=1):
    """格式化百分比"""
    if value is None or (isinstance(value, float) and (value != value)):
        return "—"
    try:
        if abs(value) < 1 and abs(value) > 0:
            return f"{value * 100:.{decimal}f}%"
        return f"{value:.{decimal}f}%"
    except (ValueError, TypeError):
        return "—"


def get_data_summary(df):
    """获取数据集的快速摘要信息"""
    info = {
        "行数": len(df),
        "列数": len(df.columns),
        "字段列表": list(df.columns),
        "缺失值统计": df.isnull().sum().to_dict(),
        "数值字段": list(df.select_dtypes(include=["number"]).columns),
        "文本字段": list(df.select_dtypes(include=["object"]).columns),
    }
    return info


def display_metric_card(title, value, subtitle="", delta=None, help_text=""):
    """在 Streamlit 中展示一个美观的指标卡片"""
    col = st.columns(1)[0]
    with col:
        st.metric(
            label=title,
            value=value,
            delta=delta,
            help=help_text,
        )


def check_api_key():
    """检查是否配置了 API Key"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_api_key_here":
        return True, api_key
    return False, None
