"""数据清洗模块：基础数据清洗和质量检查"""

import pandas as pd
import numpy as np


def clean_data(df, field_mapping):
    """
    对数据进行基础清洗。

    参数:
        df: Pandas DataFrame
        field_mapping: dict — 字段映射 {标准字段名: 原始列名}

    返回:
        cleaned_df: 清洗后的 DataFrame
        cleaning_log: list — 清洗操作记录
        quality_issues: list — 数据质量问题列表
    """
    cleaned_df = df.copy()
    cleaning_log = []
    quality_issues = []

    # 1. 去除完全重复行
    before = len(cleaned_df)
    cleaned_df = cleaned_df.drop_duplicates()
    after = len(cleaned_df)
    if before > after:
        cleaning_log.append(f"已去除重复行：{before - after} 行")

    # 2. 日期字段处理
    date_col = field_mapping.get("date")
    if date_col and date_col in cleaned_df.columns:
        try:
            # 尝试多种格式解析
            cleaned_df[date_col] = pd.to_datetime(cleaned_df[date_col], errors="coerce")
            null_dates = cleaned_df[date_col].isnull().sum()
            if null_dates > 0:
                quality_issues.append(f"日期字段存在 {null_dates} 个无法解析的日期值。")
            cleaning_log.append(f"日期字段「{date_col}」已转为日期格式。")
        except Exception as e:
            quality_issues.append(f"日期字段转换失败：{str(e)}")
    else:
        cleaning_log.append("未识别到日期字段，跳过日期处理。")

    # 3. 数值字段处理
    numeric_fields = ["gmv", "orders", "uv", "pv", "refund_amount", "ad_cost"]
    for field in numeric_fields:
        col = field_mapping.get(field)
        if col and col in cleaned_df.columns:
            try:
                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce")
            except Exception as e:
                quality_issues.append(f"字段「{col}」转为数值时出错：{str(e)}")

    # 4. 缺失值提示
    missing_series = cleaned_df.isnull().sum()
    missing_cols = missing_series[missing_series > 0]
    if len(missing_cols) > 0:
        for col, cnt in missing_cols.items():
            pct = cnt / len(cleaned_df) * 100
            if pct > 50:
                quality_issues.append(f"字段「{col}」缺失严重（{pct:.1f}%），建议检查数据源。")
            elif pct > 10:
                quality_issues.append(f"字段「{col}」存在 {cnt} 个缺失值（{pct:.1f}%）。")
        cleaning_log.append(f"已统计缺失值情况。")

    # 5. 数据合理性检查
    # 检查负数销售额
    gmv_col = field_mapping.get("gmv")
    if gmv_col and gmv_col in cleaned_df.columns:
        neg_gmv = cleaned_df[gmv_col] < 0
        neg_count = neg_gmv.sum()
        if neg_count > 0:
            quality_issues.append(f"发现 {neg_count} 条负数销售额记录（字段：{gmv_col}），已替换为 0。")
            cleaned_df.loc[neg_gmv, gmv_col] = 0

    # 检查负数订单量
    orders_col = field_mapping.get("orders")
    if orders_col and orders_col in cleaned_df.columns:
        neg_orders = cleaned_df[orders_col] < 0
        neg_count = neg_orders.sum()
        if neg_count > 0:
            quality_issues.append(f"发现 {neg_count} 条负数订单量记录，已替换为 0。")
            cleaned_df.loc[neg_orders, orders_col] = 0

    # 检查退款金额大于销售额
    refund_col = field_mapping.get("refund_amount")
    if gmv_col and refund_col and gmv_col in cleaned_df.columns and refund_col in cleaned_df.columns:
        refund_gt_gmv = cleaned_df[refund_col] > cleaned_df[gmv_col]
        bad_count = refund_gt_gmv.sum()
        if bad_count > 0:
            quality_issues.append(
                f"发现 {bad_count} 条退款金额大于销售额的记录，可能数据有误。"
            )

    # 6. 删除全为空的列
    empty_cols = [col for col in cleaned_df.columns if cleaned_df[col].isnull().all()]
    if empty_cols:
        cleaned_df = cleaned_df.drop(columns=empty_cols)
        cleaning_log.append(f"已删除完全为空的列：{', '.join(empty_cols)}")

    if not cleaning_log:
        cleaning_log.append("未发现需要清洗的数据问题。")

    return cleaned_df, cleaning_log, quality_issues
