import tushare as ts
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import os

# ================= 配置 =================
MY_TOKEN = 'hVHIqepGSSaLalvergpnPImzSZzQeQkZMMowilWmnsdkAHHXnSPHLootFBkaPUeT'
pro = ts.pro_api(MY_TOKEN, timeout=120)
pro._DataApi__http_url = "http://118.89.66.41:8010/"

TODAY_STR = datetime.now().strftime('%Y%m%d')
OUTPUT_FILE = '股票综合数据_含极值财务估值.xlsx'
ALL_DAILY_FILE = 'all_history_daily.csv'

# ================= 拉取日线数据 =================
start_date = '20260101'
end_date = TODAY_STR

if os.path.exists(ALL_DAILY_FILE):
    old_raw_df = pd.read_csv(ALL_DAILY_FILE, parse_dates=['trade_date'])
    last_date = old_raw_df['trade_date'].max()
    start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime('%Y%m%d')
else:
    old_raw_df = pd.DataFrame()

if start_date <= end_date:
    trade_cal = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open='1')
    all_data = []
    for date in trade_cal['cal_date']:
        try:
            df = pro.daily(trade_date=date)
            if df is not None and not df.empty:
                all_data.append(df)
            time.sleep(0.3)
        except Exception as e:
            print(f"❌ 拉取 {date} 日线失败：{e}")
            time.sleep(5)
    if all_data:
        new_df = pd.concat(all_data, ignore_index=True)
        new_df['trade_date'] = pd.to_datetime(new_df['trade_date'])
        full_df = pd.concat([old_raw_df, new_df]).drop_duplicates(subset=['ts_code','trade_date'])
    else:
        full_df = old_raw_df
else:
    full_df = old_raw_df

full_df.to_csv(ALL_DAILY_FILE, index=False)

# ================= 计算最高/最低价及涨跌幅 =================
if not full_df.empty:
    full_df = full_df.sort_values(['ts_code','trade_date'])
    full_df['pre_close'] = full_df['close'].shift(1)

    def calc_extremes(group):
        group = group.copy()
        current_price = group['close'].iloc[-1]
        max_row = group.loc[group['high'].idxmax()]
        min_row = group.loc[group['low'].idxmin()]
        return pd.Series({
            '当前价': current_price,
            '最高价': max_row['high'],
            '最高价时间': max_row['trade_date'].date(),
            '最低价': min_row['low'],
            '最低价时间': min_row['trade_date'].date(),
            '最高相对昨收%': ((max_row['high'] - current_price)/current_price*100),
            '最低相对昨收%': ((min_row['low'] - current_price)/current_price*100)
        })

    price_result = full_df.groupby('ts_code').apply(calc_extremes).reset_index()
else:
    price_result = pd.DataFrame()

# ================= 股票基础信息 =================
df_stocks_basic = pro.stock_basic(list_status='L', fields='ts_code,name,industry')
df_result = pd.DataFrame(index=df_stocks_basic['ts_code'])
all_codes = df_stocks_basic['ts_code'].tolist()

# ================= 拉取营业收入 =================
def fetch_financial(codes, period, type_='4'):
    ts_codes_str = ','.join(codes)
    try:
        df = pro.income_vip(ts_code=ts_codes_str, period=period, type=type_,
                            fields='ts_code,revenue,yoy_revenue')
        if df is None or df.empty:
            return pd.DataFrame()
        year = period[:4]
        prefix = f"{year}Q1" if type_=='1' else year
        df.rename(columns={'revenue': f'{prefix}营业总收入', 'yoy_revenue': f'{prefix}营业总收入同比增长率(接口)'}, inplace=True)
        df.drop_duplicates(subset=['ts_code'], keep='first', inplace=True)
        df.set_index('ts_code', inplace=True)
        return df
    except Exception as e:
        print(f"❌ 财务数据请求失败: {e}")
        return pd.DataFrame()

tasks = [
    {'period':'20241231','type':'4'},
    {'period':'20250331','type':'1'},
    {'period':'20251231','type':'4'},
    {'period':'20260331','type':'1'}
]
for task in tasks:
    df_batch = fetch_financial(all_codes, task['period'], task['type'])
    if not df_batch.empty:
        df_result = df_result.join(df_batch, how='left')

