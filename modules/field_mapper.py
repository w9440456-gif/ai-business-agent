"""字段映射模块：自动识别字段并支持手动映射"""

# 标准字段名称列表
STANDARD_FIELDS = ["date", "platform", "category", "product_name", "gmv", "orders", "uv", "pv", "refund_amount", "ad_cost"]

# 字段别名映射表（中文名 → 标准字段名）
FIELD_ALIASES = {
    # 日期
    "date": ["date", "日期", "时间", "下单时间", "支付时间", "统计日期", "交易时间", "业务日期", "销售日期"],
    # 平台
    "platform": ["platform", "平台", "渠道", "店铺", "来源", "销售渠道", "电商平台"],
    # 品类
    "category": ["category", "品类", "类目", "商品类目", "分类", "商品分类", "产品类目"],
    # 商品名称
    "product_name": ["product", "product_name", "商品", "商品名称", "sku", "产品名称", "产品", "商品名"],
    # 销售额
    "gmv": ["gmv", "销售额", "成交金额", "支付金额", "收入", "营业收入", "交易金额", "销售金额", "金额", "销售总额"],
    # 订单量
    "orders": ["orders", "订单量", "订单数", "成交订单数", "支付订单数", "销量", "销售数量", "订单"],
    # 访客数
    "uv": ["uv", "访客数", "用户数", "访问用户数", "独立访客", "访客"],
    # 浏览量
    "pv": ["pv", "浏览量", "访问量", "页面浏览量", "浏览量", "点击量"],
    # 退款金额
    "refund_amount": ["refund", "refund_amount", "退款", "退款金额", "售后金额", "退货金额", "退款额"],
    # 推广花费
    "ad_cost": ["ad_cost", "广告费", "推广费", "投放花费", "营销费用", "推广花费", "广告花费", "推广支出"],
}


def auto_map_fields(df):
    """
    自动识别 DataFrame 中的字段映射。

    参数:
        df: Pandas DataFrame

    返回:
        mapping: dict — {标准字段名: 原始列名 或 None}
        unmatched: list — 未匹配的原始列名
    """
    # 标准字段的优先级顺序
    field_priority = [
        "date", "gmv", "orders", "uv", "pv", "platform",
        "category", "product_name", "refund_amount", "ad_cost"
    ]

    mapping = {key: None for key in STANDARD_FIELDS}
    used_columns = set()

    # 按优先级匹配每个标准字段
    for std_field in field_priority:
        aliases = FIELD_ALIASES.get(std_field, [std_field])

        for col in df.columns:
            col_str = str(col).strip().lower()
            if col in used_columns:
                continue
            for alias in aliases:
                alias_lower = alias.strip().lower()
                # 完全匹配 或 包含匹配（中文）
                if col_str == alias_lower or col_str.find(alias_lower) != -1:
                    mapping[std_field] = col
                    used_columns.add(col)
                    break
            if mapping[std_field] is not None:
                break

    # 未匹配的列
    unmatched = [col for col in df.columns if col not in used_columns]

    return mapping, unmatched


def get_available_options(df, mapped_field):
    """
    获取某个标准字段的可选原始列名列表（用于手动映射的下拉框）。

    参数:
        df: Pandas DataFrame
        mapped_field: 已映射的原始列名（可能为 None）

    返回:
        options: list — 可选的原始列名，第一个是"未选择"
        current_index: int — 当前选中项的索引
    """
    options = ["未选择"] + list(df.columns)
    if mapped_field and mapped_field in df.columns:
        current_index = options.index(mapped_field)
    else:
        current_index = 0
    return options, current_index
