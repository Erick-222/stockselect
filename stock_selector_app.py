import streamlit as st
import pandas as pd
import numpy as np
import subprocess
import os
import time
import io

DATA_FILE = '股票综合数据_含极值财务估值.xlsx'
ALL_SCRIPT = 'ALL.py'

st.set_page_config(page_title="A股选股系统", layout="wide")
st.title("📊 A股选股系统（最终修复版，2位小数 + 全部显示）")

# ================= 数据更新按钮 ==================
update_col, info_col = st.columns([1,3])
with update_col:
    if st.button("🔄 更新数据库"):
        if os.path.exists(ALL_SCRIPT):
            with st.spinner("🚀 正在执行 ALL.py 更新数据库，请稍等..."):
                subprocess.run(["python", ALL_SCRIPT])
            if os.path.exists(DATA_FILE):
                mtime = os.path.getmtime(DATA_FILE)
                last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                st.success(f"✅ 数据库更新完成！文件最后修改时间: {last_update}")
            else:
                st.error("❌ 更新完成，但未找到 Excel 文件")
        else:
            st.error(f"❌ 未找到 {ALL_SCRIPT}")

# ================= 加载数据 ==================
@st.cache_data
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE)

        # 去掉列名前后空格和不可见字符
        df.columns = df.columns.str.strip()

        # 打印列名，方便调试
        # st.write(df.columns.tolist())

        # 统一关键列名
        rename_map = {
            '2025营业总收入年增长率 ': '2025营业总收入年增长率',
            '2026年第一季度增长率 ': '2026年第一季度增长率',
            '2025归母净利润增长率': '2025归母净利润增长率',
            '2026Q1归母净利润增长率': '2026Q1归母净利润增长率',
            '2025归母净利润增长': '年度增长率',
            '2026Q1归母净利润增长': '季度增长率'
        }
        df.rename(columns=rename_map, inplace=True)

        # 转换为数值类型
        percent_cols = ['年度增长率','季度增长率',
                        '2025归母净利润增长率','2026Q1归母净利润增长率',
                        '2025营业总收入年增长率','2026年第一季度增长率']
        for col in percent_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.rstrip('%'), errors='coerce')

        # 增长率转换为百分比格式并保留2位小数
        growth_cols = ['2025营业总收入年增长率','2026年第一季度增长率',
                       '2025归母净利润增长率','2026Q1归母净利润增长率']
        for col in growth_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
                # 存储为字符串格式的百分比
                df[col] = df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else x)

        # 营收和利润以万元为单位，取整
        revenue_profit_cols = ['2025营业总收入','2026Q1营业总收入',
                               '2025_归母净利润','2026Q1_归母净利润']
        for col in revenue_profit_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(0)

        # 其他数字保留2位小数
        other_num_cols = ['当前价','最高价','最低价','pe_ttm','pb',
                          '最高相对昨收%','最低相对昨收%']
        for col in other_num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

        # 日期
        for col in ['最高价时间','最低价时间']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.date

        if 'industry' not in df.columns:
            df['industry'] = "N/A"

        return df
    else:
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.warning("⚠️ 数据为空，请先更新数据库")
    st.stop()

# ================= 侧边栏 ==================
with st.sidebar:
    st.header("筛选条件")

    # 当前价
    use_price = st.checkbox("启用当前价筛选", value=True)
    if use_price:
        price_min = st.number_input("当前价 ≥", -1_000_000, 1_000_000, -1_000_000)
        price_max = st.number_input("当前价 ≤", -1_000_000, 1_000_000, 1_000_000)

    # PE/PB
    use_pe_pb = st.checkbox("启用 PE/PB 筛选", value=True)
    if use_pe_pb:
        pe_min = st.number_input("PE ≥", -1_000_000, 1_000_000, -1_000_000)
        pe_max = st.number_input("PE ≤", -1_000_000, 1_000_000, 1_000_000)
        pb_min = st.number_input("PB ≥", -1_000_000, 1_000_000, -1_000_000)
        pb_max = st.number_input("PB ≤", -1_000_000, 1_000_000, 1_000_000)

    # 25年营业收入增长率
    use_growth25 = st.checkbox("启用25年营业收入增长筛选", value=True)
    if use_growth25:
        growth_min = st.number_input("25年营业总收入年增长率 ≥", -1_000_000, 1_000_000, -1_000_000)
        growth_max = st.number_input("25年营业总收入年增长率 ≤", -1_000_000, 1_000_000, 1_000_000)

    # 26Q1营业收入增长率
    use_growth26Q1 = st.checkbox("启用26Q1营业收入增长筛选", value=True)
    if use_growth26Q1:
        q1_growth_min = st.number_input("26年第一季度增长率 ≥", -1_000_000, 1_000_000, -1_000_000)
        q1_growth_max = st.number_input("26年第一季度增长率 ≤", -1_000_000, 1_000_000, 1_000_000)

    # 25年归母净利润增长率
    use_ni25 = st.checkbox("启用25年归母净利润增长筛选", value=True)
    if use_ni25:
        ni_25_min = st.number_input("25年归母净利润增长率 ≥", -1_000_000, 1_000_000, -1_000_000)
        ni_25_max = st.number_input("25年归母净利润增长率 ≤", -1_000_000, 1_000_000, 1_000_000)

    # 26Q1归母净利润增长率
    use_ni26q1 = st.checkbox("启用26Q1归母净利润增长筛选", value=True)
    if use_ni26q1:
        ni_26q1_min = st.number_input("26Q1归母净利润增长率 ≥", -1_000_000, 1_000_000, -1_000_000)
        ni_26q1_max = st.number_input("26Q1归母净利润增长率 ≤", -1_000_000, 1_000_000, 1_000_000)

    # 最高/最低相对昨收%
    use_high_pct = st.checkbox("启用最高相对昨收%筛选", value=True)
    if use_high_pct:
        high_pct_min = st.number_input("最高相对昨收% ≥", -1_000_000, 1_000_000, -1_000_000)
        high_pct_max = st.number_input("最高相对昨收% ≤", -1_000_000, 1_000_000, 1_000_000)

    use_low_pct = st.checkbox("启用最低相对昨收%筛选", value=True)
    if use_low_pct:
        low_pct_min = st.number_input("最低相对昨收% ≥", -1_000_000, 1_000_000, -1_000_000)
        low_pct_max = st.number_input("最低相对昨收% ≤", -1_000_000, 1_000_000, 1_000_000)

    # 行业
    use_industry = st.checkbox("启用行业筛选", value=True)
    if use_industry and 'industry' in df.columns:
        industries = df['industry'].dropna().unique().tolist()
        selected_industries = st.multiselect("行业筛选", options=industries, default=industries)

