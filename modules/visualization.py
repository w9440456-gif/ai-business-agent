"""可视化模块：使用 Plotly 生成经营分析图表"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots


def _style_layout(fig, title, xlabel="", ylabel=""):
    """统一设置图表样式"""
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=50, b=40),
        font=dict(family="Arial, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_gmv_trend(date_agg, date_col, gmv_col, title="销售额趋势"):
    """销售额趋势折线图"""
    if date_agg.empty or gmv_col not in date_agg.columns:
        return _empty_fig("暂无销售额数据")
    fig = px.line(
        date_agg, x=date_col, y=gmv_col,
        title=title, markers=True,
        color_discrete_sequence=["#2E86AB"]
    )
    fig.update_traces(line=dict(width=2.5))
    return _style_layout(fig, title, xlabel="日期", ylabel="销售额")


def plot_orders_trend(date_agg, date_col, orders_col, title="订单量趋势"):
    """订单量趋势折线图"""
    if date_agg.empty or orders_col not in date_agg.columns:
        return _empty_fig("暂无订单量数据")
    fig = px.line(
        date_agg, x=date_col, y=orders_col,
        title=title, markers=True,
        color_discrete_sequence=["#A23B72"]
    )
    fig.update_traces(line=dict(width=2.5))
    return _style_layout(fig, title, xlabel="日期", ylabel="订单量")


def plot_category_top10(cat_agg, cat_col, sales_col="总销售额", title="品类销售额 Top 10"):
    """品类销售额 Top 10 柱状图"""
    if cat_agg.empty:
        return _empty_fig("暂无品类数据")
    top10 = cat_agg.head(10)
    fig = px.bar(
        top10, x=cat_col, y=sales_col,
        title=title, text_auto=".0f",
        color=sales_col, color_continuous_scale="Blues",
    )
    fig.update_traces(textposition="outside")
    return _style_layout(fig, title, xlabel="品类", ylabel="销售额")


def plot_platform_contribution(plat_agg, plat_col, sales_col="gmv_sum", title="平台销售额贡献"):
    """平台销售额贡献饼图"""
    if plat_agg.empty or sales_col not in plat_agg.columns:
        return _empty_fig("暂无平台数据")
    fig = px.pie(
        plat_agg, values=sales_col, names=plat_col,
        title=title, hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="outside", textinfo="percent+label")
    return _style_layout(fig, title)


def plot_refund_rate(date_agg, date_col, refund_col, gmv_col, title="退款率趋势"):
    """退款率趋势图"""
    if date_agg.empty or refund_col not in date_agg.columns or gmv_col not in date_agg.columns:
        return _empty_fig("暂无退款数据")
    temp = date_agg.copy()
    temp["退款率"] = temp[refund_col] / temp[gmv_col].replace(0, float("nan")) * 100
    temp["退款率"] = temp["退款率"].clip(upper=100)

    fig = px.line(
        temp, x=date_col, y="退款率",
        title=title, markers=True,
        color_discrete_sequence=["#E07A5F"]
    )
    # 添加 10% 警戒线
    fig.add_hline(
        y=10, line_dash="dash", line_color="red",
        annotation_text="警戒线 (10%)", annotation_position="top left"
    )
    fig.update_traces(line=dict(width=2.5))
    return _style_layout(fig, title, xlabel="日期", ylabel="退款率 (%)")


def plot_roi(date_agg, date_col, gmv_col, ad_col, title="ROI 趋势"):
    """ROI 趋势图"""
    if date_agg.empty or gmv_col not in date_agg.columns or ad_col not in date_agg.columns:
        return _empty_fig("暂无推广数据")
    temp = date_agg.copy()
    temp["ROI"] = temp[gmv_col] / temp[ad_col].replace(0, float("nan"))
    temp["ROI"] = temp["ROI"].clip(upper=20)

    fig = px.line(
        temp, x=date_col, y="ROI",
        title=title, markers=True,
        color_discrete_sequence=["#3D5A80"]
    )
    fig.add_hline(
        y=1, line_dash="dash", line_color="red",
        annotation_text="保本线 (1.0)", annotation_position="top left"
    )
    fig.update_traces(line=dict(width=2.5))
    return _style_layout(fig, title, xlabel="日期", ylabel="ROI")


def plot_conversion_rate(date_agg, date_col, orders_col, uv_col, title="转化率趋势"):
    """转化率趋势图"""
    if date_agg.empty or orders_col not in date_agg.columns or uv_col not in date_agg.columns:
        return _empty_fig("暂无转化率数据")
    temp = date_agg.copy()
    temp["转化率"] = temp[orders_col] / temp[uv_col].replace(0, float("nan")) * 100
    temp["转化率"] = temp["转化率"].clip(upper=50)

    fig = px.line(
        temp, x=date_col, y="转化率",
        title=title, markers=True,
        color_discrete_sequence=["#81B29A"]
    )
    fig.update_traces(line=dict(width=2.5))
    return _style_layout(fig, title, xlabel="日期", ylabel="转化率 (%)")


def _empty_fig(message="暂无可用数据"):
    """返回一个空的占位图"""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="gray")
    )
    fig.update_layout(
        title=dict(text=message, x=0.5),
        template="plotly_white",
        height=300,
    )
    return fig
