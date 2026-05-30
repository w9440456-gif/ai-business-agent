"""
AI 企业经营分析 Agent 主程序
============================
基于 Streamlit 的交互式经营数据分析系统。
支持结构化 Excel/CSV 数据上传、字段映射、数据清洗、指标计算、
可视化分析、异常识别、AI 报告生成和自然语言问数。

启动方式：
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# 设置页面配置（必须在最前面）
st.set_page_config(
    page_title="AI 企业经营分析 Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入模块
from modules.data_loader import load_data, load_sample_data
from modules.data_validator import validate_structure
from modules.field_mapper import auto_map_fields, STANDARD_FIELDS
from modules.data_cleaner import clean_data
from modules.metrics import calculate_metrics, aggregate_by_date, aggregate_by_category, aggregate_by_platform
from modules.visualization import (
    plot_gmv_trend, plot_orders_trend, plot_category_top10,
    plot_platform_contribution, plot_refund_rate, plot_roi, plot_conversion_rate
)
from modules.anomaly_detection import detect_anomalies
from modules.ai_report import generate_ai_report, generate_context_for_qa
from modules.qa_agent import answer_business_question
from config.prompts import PROMPT_CONFIG, REPORTER_REPORT_PROMPT, FUNCTION_CALLING_TOOLS
from utils.helpers import format_number, format_percent, safe_divide, check_api_key


# ============ 页面标题 ============
st.title("📊 AI 企业经营分析 Agent")
st.markdown(
    """
    <div style="color: #666; font-size: 16px; margin-bottom: 20px;">
    上传结构化经营数据，自动生成指标看板、异常诊断与经营分析报告
    </div>
    """,
    unsafe_allow_html=True,
)

# ============ 辅助函数 ============
def _get_field_desc(std_field):
    """获取标准字段的中文描述"""
    descs = {
        "date": "日期",
        "platform": "平台",
        "category": "品类",
        "product_name": "商品名称",
        "gmv": "销售额",
        "orders": "订单量",
        "uv": "访客数",
        "pv": "浏览量",
        "refund_amount": "退款金额",
        "ad_cost": "推广花费",
    }
    return descs.get(std_field, "")


# ============ 初始化 Session State ============
if "df" not in st.session_state:
    st.session_state.df = None
if "field_mapping" not in st.session_state:
    st.session_state.field_mapping = None
if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "cleaning_log" not in st.session_state:
    st.session_state.cleaning_log = None
if "quality_issues" not in st.session_state:
    st.session_state.quality_issues = None
if "anomalies" not in st.session_state:
    st.session_state.anomalies = None
if "date_agg" not in st.session_state:
    st.session_state.date_agg = None
if "cat_agg" not in st.session_state:
    st.session_state.cat_agg = None
if "plat_agg" not in st.session_state:
    st.session_state.plat_agg = None
if "data_source" not in st.session_state:
    st.session_state.data_source = None  # "uploaded" 或 "sample"
if "unmatched" not in st.session_state:
    st.session_state.unmatched = None
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "qa_messages" not in st.session_state:
    st.session_state.qa_messages = []
if "qa_context" not in st.session_state:
    st.session_state.qa_context = None
if "ai_available" not in st.session_state:
    st.session_state.ai_available = False


# ============ 检查 AI 可用性 ============
st.session_state.ai_available, _ = check_api_key()


# ============ Tab 布局 ============
tab_names = [
    "📤 数据上传与预览",
    "🔗 字段映射与数据清洗",
    "📊 核心指标看板",
    "📈 可视化分析",
    "⚠️ 异常识别",
    "🤖 AI 经营分析报告",
    "💬 AI 问数助手",
]
tabs = st.tabs(tab_names)


# ======================================================
# Tab 1: 数据上传与预览
# ======================================================
with tabs[0]:
    st.subheader("上传经营数据")

    # 说明
    st.info(
        "📋 支持的格式：.csv（推荐 UTF-8 编码）或 .xlsx 文件。"
        "要求第一行为字段名，每列一个变量，每行一条记录。"
        "不支持合并单元格、多行表头或交叉表格式。"
    )

    # 标准模板下载
    template_path = os.path.join(os.path.dirname(__file__), "data", "standard_template.csv")
    if os.path.exists(template_path):
        with open(template_path, "rb") as f:
            template_bytes = f.read()
        st.download_button(
            label="📥 下载标准模板",
            data=template_bytes,
            file_name="standard_template.csv",
            mime="text/csv",
            help="下载标准字段模板，按此格式准备数据可获得最佳分析效果",
        )

    # 文件上传区域
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "选择 CSV 或 Excel 文件",
            type=["csv", "xlsx", "xls"],
            help="上传包含经营数据的文件",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_sample = st.button("📋 使用样例数据体验", type="secondary")

    # 处理数据加载
    df = None
    data_source = None

    if uploaded_file is not None:
        # 用户上传了文件
        with st.spinner("正在读取数据..."):
            df, error = load_data(uploaded_file)
            if error:
                st.error(error)
            else:
                data_source = "uploaded"
    elif use_sample:
        # 使用样例数据
        with st.spinner("正在加载样例数据..."):
            df, error = load_sample_data()
            if error:
                st.error(error)
            else:
                data_source = "sample"
                st.success("已加载样例数据（1000 行电商经营数据）")

    if df is not None:
        # 保存到 session state
        st.session_state.df = df
        st.session_state.data_source = data_source

        # 数据格式校验
        with st.spinner("正在校验数据格式..."):
            passed, issues, suggestions = validate_structure(df)

        if not passed:
            st.warning("⚠️ 数据格式需要调整")
            for issue in issues:
                st.write(f"- {issue}")
            for suggestion in suggestions:
                st.write(f"💡 建议：{suggestion}")
            st.info(
                "当前版本主要支持结构化经营明细数据，"
                "请将表格整理为「一行一条记录、一列一个字段」的格式后重新上传。"
            )

        # 数据预览
        st.subheader("数据预览")
        st.write(f"数据量：{len(df)} 行 × {len(df.columns)} 列")

        # 显示前 10 行
        st.dataframe(df.head(10))

        # 数据基本信息
        with st.expander("查看数据基本信息"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**字段列表**")
                for col in df.columns:
                    dtype = str(df[col].dtype)
                    non_null = df[col].notna().sum()
                    st.write(f"- {col}（{dtype}，{non_null}/{len(df)} 非空）")
            with col2:
                st.write("**数值字段统计**")
                numeric_cols = df.select_dtypes(include=["number"]).columns
                if len(numeric_cols) > 0:
                    st.dataframe(df[numeric_cols].describe())
                else:
                    st.write("未检测到数值字段")

        # 自动字段映射
        st.session_state.field_mapping, st.session_state.unmatched = auto_map_fields(df)
        st.success(
            f"已自动识别字段映射。请进入「字段映射与数据清洗」Tab 检查和调整。"
        )

    elif uploaded_file is None and not use_sample:
        # 未上传文件，显示提示
        st.markdown("""
        <div style="text-align: center; padding: 40px 20px; color: #999;">
            <div style="font-size: 48px; margin-bottom: 10px;">📂</div>
            <div style="font-size: 18px; margin-bottom: 8px;">请上传经营数据文件</div>
            <div style="font-size: 14px;">
                支持 CSV 和 Excel 格式<br>
                或点击「使用样例数据」快速体验
            </div>
        </div>
        """, unsafe_allow_html=True)


# ======================================================
# Tab 2: 字段映射与数据清洗
# ======================================================
with tabs[1]:
    st.subheader("字段映射与数据清洗")

    if st.session_state.df is None:
        st.info("请先在「数据上传与预览」Tab 中上传数据或加载样例数据。")
    elif st.session_state.field_mapping is None:
        st.warning("字段映射尚未初始化，请先在数据上传 Tab 中加载数据。")
    else:
        df = st.session_state.df
        field_mapping = st.session_state.field_mapping

        # ---- 字段映射 ----
        st.markdown("### 字段映射")
        st.markdown(
            "系统已自动识别部分字段，如有偏差可在下拉框中手动调整。"
            "标注 ✅ 为已匹配，标注 ❌ 为未匹配。"
        )

        mapping_display = {}
        for std_field in STANDARD_FIELDS:
            original = field_mapping.get(std_field)

            # 构建下拉选项
            options = ["未选择"] + list(df.columns)
            current = options.index(original) if original in df.columns else 0

            selected = st.selectbox(
                f"**{std_field}**（{_get_field_desc(std_field)}）",
                options=options,
                index=current,
                key=f"map_{std_field}",
            )

            mapping_display[std_field] = selected if selected != "未选择" else None

        if st.button("✅ 确认字段映射并进入数据清洗", type="primary"):
            st.session_state.field_mapping = mapping_display

            # 执行数据清洗
            with st.spinner("正在清洗数据..."):
                cleaned_df, cleaning_log, quality_issues = clean_data(
                    df, mapping_display
                )

                # 计算指标
                metrics = calculate_metrics(cleaned_df, mapping_display)

                # 聚合数据
                date_agg = aggregate_by_date(cleaned_df, mapping_display)
                cat_agg = aggregate_by_category(cleaned_df, mapping_display)
                plat_agg = aggregate_by_platform(cleaned_df, mapping_display)

                # 异常检测
                anomalies = detect_anomalies(
                    cleaned_df,
                    mapping_display,
                    {"date_agg": date_agg, "cat_agg": cat_agg, "plat_agg": plat_agg},
                    metrics,
                )

                # 保存到 session state
                st.session_state.cleaned_df = cleaned_df
                st.session_state.metrics = metrics
                st.session_state.cleaning_log = cleaning_log
                st.session_state.quality_issues = quality_issues
                st.session_state.anomalies = anomalies
                st.session_state.date_agg = date_agg
                st.session_state.cat_agg = cat_agg
                st.session_state.plat_agg = plat_agg

                # 数据更新后重置缓存
                st.session_state.qa_messages = []
                st.session_state.qa_context = None
                st.session_state.pop("docx_bytes_basic", None)
                st.session_state.pop("docx_bytes_basic_ok", None)

                st.success("数据清洗和指标计算完成！请切换到其他 Tab 查看分析结果。")

        # ---- 未映射字段 ----
        if st.session_state.unmatched:
            st.markdown("#### 未匹配的原始字段")
            for col in st.session_state.unmatched:
                st.write(f"- {col}")
            st.caption("这些字段未被映射到标准字段，不会影响分析功能。")

        # ---- 显示清洗结果（如果已有） ----
        if st.session_state.cleaned_df is not None:
            st.markdown("---")
            st.markdown("### 数据清洗结果")

            # 清洗日志
            with st.expander("📋 清洗操作日志", expanded=True):
                for log in st.session_state.cleaning_log:
                    st.write(f"- ✅ {log}")

            # 数据质量问题
            if st.session_state.quality_issues:
                with st.expander("⚠️ 数据质量问题", expanded=True):
                    for issue in st.session_state.quality_issues:
                        st.warning(issue)
            else:
                st.success("未发现数据质量问题，数据质量较好。")

            # 清洗后数据预览
            with st.expander("查看清洗后的数据"):
                st.dataframe(st.session_state.cleaned_df.head(10))


# ======================================================
# Tab 3: 核心指标看板
# ======================================================
with tabs[2]:
    st.subheader("核心经营指标")

    if st.session_state.metrics is None:
        st.info("请先在「字段映射与数据清洗」Tab 中完成字段映射和数据处理。")
    else:
        metrics = st.session_state.metrics
        keys = metrics.get("_keys_present", [])

        # 指标卡片
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            gmv = metrics.get("总销售额 (GMV)", 0)
            st.metric("总销售额 (GMV)", format_number(gmv))

        with col2:
            orders = metrics.get("总订单量", 0)
            st.metric("总订单量", format_number(orders))

        with col3:
            if "gmv" in keys and "orders" in keys:
                avg = metrics.get("平均客单价", 0)
                st.metric("平均客单价", format_number(avg))
            else:
                st.metric("平均客单价", "—")

        with col4:
            if "refund" in keys:
                rate = metrics.get("退款率", 0)
                st.metric("退款率", format_percent(rate))
            else:
                st.metric("退款率", "—")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if "ad" in keys:
                roi = metrics.get("ROI (投产比)", 0)
                st.metric("ROI (投产比)", f"{roi:.2f}")
            else:
                st.metric("ROI (投产比)", "—")

        with col2:
            if "uv" in keys:
                uv = metrics.get("总访客数 (UV)", 0)
                st.metric("总访客数 (UV)", format_number(uv))
            else:
                st.metric("总访客数 (UV)", "—")

        with col3:
            if "orders" in keys and "uv" in keys:
                conv = metrics.get("转化率", 0)
                st.metric("转化率", format_percent(conv))
            else:
                st.metric("转化率", "—")

        with col4:
            if "ad" in keys:
                ad = metrics.get("总推广花费", 0)
                st.metric("总推广花费", format_number(ad))
            else:
                st.metric("总推广花费", "—")

        st.markdown("---")
        st.caption("指标说明：GMV = 成交总额 | 客单价 = GMV / 订单量 | ROI = GMV / 推广花费 | 退款率 = 退款金额 / GMV | 转化率 = 订单量 / 访客数")

        # ---- 导出 Word 报告按钮 ----
        st.markdown("---")
        st.markdown("### 📄 导出报告")

        # 在 session state 中缓存 Word 文档字节，避免每次重绘时重新生成
        if "docx_bytes_basic" not in st.session_state:
            from modules.report_export import export_report_to_docx
            success, data = export_report_to_docx(
                metrics=st.session_state.metrics,
                anomalies=st.session_state.anomalies,
                field_mapping=st.session_state.field_mapping,
                ai_report=None,
            )
            if success:
                st.session_state.docx_bytes_basic = data
                st.session_state.docx_bytes_basic_ok = True
            else:
                st.session_state.docx_bytes_basic_ok = False
                st.session_state.docx_bytes_basic_error = data

        if st.session_state.get("docx_bytes_basic_ok"):
            st.download_button(
                label="📥 下载 Word 经营分析报告（基础版）",
                data=st.session_state.docx_bytes_basic,
                file_name=f"企业经营分析报告_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
            )


# ======================================================
# Tab 4: 可视化分析
# ======================================================
with tabs[3]:
    st.subheader("可视化分析")

    if st.session_state.metrics is None:
        st.info("请先在「字段映射与数据清洗」Tab 中完成数据处理。")
    else:
        field_mapping = st.session_state.field_mapping
        date_agg = st.session_state.date_agg
        cat_agg = st.session_state.cat_agg
        plat_agg = st.session_state.plat_agg

        date_col = field_mapping.get("date")
        gmv_col = field_mapping.get("gmv")
        orders_col = field_mapping.get("orders")
        uv_col = field_mapping.get("uv")
        pv_col = field_mapping.get("pv")
        refund_col = field_mapping.get("refund_amount")
        ad_col = field_mapping.get("ad_cost")
        cat_col = field_mapping.get("category")
        plat_col = field_mapping.get("platform")

        # 第一行：销售额 + 订单量趋势
        col1, col2 = st.columns(2)
        with col1:
            if date_col and gmv_col and not date_agg.empty:
                fig = plot_gmv_trend(date_agg, date_col, gmv_col)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("暂无销售额趋势数据")

        with col2:
            if date_col and orders_col and not date_agg.empty:
                fig = plot_orders_trend(date_agg, date_col, orders_col)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("暂无订单量趋势数据")

        # 第二行：品类 Top10 + 平台贡献
        col1, col2 = st.columns(2)
        with col1:
            if cat_col and cat_agg is not None and not cat_agg.empty:
                fig = plot_category_top10(cat_agg, cat_col)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("暂无品类分析数据")

        with col2:
            if plat_col and plat_agg is not None and not plat_agg.empty:
                fig = plot_platform_contribution(plat_agg, plat_col)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("暂无平台分析数据")

        # 第三行：退款率 + ROI + 转化率
        col1, col2, col3 = st.columns(3)

        with col1:
            if date_col and refund_col and gmv_col and not date_agg.empty:
                fig = plot_refund_rate(date_agg, date_col, refund_col, gmv_col)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("暂无退款率数据")

        with col2:
            if date_col and gmv_col and ad_col and not date_agg.empty:
                fig = plot_roi(date_agg, date_col, gmv_col, ad_col)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("暂无 ROI 数据")

        with col3:
            if date_col and orders_col and uv_col and not date_agg.empty:
                fig = plot_conversion_rate(date_agg, date_col, orders_col, uv_col)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("暂无转化率数据")


# ======================================================
# Tab 5: 异常识别
# ======================================================
with tabs[4]:
    st.subheader("经营异常识别")

    if st.session_state.anomalies is None:
        st.info("请先在「字段映射与数据清洗」Tab 中完成数据处理。")
    else:
        anomalies = st.session_state.anomalies

        if len(anomalies) == 1 and anomalies[0]["type"] == "暂无异常":
            st.success("🎉 基于当前数据，未检测到明显的经营异常情况。")
        else:
            st.markdown(f"共检测到 {len(anomalies)} 个经营异常点")

            for i, anomaly in enumerate(anomalies):
                severity = anomaly.get("severity", "低")
                sev_color = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(severity, "⚪")

                with st.expander(
                    f"{sev_color} [{severity}] {anomaly.get('type', '未知异常')}",
                    expanded=(severity == "高"),
                ):
                    st.markdown(f"**异常描述：** {anomaly.get('description', '')}")

                    causes = anomaly.get("possible_causes", [])
                    if causes:
                        st.markdown("**可能原因：**")
                        for cause in causes:
                            st.markdown(f"- {cause}")

                    suggest = anomaly.get("suggest_metrics", "")
                    if suggest:
                        st.markdown(f"**建议关注指标：** {suggest}")

        # 聚合数据展示
        st.markdown("---")
        st.markdown("### 详细数据参考")

        tab_d, tab_c, tab_p = st.tabs(["按日期汇总", "按品类汇总", "按平台汇总"])

        with tab_d:
            if st.session_state.date_agg is not None and not st.session_state.date_agg.empty:
                st.dataframe(st.session_state.date_agg)
            else:
                st.info("暂无按日期汇总数据")

        with tab_c:
            if st.session_state.cat_agg is not None and not st.session_state.cat_agg.empty:
                st.dataframe(st.session_state.cat_agg)
            else:
                st.info("暂无按品类汇总数据")

        with tab_p:
            if st.session_state.plat_agg is not None and not st.session_state.plat_agg.empty:
                st.dataframe(st.session_state.plat_agg)
            else:
                st.info("暂无按平台汇总数据")


# ======================================================
# Tab 6: AI 经营分析报告
# ======================================================
with tabs[5]:
    st.subheader("AI 经营分析报告")

    if st.session_state.anomalies is None:
        st.info("请先在「字段映射与数据清洗」Tab 中完成数据处理。")
    else:
        # 检查 API Key
        if not st.session_state.ai_available:
            st.warning(
                "⚠️ 请先配置 API Key 即可使用 AI 经营分析报告功能。"
            )
            st.markdown("""
            配置方式：
            1. 在项目根目录创建 `.env` 文件（可复制 `.env.example`）
            2. 填入你的 API Key

            使用 DeepSeek API（推荐）：
            ```
            OPENAI_API_KEY=sk-your-deepseek-api-key
            OPENAI_MODEL=deepseek-chat
            OPENAI_BASE_URL=https://api.deepseek.com/v1
            ```

            或使用 OpenAI API：
            ```
            OPENAI_API_KEY=sk-your-openai-api-key
            OPENAI_MODEL=gpt-4o-mini
            ```
            3. 重启应用（Ctrl+C 后重新运行）即可使用
            """)
        else:
            if st.button("🤖 生成 AI 经营分析报告", type="primary", width="stretch"):
                with st.spinner("AI 正在分析数据并生成报告，请稍候..."):
                    # 准备指标摘要文本
                    metrics = st.session_state.metrics
                    metrics_text = "\n".join(
                        [f"- {k}: {v}" for k, v in metrics.items() if not k.startswith("_")]
                    )

                    # 准备聚合摘要
                    agg_text = ""
                    if st.session_state.date_agg is not None and not st.session_state.date_agg.empty:
                        agg_text += f"\n按日期汇总数据：\n{st.session_state.date_agg.describe().to_string()}\n"
                    if st.session_state.cat_agg is not None and not st.session_state.cat_agg.empty:
                        agg_text += f"\n按品类汇总数据：\n{st.session_state.cat_agg.to_string()}\n"
                    if st.session_state.plat_agg is not None and not st.session_state.plat_agg.empty:
                        agg_text += f"\n按平台汇总数据：\n{st.session_state.plat_agg.to_string()}\n"

                    # 准备异常摘要
                    anomalies_text = "\n".join(
                        [f"- [{a['severity']}] {a['type']}: {a['description']}"
                         for a in st.session_state.anomalies]
                    )

                    success, result = generate_ai_report(metrics_text, agg_text, anomalies_text)

                    if success:
                        st.success("AI 经营分析报告已生成！")
                        st.session_state.last_report = result
                        st.markdown(result)

                        # 预生成含 AI 报告的 Word 文档，供下载
                        from modules.report_export import export_report_to_docx
                        _, docx_bytes = export_report_to_docx(
                            metrics=st.session_state.metrics,
                            anomalies=st.session_state.anomalies,
                            field_mapping=st.session_state.field_mapping,
                            ai_report=result,
                        )
                        st.markdown("---")
                        st.download_button(
                            label="📥 下载含 AI 报告的 Word 文档",
                            data=docx_bytes,
                            file_name=f"企业经营分析报告_含AI分析_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            width="stretch",
                        )
                    else:
                        st.error(result)

            # 显示上次生成的报告（点击其他 Tab 回来后仍然可见）
            if st.session_state.get("last_report"):
                st.markdown("---")
                st.markdown("### 上次生成的报告")
                st.markdown(st.session_state.last_report)


# ======================================================
# Tab 7: AI 问数助手（多轮对话）
# ======================================================
with tabs[6]:
    st.subheader("AI 问数助手")

    if st.session_state.anomalies is None:
        st.info("请先在「字段映射与数据清洗」Tab 中完成数据处理。")
    else:
        if not st.session_state.ai_available:
            st.warning("⚠️ 请先配置 API Key 即可使用 AI 问数助手功能。")
        else:
            # ---- 初始化对话历史 ----
            if "qa_messages" not in st.session_state:
                st.session_state.qa_messages = []  # [{"role": "user"|"assistant", "content": str}]
            if "qa_context" not in st.session_state:
                st.session_state.qa_context = None

            # ---- 首次访问时准备数据上下文（后续复用） ----
            if st.session_state.qa_context is None:
                metrics = st.session_state.metrics
                metrics_text = "\n".join(
                    [f"- {k}: {v}" for k, v in metrics.items() if not k.startswith("_")]
                )
                agg_text = ""
                if st.session_state.date_agg is not None and not st.session_state.date_agg.empty:
                    agg_text += f"\n按日期汇总数据：\n{st.session_state.date_agg.describe().to_string()}\n"
                if st.session_state.cat_agg is not None and not st.session_state.cat_agg.empty:
                    agg_text += f"\n按品类汇总数据：\n{st.session_state.cat_agg.to_string()}\n"
                if st.session_state.plat_agg is not None and not st.session_state.plat_agg.empty:
                    agg_text += f"\n按平台汇总数据：\n{st.session_state.plat_agg.to_string()}\n"
                anomalies_text = "\n".join(
                    [f"- [{a['severity']}] {a['type']}: {a['description']}"
                     for a in st.session_state.anomalies]
                )
                st.session_state.qa_context = generate_context_for_qa(
                    metrics_text, agg_text, anomalies_text, st.session_state.field_mapping
                )

            # ---- 对话记录显示区域 ----
            chat_container = st.container()
            with chat_container:
                if not st.session_state.qa_messages:
                    st.info("开始对话吧！可以问我关于经营数据的任何问题，也可以点击下方的快捷提问。")
                else:
                    for msg in st.session_state.qa_messages:
                        if msg["role"] == "user":
                            st.markdown(f"> **问：** {msg['content']}")
                        else:
                            st.markdown(f"**答：** {msg['content']}")
                        st.markdown("---")

            st.markdown("")

            # ---- 快捷按钮行 ----
            preset_questions = [
                "整体经营情况怎么样？",
                "哪个品类表现最好？",
                "哪个平台 ROI 最低？",
                "退款率异常在哪里？",
                "应该重点优化哪些方面？",
                "推广效率怎么样？",
                "这份数据说明了什么问题？",
            ]
            clicked_question = None
            cols = st.columns(4)
            for i, q in enumerate(preset_questions):
                with cols[i % 4]:
                    if st.button(q, key=f"qa_preset_{i}", width="stretch"):
                        clicked_question = q

            # ---- 输入框 + 操作按钮行 ----
            st.markdown("---")
            col_inp, col_ask, col_clear = st.columns([4, 1, 1])
            with col_inp:
                user_question = st.text_input(
                    "输入你的经营分析问题（Enter 发送）：",
                    placeholder="例如：本月销售额为什么下降？",
                    label_visibility="collapsed",
                    key="qa_input",
                )
            with col_ask:
                ask_button = st.button("💬 发送", type="primary", width="stretch")
            with col_clear:
                if st.button("🗑️ 清空对话", width="stretch"):
                    st.session_state.qa_messages = []
                    st.rerun()

            # ---- 确定当前要问的问题，并触发回答 ----
            question = clicked_question if clicked_question else (user_question if ask_button else None)

            if question and question.strip():
                # 加到历史中
                st.session_state.qa_messages.append({"role": "user", "content": question})

                with st.spinner("AI 正在分析你的问题..."):
                    # 除当前问题外的历史记录传给 API
                    history_for_api = [
                        m for m in st.session_state.qa_messages[:-1]
                    ]
                    success, answer = answer_business_question(
                        question,
                        st.session_state.qa_context,
                        history=history_for_api,
                    )

                if success:
                    st.session_state.qa_messages.append({"role": "assistant", "content": answer})
                else:
                    # 错误回退：移除刚加的用户问题
                    st.session_state.qa_messages.pop()
                    st.error(answer)

                st.rerun()


# ======================================================
# Tab 8: 多 Agent 流水线
# ======================================================
tabs_agent = st.tabs([""])[0]  # 占位，实际我们手动管理
# 用 expander 方式展示在 AI 报告 Tab 后面
with tabs[5]:  # 在 AI 报告 Tab 底部增加 Agent 模式
    pass

# 在 AI 问数 Tab 后面加一个独立区域
st.markdown("---")
st.markdown("### 🤖 Agent 协作流水线（进阶模式）")
with st.expander("点击展开 Agent 流水线（Analyser → Reporter → Critic）", expanded=False):
    st.markdown("""
    **多 Agent 协作流程：**
    1. **Analyser（数据分析师）**：分析数据，支持 Function Calling 工具调用
    2. **Reporter（报告撰写师）**：基于分析结果生成结构化报告
    3. **Critic（质量评审师）**：对报告进行评分和改进建议
    """)

    if st.session_state.anomalies is None:
        st.info("请先在「字段映射与数据清洗」Tab 中完成数据处理。")
    elif not st.session_state.ai_available:
        st.warning("⚠️ 需要配置 API Key 才能运行 Agent 流水线。")
    else:
        agent_question = st.text_input(
            "输入分析问题（Agent 将自动调用工具分析数据并生成报告）：",
            placeholder="例如：请分析整体经营情况，重点关注异常...",
            key="agent_pipeline_input",
        )
        if st.button("🚀 运行完整 Agent 流水线", type="primary", width="stretch"):
            with st.spinner("正在依次执行 Analyser → Reporter → Critic..."):
                from core.multi_agent import run_multi_agent_pipeline
                question = agent_question.strip() or "请分析整体经营情况"
                success, result_data = run_multi_agent_pipeline(
                    df=st.session_state.cleaned_df,
                    field_mapping=st.session_state.field_mapping,
                    user_question=question,
                )

                if success:
                    outputs = result_data.get("stage_outputs", {})

                    # Analyser 输出
                    analyser_out = outputs.get("Analyser", {})
                    st.success("✅ Analyser 分析完成")
                    if analyser_out.get("success"):
                        with st.expander("📊 Analyser 分析结果", expanded=False):
                            st.markdown(analyser_out.get("answer", "无输出"))

                    # Reporter 输出
                    reporter_out = outputs.get("Reporter", {})
                    if reporter_out.get("success"):
                        st.success("✅ Reporter 报告生成完成")
                        report_text = reporter_out.get("report", "")
                        st.session_state.last_report = report_text
                        with st.expander("📄 Reporter 经营分析报告", expanded=True):
                            st.markdown(report_text)
                    else:
                        st.warning(f"Reporter 报告生成失败: {reporter_out.get('report', '')}")

                    # Critic 输出
                    critic_out = outputs.get("Critic", {})
                    if critic_out.get("success"):
                        st.success("✅ Critic 质量评审完成")
                        with st.expander("📝 Critic 质量评分与改进建议", expanded=True):
                            st.markdown(critic_out.get("critique", "无输出"))
                else:
                    error_info = result_data.get("error", "未知错误")
                    st.error(f"Agent 流水线执行失败：{error_info}")
                    stage_outputs = result_data.get("stage_outputs", {})
                    if stage_outputs:
                        with st.expander("查看已完成的阶段输出"):
                            for sname, sout in stage_outputs.items():
                                st.markdown(f"**{sname}**")
                                st.markdown(str(sout.get("answer", sout.get("report", sout.get("critique", "无"))))[:500])


# ============ 辅助函数 ============
# ============ 页脚 ============
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #999; font-size: 12px; padding: 10px;">
        AI 企业经营分析 Agent v1.0 | 基于 Streamlit + Pandas + Plotly + OpenAI API
    </div>
    """,
    unsafe_allow_html=True,
)
