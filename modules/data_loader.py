"""数据加载模块：支持 CSV 和 XLSX 文件读取"""

import pandas as pd
import io


def load_data(uploaded_file):
    """
    读取上传的文件（CSV 或 XLSX），返回 Pandas DataFrame。

    参数:
        uploaded_file: Streamlit 上传的文件对象

    返回:
        df: Pandas DataFrame（成功时）
        error_msg: 错误信息（失败时返回 None）
    """
    try:
        # 获取文件名
        file_name = uploaded_file.name

        # 根据文件扩展名选择读取方式
        if file_name.endswith(".csv"):
            # CSV 文件：尝试多种编码读取
            encodings = ["utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"]
            for enc in encodings:
                try:
                    # 读取文件内容
                    content = uploaded_file.getvalue()
                    df = pd.read_csv(io.BytesIO(content), encoding=enc)
                    return df, None
                except (UnicodeDecodeError, Exception):
                    continue
            return None, "无法解析 CSV 文件编码，请尝试另存为 UTF-8 编码的 CSV 后重新上传。"

        elif file_name.endswith((".xlsx", ".xls")):
            # Excel 文件
            content = uploaded_file.getvalue()
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
            return df, None

        else:
            return None, f"不支持的文件格式：{file_name}。当前仅支持 .csv、.xlsx、.xls 格式。"

    except Exception as e:
        return None, f"文件读取失败：{str(e)}"


def load_sample_data():
    """加载内置的样例数据"""
    try:
        import os
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ecommerce_data.csv"
        )
        df = pd.read_csv(sample_path, encoding="utf-8-sig")
        return df, None
    except Exception as e:
        return None, f"样例数据加载失败：{str(e)}"