# ================= 拉取归母净利润 =================
def fetch_net_income(codes, period, type_='4'):
    ts_codes_str = ','.join(codes)
    try:
        df = pro.income_vip(ts_code=ts_codes_str, period=period, type=type_, fields='ts_code,n_income_attr_p')
        if df is None or df.empty:
            return pd.DataFrame()
        prefix = f"{period[:4]}Q1" if type_=='1' else period[:4]
        df.rename(columns={'n_income_attr_p': f'{prefix}_归母净利润'}, inplace=True)
        df.drop_duplicates(subset=['ts_code'], keep='first', inplace=True)
        df.set_index('ts_code', inplace=True)
        return df
    except Exception as e:
        print(f"❌ 净利润数据请求失败: {e}")
        return pd.DataFrame()

for task in tasks:
    df_income = fetch_net_income(all_codes, task['period'], task['type'])
    if not df_income.empty:
        df_result = df_result.join(df_income, how='left')

# ================= 计算归母净利润增长率 =================
df_result['2025归母净利润增长率'] = np.where(
    df_result.get('2024_归母净利润',0) != 0,
    (df_result['2025_归母净利润'] - df_result['2024_归母净利润'])/df_result['2024_归母净利润'].abs() * 100,
    np.nan
)
df_result['2025归母净利润增长率'] = df_result['2025归母净利润增长率'].round(2)

df_result['2026Q1归母净利润增长率'] = np.where(
    df_result.get('2025Q1_归母净利润',0) != 0,
    (df_result['2026Q1_归母净利润'] - df_result['2025Q1_归母净利润'])/df_result['2025Q1_归母净利润'].abs() * 100,
    np.nan
)
df_result['2026Q1归母净利润增长率'] = df_result['2026Q1归母净利润增长率'].round(2)

# ================= 计算营业总收入增长率 =================
df_result['2025营业总收入年增长率'] = np.where(
    df_result.get('2024营业总收入',0) != 0,
    (df_result['2025营业总收入'] - df_result['2024营业总收入'])/df_result['2024营业总收入'].abs() * 100,
    np.nan
)
df_result['2025营业总收入年增长率'] = df_result['2025营业总收入年增长率'].round(2)

df_result['2026年第一季度增长率'] = np.where(
    df_result.get('2025Q1营业总收入',0) != 0,
    (df_result['2026Q1营业总收入'] - df_result['2025Q1营业总收入'])/df_result['2025Q1营业总收入'].abs() * 100,
    np.nan
)
df_result['2026年第一季度增长率'] = df_result['2026年第一季度增长率'].round(2)

# 金额单位万元，取整
for col in ['2024营业总收入','2025营业总收入','2025Q1营业总收入','2026Q1营业总收入',
            '2024_归母净利润','2025_归母净利润','2025Q1_归母净利润','2026Q1_归母净利润']:
    if col in df_result.columns:
        df_result[col] = pd.to_numeric(df_result[col], errors='coerce')/10000
        df_result[col] = df_result[col].round(0)

# ================= 前一个交易日估值 =================
try:
    df_cal = pro.trade_cal(exchange='SSE', is_open=1, end_date=TODAY_STR, limit=2)
    target_date = df_cal.iloc[1]['cal_date']
    df_basic = pro.daily_basic(trade_date=target_date, fields='ts_code,pe,pe_ttm,pb,total_mv,circ_mv')
except:
    df_basic = pd.DataFrame()
    target_date = None

# ================= 合并最终结果 =================
final_df = price_result.merge(df_result, on='ts_code', how='left')
if not df_basic.empty:
    final_df = final_df.merge(df_basic, on='ts_code', how='left')

final_df = final_df.merge(df_stocks_basic, on='ts_code', how='left')

# 保存 Excel
final_df.to_excel(OUTPUT_FILE, index=False)
print(f"🎉 综合数据已保存至: {OUTPUT_FILE}")
if target_date:
    print(f"📅 估值数据日期: {target_date}")