# ================= 数据筛选 ==================
filtered_df = df.copy()

# 定义一个辅助函数来处理百分比字符串的筛选
def filter_by_percentage(df, col, min_val, max_val):
    """处理百分比格式的筛选"""
    if col not in df.columns:
        return df
    # 将百分比字符串转换为数值
    temp_series = df[col].astype(str).str.rstrip('%').astype(float)
    return df[(temp_series >= min_val) & (temp_series <= max_val)]

if use_price:
    filtered_df = filtered_df[(filtered_df['当前价'] >= price_min) & (filtered_df['当前价'] <= price_max)]
if use_pe_pb:
    filtered_df = filtered_df[(filtered_df['pe_ttm'] >= pe_min) & (filtered_df['pe_ttm'] <= pe_max)]
    filtered_df = filtered_df[(filtered_df['pb'] >= pb_min) & (filtered_df['pb'] <= pb_max)]
if use_growth25:
    filtered_df = filter_by_percentage(filtered_df, '2025营业总收入年增长率', growth_min, growth_max)
if use_growth26Q1:
    filtered_df = filter_by_percentage(filtered_df, '2026年第一季度增长率', q1_growth_min, q1_growth_max)
if use_ni25:
    filtered_df = filter_by_percentage(filtered_df, '2025归母净利润增长率', ni_25_min, ni_25_max)
if use_ni26q1:
    filtered_df = filter_by_percentage(filtered_df, '2026Q1归母净利润增长率', ni_26q1_min, ni_26q1_max)
if use_high_pct:
    filtered_df = filtered_df[(filtered_df['最高相对昨收%'] >= high_pct_min) &
                              (filtered_df['最高相对昨收%'] <= high_pct_max)]
if use_low_pct:
    filtered_df = filtered_df[(filtered_df['最低相对昨收%'] >= low_pct_min) &
                              (filtered_df['最低相对昨收%'] <= low_pct_max)]
if use_industry:
    filtered_df = filtered_df[filtered_df['industry'].isin(selected_industries)]

# ================= 强制列顺序 ==================
columns_order = [
    'ts_code','name','industry','当前价',
    '最高价','最高价时间','最高相对昨收%',
    '最低价','最低价时间','最低相对昨收%',
    'pe_ttm','pb',
    '2025营业总收入','2025营业总收入年增长率',
    '2026Q1营业总收入','2026年第一季度增长率',
    '2025_归母净利润','2025归母净利润增长率',
    '2026Q1_归母净利润','2026Q1归母净利润增长率'
]
columns_order = [col for col in columns_order if col in filtered_df.columns]
filtered_df = filtered_df[columns_order]

# ================= 可视化 ==================
def highlight_rows(row):
    color = []
    for col in filtered_df.columns:
        if col in ['涨跌幅','最高相对昨收%','最低相对昨收%']:
            val = row[col]
            if pd.notna(val):
                # 处理字符串格式的百分比
                if isinstance(val, str) and '%' in val:
                    try:
                        num_val = float(val.replace('%', ''))
                        if num_val > 0: color.append('color: red')
                        elif num_val < 0: color.append('color: green')
                        else: color.append('')
                    except:
                        color.append('')
                # 处理数值格式
                elif isinstance(val, (int, float)):
                    if val > 0: color.append('color: red')
                    elif val < 0: color.append('color: green')
                    else: color.append('')
                else:
                    color.append('')
            else:
                color.append('')
        elif col in ['最高价','最低价']:
            color.append('font-weight: bold')
        else:
            color.append('')
    return color

def format_numbers(val):
    """格式化数值显示为2位小数，保持数值类型"""
    if isinstance(val, (int, float)) and pd.notna(val):
        return round(val, 2)
    return val

# 格式化 DataFrame 的数值列
display_df = filtered_df.copy()
for col in display_df.columns:
    # 跳过字符串类型的列（如增长率百分比）
    if display_df[col].dtype in ['object', 'str']:
        continue
    # 对数值列应用格式化
    if display_df[col].dtype in ['float64', 'int64']:
        display_df[col] = display_df[col].apply(format_numbers)

st.subheader(f"筛选结果: {len(filtered_df)} 条股票")
st.dataframe(display_df.style.apply(highlight_rows, axis=1).format(precision=2), use_container_width=True)

# ================= 导出 Excel ==================
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

excel_data = to_excel(filtered_df)
st.download_button(
    label="📥 导出 Excel",
    data=excel_data,
    file_name='选股结果.xlsx',
    mime='application/vnd.ms-excel'
)