"""数据格式校验模块"""

import pandas as pd


# 标准字段（用于判断数据是否包含经营数据相关字段）
STANDARD_FIELDS = {
    "date": ["date", "日期", "时间", "下单时间", "支付时间", "统计日期", "交易时间"],
    "gmv": ["gmv", "销售额", "成交金额", "支付金额", "收入", "营业收入", "交易金额", "销售金额", "金额"],
    "orders": ["orders", "订单量", "订单数", "成交订单", "支付订单", "销量", "数量"],
    "uv": ["uv", "访客数", "用户数", "访问用户"],
    "pv": ["pv", "浏览量", "访问量", "页面浏览量"],
}


def validate_structure(df):
    """
    校验上传数据是否满足结构化要求。

    参数:
        df: Pandas DataFrame

    返回:
        passed: bool — 是否通过校验
        issues: list — 问题列表
        suggestions: list — 修改建议列表
    """
    issues = []
    suggestions = []
    passed = True

    # 1. 是否为空表
    if df is None or df.empty:
        return False, ["数据集为空，没有任何数据行。"], ["请上传包含数据的文件。"]

    # 2. 列数是否过少
    if len(df.columns) < 2:
        issues.append(f"列数过少（{len(df.columns)} 列），正常经营数据应至少包含 3-5 个字段。")
        suggestions.append("请检查文件格式，确保每一列代表一个字段。")
        passed = False

    # 3. 行数是否过少
    if len(df) < 5:
        issues.append(f"行数过少（{len(df)} 行），数据分析需要至少 5 条以上记录。")
        suggestions.append("请补充更多经营数据后重新上传。")
        passed = False

    # 4. 是否存在大量空列
    empty_cols = [col for col in df.columns if df[col].isnull().all()]
    if len(empty_cols) > 0:
        issues.append(f"存在 {len(empty_cols)} 个完全为空的列：{', '.join(empty_cols[:5])}")
        suggestions.append("建议删除空列后重新上传。")
        passed = False

    # 5. 是否存在重复列名
    if len(df.columns) != len(set(df.columns)):
        dup_cols = [col for col in df.columns if list(df.columns).count(col) > 1]
        dup_cols = list(set(dup_cols))
        issues.append(f"存在重复列名：{', '.join(dup_cols)}。")
        suggestions.append("请确保每个字段有唯一的列名。")

    # 6. 是否看起来像结构化数据
    # 检查列名中是否有纯序号列名（如 0,1,2...），可能是数据未正确解析
    numeric_col_count = sum(
        1 for col in df.columns if
        (isinstance(col, (int, float)) or
         (isinstance(col, str) and col.isdigit()))
    )
    if numeric_col_count > len(df.columns) * 0.5:
        issues.append("大部分列名是数字序号，数据可能未正确解析。")
        suggestions.append("请确保文件第一行是字段名，而非数据。检查文件格式后重新上传。")
        passed = False

    # 7. 检查是否包含经营数据字段
    all_col_names = [str(c).lower().strip() for c in df.columns]
    found_fields = set()
    for field_type, aliases in STANDARD_FIELDS.items():
        for col in all_col_names:
            for alias in aliases:
                if col == alias or col.startswith(alias) or alias in col:
                    found_fields.add(field_type)
                    break

    if len(found_fields) < 2:
        issues.append(
            f"数据中未识别到足够的经营指标字段（日期、销售额、订单量等）。"
        )
        suggestions.append(
            "推荐字段：date（日期）、gmv（销售额）、orders（订单量）。"
            "可下载标准模板参考格式。"
        )
        passed = False

    return passed, issues, suggestions
