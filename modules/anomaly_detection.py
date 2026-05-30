"""经营异常检测模块：基于规则引擎"""

import pandas as pd
import numpy as np
from utils.helpers import safe_divide


def detect_anomalies(df, field_mapping, aggregates, metrics):
    """
    基于规则引擎检测经营异常。

    参数:
        df: Pandas DataFrame
        field_mapping: dict — 字段映射
        aggregates: dict — 聚合结果
        metrics: dict — 核心指标

    返回:
        anomalies: list — 异常列表，每条包含 type, description, possible_causes, suggest_metrics, severity
    """
    anomalies = []
    keys_present = metrics.get("_keys_present", [])

    gmv_col = field_mapping.get("gmv")
    orders_col = field_mapping.get("orders")
    uv_col = field_mapping.get("uv")
    pv_col = field_mapping.get("pv")
    refund_col = field_mapping.get("refund_amount")
    ad_col = field_mapping.get("ad_cost")
    date_col = field_mapping.get("date")
    cat_col = field_mapping.get("category")
    plat_col = field_mapping.get("platform")

    # --- 异常1：销售额环比下降超过20% ---
    if gmv_col and gmv_col in df.columns and date_col and date_col in df.columns:
        try:
            date_agg = df.groupby(date_col)[gmv_col].sum().reset_index()
            date_agg = date_agg.sort_values(date_col)

            if len(date_agg) >= 2:
                # 比较最后两期的日均销售额
                mid = len(date_agg) // 2
                first_half = date_agg.iloc[:mid][gmv_col].mean()
                second_half = date_agg.iloc[mid:][gmv_col].mean()
                if first_half > 0:
                    change = (second_half - first_half) / first_half
                    if change < -0.2:
                        anomalies.append({
                            "type": "销售额大幅下降",
                            "description": f"后半段日均销售额较前半段下降 {abs(change) * 100:.1f}%。",
                            "possible_causes": [
                                "季节性/周期性需求下降",
                                "推广投放减少或效果变差",
                                "竞品价格战或市场冲击",
                                "产品质量问题导致口碑下滑",
                            ],
                            "suggest_metrics": "日销售额、推广费用、转化率、退换货率",
                            "severity": "高",
                        })
        except Exception:
            pass

    # --- 异常2：最近期订单量环比下降 ---
    if orders_col and orders_col in df.columns and date_col and date_col in df.columns:
        try:
            date_agg = df.groupby(date_col)[orders_col].sum().reset_index()
            date_agg = date_agg.sort_values(date_col)
            if len(date_agg) >= 2:
                mid = len(date_agg) // 2
                first_orders = date_agg.iloc[:mid][orders_col].mean()
                second_orders = date_agg.iloc[mid:][orders_col].mean()
                if first_orders > 0 and (second_orders - first_orders) / first_orders < -0.2:
                    change = (second_orders - first_orders) / first_orders
                    anomalies.append({
                        "type": "订单量大幅下降",
                        "description": f"后半段日均订单量较前半段下降 {abs(change) * 100:.1f}%。",
                        "possible_causes": [
                            "流量波动或减少",
                            "转化率下降",
                            "商品吸引力下降",
                            "竞品活动冲击",
                        ],
                        "suggest_metrics": "订单量、UV、转化率、客单价",
                        "severity": "高",
                    })
        except Exception:
            pass

    # --- 异常3：退款率高于10% ---
    if "refund" in keys_present:
        refund_rate = metrics.get("退款率", 0)
        if refund_rate > 0.1:
            anomalies.append({
                "type": "退款率偏高",
                "description": f"整体退款率为 {refund_rate * 100:.1f}%，超过 10% 的警戒线。",
                "possible_causes": [
                    "部分品类退款率异常偏高（如服饰、美妆）",
                    "商品质量或描述不符",
                    "物流配送问题导致退货",
                    "售后处理流程不畅",
                ],
                "suggest_metrics": "品类退款率、退款原因分布",
                "severity": "中" if refund_rate < 0.15 else "高",
            })

    # --- 异常4：ROI 低于1 ---
    if "ad" in keys_present:
        roi = metrics.get("ROI (投产比)", 0)
        if roi < 1:
            anomalies.append({
                "type": "ROI 低于保本线",
                "description": f"整体 ROI 为 {roi:.2f}，低于 1.0 的保本线。推广投入未能带来正向回报。",
                "possible_causes": [
                    "推广投放效率低下",
                    "目标人群定位不准",
                    "落地页转化率低",
                    "出价策略不合理",
                ],
                "suggest_metrics": "ROI、推广费用占比、转化率",
                "severity": "高",
            })

    # --- 异常5：Top1 品类占比过高 ---
    if cat_col and cat_col in df.columns and gmv_col and gmv_col in df.columns:
        try:
            cat_agg = df.groupby(cat_col)[gmv_col].sum()
            top1_ratio = cat_agg.max() / cat_agg.sum()
            if top1_ratio > 0.4:
                top_cat = cat_agg.idxmax()
                anomalies.append({
                    "type": "品类集中度过高",
                    "description": f"Top1 品类「{top_cat}」销售额占比为 {top1_ratio * 100:.1f}%，超过 40%。",
                    "possible_causes": [
                        "品类结构单一，缺乏多元化布局",
                        "其他品类推广力度不足",
                        "过度依赖单一品类的市场需求",
                    ],
                    "suggest_metrics": "各品类销售额占比、品类数量",
                    "severity": "中",
                })
        except Exception:
            pass

    # --- 异常6：推广花费增加但销售额下降 ---
    if ad_col and gmv_col and ad_col in df.columns and gmv_col in df.columns and date_col and date_col in df.columns:
        try:
            # 按日期分组，计算推广费和销售额
            temp = df.groupby(date_col)[[gmv_col, ad_col]].sum().reset_index()
            temp = temp.sort_values(date_col)

            if len(temp) >= 10:
                # 取前 30% 和后 30% 的数据对比
                n = len(temp)
                first_n = max(3, n // 3)
                last_n = max(3, n // 3)

                first_avg_ad = temp.iloc[:first_n][ad_col].mean()
                last_avg_ad = temp.iloc[-last_n:][ad_col].mean()
                first_avg_gmv = temp.iloc[:first_n][gmv_col].mean()
                last_avg_gmv = temp.iloc[-last_n:][gmv_col].mean()

                if first_avg_ad > 0 and last_avg_ad > first_avg_ad * 1.1 and last_avg_gmv < first_avg_gmv * 0.9:
                    ad_change = (last_avg_ad - first_avg_ad) / first_avg_ad * 100
                    gmv_change = (last_avg_gmv - first_avg_gmv) / first_avg_gmv * 100
                    anomalies.append({
                        "type": "推广效率下降",
                        "description": f"推广费用增加 {ad_change:.0f}%，但销售额下降 {abs(gmv_change):.0f}%。",
                        "possible_causes": [
                            "推广投放策略需优化",
                            "流量质量下降",
                            "商品竞争力减弱",
                            "市场环境变化",
                        ],
                        "suggest_metrics": "ROI、CPC、转化率",
                        "severity": "高",
                    })
        except Exception:
            pass

    # --- 异常7：退款金额大于销售额 ---
    if refund_col and gmv_col and refund_col in df.columns and gmv_col in df.columns:
        try:
            over_refund = df[df[refund_col] > df[gmv_col]]
            if len(over_refund) > 0:
                anomalies.append({
                    "type": "退款数据异常",
                    "description": f"发现 {len(over_refund)} 条退款金额大于销售额的记录。",
                    "possible_causes": [
                        "数据录入错误",
                        "退款计算口径不同",
                        "包含部分全额退款但数据合并有误",
                    ],
                    "suggest_metrics": "退款金额、销售额、数据源准确性",
                    "severity": "中",
                })
        except Exception:
            pass

    # --- 异常8：UV 增加但订单量下降 ---
    if uv_col and orders_col and uv_col in df.columns and orders_col in df.columns and date_col and date_col in df.columns:
        try:
            temp = df.groupby(date_col)[[uv_col, orders_col]].sum().reset_index()
            temp = temp.sort_values(date_col)

            if len(temp) >= 10:
                n = len(temp)
                first_n = max(3, n // 3)
                last_n = max(3, n // 3)

                first_uv = temp.iloc[:first_n][uv_col].mean()
                last_uv = temp.iloc[-last_n:][uv_col].mean()
                first_orders = temp.iloc[:first_n][orders_col].mean()
                last_orders = temp.iloc[-last_n:][orders_col].mean()

                if first_uv > 0 and first_orders > 0:
                    uv_change = (last_uv - first_uv) / first_uv
                    orders_change = (last_orders - first_orders) / first_orders
                    if uv_change > 0.1 and orders_change < -0.1:
                        anomalies.append({
                            "type": "流量质量下降",
                            "description": (
                                f"UV 增加 {uv_change * 100:.0f}%，但订单量下降 {abs(orders_change) * 100:.0f}%。"
                                "流量在增加但转化效果变差。"
                            ),
                            "possible_causes": [
                                "推广带来不精准流量",
                                "落地页吸引力不足",
                                "商品价格或竞争力问题",
                                "临时性活动引流但转化不佳",
                            ],
                            "suggest_metrics": "转化率、UV、CPC、订单量",
                            "severity": "中",
                        })
        except Exception:
            pass

    # 如果没有检测到任何异常
    if not anomalies:
        anomalies.append({
            "type": "暂无异常",
            "description": "基于当前数据，未检测到明显的经营异常情况。",
            "possible_causes": [],
            "suggest_metrics": "",
            "severity": "低",
        })

    return anomalies
