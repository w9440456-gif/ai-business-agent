"""核心经营指标计算模块"""

import pandas as pd
import numpy as np
from utils.helpers import safe_divide


def calculate_metrics(df, field_mapping):
    """
    计算核心经营指标（全局汇总）。

    参数:
        df: Pandas DataFrame
        field_mapping: dict — 字段映射

    返回:
        metrics: dict — 核心指标字典
    """
    metrics = {}
    keys_present = []

    gmv_col = field_mapping.get("gmv")
    orders_col = field_mapping.get("orders")
    uv_col = field_mapping.get("uv")
    pv_col = field_mapping.get("pv")
    refund_col = field_mapping.get("refund_amount")
    ad_col = field_mapping.get("ad_cost")

    # 总销售额
    if gmv_col and gmv_col in df.columns:
        total_gmv = df[gmv_col].sum()
        metrics["总销售额 (GMV)"] = total_gmv
        keys_present.append("gmv")

    # 总订单量
    if orders_col and orders_col in df.columns:
        total_orders = df[orders_col].sum()
        metrics["总订单量"] = int(total_orders)
        keys_present.append("orders")

    # 平均客单价
    if "gmv" in keys_present and "orders" in keys_present:
        metrics["平均客单价"] = safe_divide(metrics["总销售额 (GMV)"], metrics["总订单量"])

    # 退款率
    if refund_col and refund_col in df.columns and "gmv" in keys_present:
        total_refund = df[refund_col].sum()
        metrics["总退款金额"] = total_refund
        metrics["退款率"] = safe_divide(total_refund, metrics["总销售额 (GMV)"])
        keys_present.append("refund")

    # ROI
    if ad_col and ad_col in df.columns and "gmv" in keys_present:
        total_ad = df[ad_col].sum()
        metrics["总推广花费"] = total_ad
        metrics["ROI (投产比)"] = safe_divide(metrics["总销售额 (GMV)"], total_ad)
        keys_present.append("ad")

    # 总访客数
    if uv_col and uv_col in df.columns:
        total_uv = df[uv_col].sum()
        metrics["总访客数 (UV)"] = int(total_uv)
        keys_present.append("uv")

    # 总浏览量
    if pv_col and pv_col in df.columns:
        total_pv = df[pv_col].sum()
        metrics["总浏览量 (PV)"] = int(total_pv)
        keys_present.append("pv")

    # 转化率
    if "orders" in keys_present and "uv" in keys_present:
        metrics["转化率"] = safe_divide(metrics["总订单量"], metrics["总访客数 (UV)"])

    # 记录可用的指标（方便其他模块引用）
    metrics["_keys_present"] = keys_present

    return metrics


def aggregate_by_date(df, field_mapping):
    """
    按日期聚合数据。

    返回:
        date_agg: DataFrame — 按日期汇总的指标
    """
    date_col = field_mapping.get("date")
    if not date_col or date_col not in df.columns:
        return pd.DataFrame()

    cols_to_agg = {}
    gmv_col = field_mapping.get("gmv")
    orders_col = field_mapping.get("orders")
    uv_col = field_mapping.get("uv")
    pv_col = field_mapping.get("pv")
    refund_col = field_mapping.get("refund_amount")
    ad_col = field_mapping.get("ad_cost")

    if gmv_col and gmv_col in df.columns:
        cols_to_agg[gmv_col] = "sum"
    if orders_col and orders_col in df.columns:
        cols_to_agg[orders_col] = "sum"
    if uv_col and uv_col in df.columns:
        cols_to_agg[uv_col] = "sum"
    if pv_col and pv_col in df.columns:
        cols_to_agg[pv_col] = "sum"
    if refund_col and refund_col in df.columns:
        cols_to_agg[refund_col] = "sum"
    if ad_col and ad_col in df.columns:
        cols_to_agg[ad_col] = "sum"

    if not cols_to_agg:
        return pd.DataFrame()

    date_agg = df.groupby(date_col).agg(cols_to_agg).reset_index()
    date_agg = date_agg.sort_values(date_col)
    return date_agg


def aggregate_by_category(df, field_mapping):
    """
    按品类聚合数据。

    返回:
        cat_agg: DataFrame — 按品类汇总的指标
    """
    cat_col = field_mapping.get("category")
    if not cat_col or cat_col not in df.columns:
        return pd.DataFrame()

    gmv_col = field_mapping.get("gmv")
    if not gmv_col or gmv_col not in df.columns:
        return pd.DataFrame()

    cat_agg = df.groupby(cat_col)[gmv_col].agg(["sum", "mean", "count"]).reset_index()
    cat_agg = cat_agg.sort_values("sum", ascending=False)
    cat_agg.columns = [cat_col, "总销售额", "平均销售额", "记录数"]
    return cat_agg


def aggregate_by_platform(df, field_mapping):
    """
    按平台聚合数据。

    返回:
        plat_agg: DataFrame — 按平台汇总的指标
    """
    plat_col = field_mapping.get("platform")
    if not plat_col or plat_col not in df.columns:
        return pd.DataFrame()

    gmv_col = field_mapping.get("gmv")
    orders_col = field_mapping.get("orders")
    ad_col = field_mapping.get("ad_cost")

    agg_dict = {}
    if gmv_col and gmv_col in df.columns:
        agg_dict["gmv_sum"] = (gmv_col, "sum")
    if orders_col and orders_col in df.columns:
        agg_dict["orders_sum"] = (orders_col, "sum")
    if ad_col and ad_col in df.columns:
        agg_dict["ad_sum"] = (ad_col, "sum")

    if not agg_dict:
        return pd.DataFrame()

    plat_agg = df.groupby(plat_col).agg(
        **agg_dict
    ).reset_index()

    # 添加计算指标
    if "gmv_sum" in plat_agg.columns:
        total = plat_agg["gmv_sum"].sum()
        plat_agg["销售额占比"] = plat_agg["gmv_sum"] / total if total > 0 else 0

    if "gmv_sum" in plat_agg.columns and "ad_sum" in plat_agg.columns:
        plat_agg["ROI"] = plat_agg.apply(
            lambda r: safe_divide(r["gmv_sum"], r["ad_sum"]), axis=1
        )

    return plat_agg.sort_values("gmv_sum", ascending=False)
