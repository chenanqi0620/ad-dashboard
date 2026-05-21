import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

from dashboard_utils import (
    render_dashboard, load_raw_data, get_gspread_client,
    calculate_metrics, calculate_daily_metrics, generate_insights,
    get_monitor_dates
)
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="EMEA FR&IT", layout="wide")

SHEET_KEY = '1Tpo3CHtniaKz050T_5mD3ewAGONVjfrDvqeSPt01gZI'


@st.cache_data(ttl=600)
def load_all_mp_plans():
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SHEET_KEY)

    mp_tabs = [ws.title for ws in spreadsheet.worksheets() if ws.title.startswith('MP-')]

    all_records = []
    for tab_name in mp_tabs:
        ws = spreadsheet.worksheet(tab_name)
        data = ws.get_all_values()

        # Find header row (has 'Platform' or 'Campaign Type')
        header_row_idx = None
        for r_idx in range(min(5, len(data))):
            row_text = [cell.strip() for cell in data[r_idx]]
            if 'Platform' in row_text or 'Campaign Type' in row_text:
                header_row_idx = r_idx
                break

        if header_row_idx is None:
            continue

        header = data[header_row_idx]

        # Detect column positions
        col_map = {}
        for i, h in enumerate(header):
            h_clean = h.strip()
            if h_clean == 'Country':
                col_map['country'] = i
            elif h_clean == 'Product':
                col_map['product'] = i
            elif h_clean == 'Benefit Channel':
                col_map['benefit_channel'] = i
            elif h_clean == 'Landing Page':
                col_map['landing_page'] = i
            elif h_clean == 'Platform':
                col_map['platform'] = i
            elif h_clean == 'AIP':
                col_map['aip'] = i
            elif h_clean in ('Campaign Type', 'Objective'):
                col_map['objective'] = i
            elif h_clean == 'Creative':
                col_map['creative'] = i
            elif h_clean == 'Creative Sub':
                col_map['creative_sub'] = i

        # Country might be at col 0 even without label
        country_idx = col_map.get('country', 0)
        product_idx = col_map.get('product', 2)
        bc_idx = col_map.get('benefit_channel')
        lp_idx = col_map.get('landing_page')
        platform_idx = col_map.get('platform', 6)
        aip_idx = col_map.get('aip', 7)
        objective_idx = col_map.get('objective', 8)
        creative_idx = col_map.get('creative', 9)
        sub_idx = col_map.get('creative_sub', 10)

        # Find date columns
        date_map = {}
        for i in range(len(header)):
            val = header[i].strip()
            if '/' in val:
                parts = val.split('/')
                try:
                    month = int(parts[0])
                    day = int(parts[1])
                    date_map[i] = f"2026-{month:02d}-{day:02d}"
                except ValueError:
                    continue

        if not date_map:
            continue

        data_start = header_row_idx + 2
        last_country = ''
        last_product = ''

        for row in data[data_start:]:
            country = row[country_idx].strip() if country_idx < len(row) else ''
            product = row[product_idx].strip() if product_idx < len(row) else ''

            if country:
                last_country = country
            else:
                country = last_country
            if product:
                last_product = product
            else:
                product = last_product

            if not country or len(country) > 5:
                continue
            platform = row[platform_idx].strip() if platform_idx < len(row) else ''
            if not platform:
                continue

            for col_idx, date_str in date_map.items():
                if col_idx >= len(row):
                    continue
                val = row[col_idx].strip().replace(',', '')
                try:
                    budget = float(val) if val else 0
                except ValueError:
                    budget = 0

                record = {
                    'Country': country,
                    'Product': product,
                    'Platform': platform,
                    'AIP': row[aip_idx].strip() if aip_idx < len(row) else '',
                    'Objective': row[objective_idx].strip() if objective_idx < len(row) else '',
                    'Creative': row[creative_idx].strip() if creative_idx < len(row) else '',
                    'Creative Sub': row[sub_idx].strip() if sub_idx < len(row) else '',
                    'Date': date_str,
                    'Plan_Cost': budget,
                }
                if bc_idx is not None:
                    record['Channel'] = row[bc_idx].strip() if bc_idx < len(row) else ''
                if lp_idx is not None:
                    record['Landing Page'] = row[lp_idx].strip() if lp_idx < len(row) else ''
                all_records.append(record)

    plan_df = pd.DataFrame(all_records)
    if len(plan_df) > 0:
        plan_df['Date'] = pd.to_datetime(plan_df['Date'], errors='coerce')
    return plan_df


# --- Main Dashboard ---
st.title("📊 EMEA FR&IT Dashboard")
st.caption("数据来源: Google Sheet (实时连接，每次刷新自动更新)")

df = load_raw_data(SHEET_KEY)

# --- Sidebar Filters ---
st.sidebar.header("筛选条件")
date_range = st.sidebar.date_input(
    "日期范围",
    value=(df['Date'].min().date(), df['Date'].max().date()),
    min_value=df['Date'].min().date(),
    max_value=df['Date'].max().date()
)

filter_cols = ['Country', 'Channel', 'Landing Page', 'Platform', 'Objective', 'Creative', 'Creative Sub', 'Ad Group']
filters = {}
for col in filter_cols:
    if col in df.columns:
        unique_vals = sorted(df[col].unique())
        filters[col] = st.sidebar.multiselect(col, options=unique_vals, default=unique_vals)

mask = (df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])
for col, vals in filters.items():
    mask = mask & (df[col].isin(vals))
filtered_df = df[mask]

# --- Monitoring date setup ---
dates_sorted = sorted(filtered_df['Date'].unique())
monitor_dates = get_monitor_dates()
monitor_data = filtered_df[filtered_df['Date'].isin(monitor_dates)]
earliest_monitor = min(monitor_dates)
prev_candidates = [d for d in dates_sorted if d < earliest_monitor]
prev_dates = prev_candidates[-3:] if len(prev_candidates) >= 3 else prev_candidates
dims = ['Country', 'Product', 'Channel', 'Landing Page', 'Platform', 'Objective', 'Creative', 'Creative Sub']
dims = [d for d in dims if d in filtered_df.columns]

# --- Plan vs Actual (multi-MP) ---
st.header("🎯 Plan vs 实际消耗监测 (合并所有 MP- 表)")
st.caption("逻辑：监测日实际消耗 vs Plan 计划值，偏差 ±30% 预警（周一监测上周五六日，其余监测前一天）")

plan_df = load_all_mp_plans()

if len(plan_df) > 0:
    # Exclude PV and SEM
    plan_df = plan_df[~plan_df['Platform'].isin(['PV', 'SEM'])]

    # Name mappings
    plan_df['Country'] = plan_df['Country'].replace({'N_ES': 'ES'})
    plan_df['Product'] = plan_df['Product'].replace({
        'T90 PRO OMNI Black': 'T90 PRO OMNI',
        'X12 PRO OMNI Black': 'X12 PRO',
        'T50 OMNI Gen3 Black': 'T50 OMNI Gen3',
    })
    plan_df['Creative Sub'] = plan_df['Creative Sub'].replace({
        'KV&ZAHA': 'KV',
        'Pieter - T90 Carousel Post': 'Pieter',
        'T90 designers ambassadors - Pieter': 'Pieter',
    })

    # Determine join keys
    join_keys = ['Country', 'Product', 'Channel', 'Landing Page', 'Platform', 'AIP', 'Objective', 'Creative', 'Creative Sub']
    join_keys = [k for k in join_keys if k in plan_df.columns and k in filtered_df.columns]

    compare_df = filtered_df.copy()
    compare_df['Creative Sub'] = compare_df['Creative Sub'].replace({'KV&ZAHA': 'KV'})

    monitor_date_strs = [d.strftime('%Y-%m-%d') for d in sorted(monitor_dates) if d in compare_df['Date'].values]
    if monitor_date_strs:
        st.subheader(f"监测日期: {', '.join(monitor_date_strs)}")

        actual_day = compare_df[compare_df['Date'].isin(monitor_dates)].groupby(join_keys).agg(Actual_Cost=('Cost', 'sum')).reset_index()
        plan_day = plan_df[plan_df['Date'].isin(monitor_dates)].groupby(join_keys).agg(Plan_Cost=('Plan_Cost', 'sum')).reset_index()

        comparison = actual_day.merge(plan_day, on=join_keys, how='outer')
        comparison['Actual_Cost'] = comparison['Actual_Cost'].fillna(0)
        comparison['Plan_Cost'] = comparison['Plan_Cost'].fillna(0)

        no_spend = comparison[(comparison['Plan_Cost'] > 0) & (comparison['Actual_Cost'] == 0)]
        no_plan = comparison[(comparison['Plan_Cost'] == 0) & (comparison['Actual_Cost'] > 0)]
        both_exist = comparison[(comparison['Plan_Cost'] > 0) & (comparison['Actual_Cost'] > 0)].copy()
        both_exist['Deviation'] = (both_exist['Actual_Cost'] - both_exist['Plan_Cost']) / both_exist['Plan_Cost'] * 100
        deviation_alerts = both_exist[both_exist['Deviation'].abs() >= 30].sort_values('Deviation', key=abs, ascending=False)

        # Detect Google DG + Conversion learning period (newly added within 3 days)
        latest_monitor = max(monitor_dates)
        learning_cutoff = latest_monitor - pd.Timedelta(days=3)
        gdg_conv_plan = plan_df[(plan_df['Platform'] == 'Google DG') & (plan_df['Objective'] == 'Conversion') & (plan_df['Plan_Cost'] > 0)]
        learning_entries = set()
        if len(gdg_conv_plan) > 0:
            first_dates = gdg_conv_plan.groupby([k for k in join_keys if k in gdg_conv_plan.columns])['Date'].min().reset_index()
            first_dates = first_dates[first_dates['Date'] >= learning_cutoff]
            for _, row in first_dates.iterrows():
                key = tuple(row[k] for k in join_keys if k in first_dates.columns)
                learning_entries.add(key)

        def is_learning(row):
            if 'Platform' in row and 'Objective' in row:
                if row['Platform'] == 'Google DG' and row['Objective'] == 'Conversion':
                    key = tuple(row[k] for k in join_keys if k in row.index)
                    return key in learning_entries
            return False

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("偏差 ±30% 预警", f"{len(deviation_alerts)} 条")
        col_b.metric("有计划无消耗", f"{len(no_spend)} 条")
        col_c.metric("无计划有消耗", f"{len(no_plan)} 条")

        if len(no_spend) > 0:
            st.error("⚠️ 有计划预算但无实际消耗（漏投）")
            d = no_spend[join_keys + ['Plan_Cost']].copy()
            d['_learning'] = no_spend.apply(is_learning, axis=1)
            d['Plan_Cost'] = d.apply(
                lambda r: f"${r['Plan_Cost']:,.2f} ⭐️" if r['_learning'] else f"${r['Plan_Cost']:,.2f}", axis=1)
            d = d.drop(columns=['_learning'])
            d.columns = [*join_keys, 'Plan 预算']
            st.dataframe(d, use_container_width=True, hide_index=True)
            if no_spend.apply(is_learning, axis=1).any():
                st.caption("⭐️ = Google DG Conversion 广告最近3天内新增，处于系统学习期（3~4天），消耗少属正常现象")

        if len(no_plan) > 0:
            st.error("⚠️ 无计划预算但有实际消耗（超范围投放）")
            d = no_plan[join_keys + ['Actual_Cost']].copy()
            d['Actual_Cost'] = d['Actual_Cost'].apply(lambda x: f"${x:,.2f}")
            d.columns = [*join_keys, '实际消耗']
            st.dataframe(d, use_container_width=True, hide_index=True)

        if len(deviation_alerts) > 0:
            st.warning("⚠️ 消耗偏差 ±30% 以上")
            d = deviation_alerts[join_keys + ['Plan_Cost', 'Actual_Cost', 'Deviation']].copy()
            d['_learning'] = deviation_alerts.apply(is_learning, axis=1)
            d['Plan_Cost'] = d['Plan_Cost'].apply(lambda x: f"${x:,.2f}")
            d['Actual_Cost'] = d['Actual_Cost'].apply(lambda x: f"${x:,.2f}")
            d['Deviation'] = d.apply(
                lambda r: f"{float(r['Deviation']):+.1f}% ⭐️" if r['_learning'] else f"{float(r['Deviation']):+.1f}%", axis=1)
            d = d.drop(columns=['_learning'])
            d.columns = [*join_keys, 'Plan 预算', '实际消耗', '偏差']
            st.dataframe(d, use_container_width=True, hide_index=True)
            if deviation_alerts.apply(is_learning, axis=1).any():
                st.caption("⭐️ = Google DG Conversion 广告最近3天内新增，处于系统学习期（3~4天），消耗少属正常现象")

        if len(deviation_alerts) == 0 and len(no_spend) == 0 and len(no_plan) == 0:
            st.success("✅ 所有投放与 Plan 一致，无异常")
    else:
        st.info("监测日期无数据")
else:
    st.info("无法加载 MP 计划数据")

# --- CPC Monitoring ---
st.header("🚨 CPC 变动预警 (Country → Product → Channel → Landing Page → Platform → Objective → Creative → Creative Sub)")
st.caption("逻辑：监测日 CPC vs 前3日均值 CPC，上涨 20%+ 触发预警（周一监测上周五六日，其余监测前一天）")

if len(monitor_data) > 0 and len(prev_dates) > 0:
    monitor_date_strs = [d.strftime('%Y-%m-%d') for d in sorted(monitor_dates) if d in filtered_df['Date'].values]
    st.caption(f"监测日期: {', '.join(monitor_date_strs)}")

    cpc_df = filtered_df[filtered_df['Objective'].isin(['Traffic', 'Conversion'])]

    latest_group = cpc_df[cpc_df['Date'].isin(monitor_dates)].groupby(dims).agg(Cost=('Cost', 'sum'), Clicks=('Clicks', 'sum')).reset_index()
    latest_group['CPC_latest'] = latest_group.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else None, axis=1)

    prev_group = cpc_df[cpc_df['Date'].isin(prev_dates)].groupby(dims).agg(Cost=('Cost', 'sum'), Clicks=('Clicks', 'sum')).reset_index()
    prev_group['CPC_prev'] = prev_group.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else None, axis=1)

    merged = latest_group[dims + ['CPC_latest']].merge(prev_group[dims + ['CPC_prev']], on=dims, how='inner')
    merged = merged.dropna(subset=['CPC_latest', 'CPC_prev'])
    merged = merged[merged['CPC_prev'] > 0]
    merged['CPC_change'] = (merged['CPC_latest'] - merged['CPC_prev']) / merged['CPC_prev'] * 100
    alerts_df = merged[merged['CPC_change'] >= 20].sort_values('CPC_change', ascending=False)

    if len(alerts_df) > 0:
        st.warning(f"共 {len(alerts_df)} 条 CPC 上涨 20%+ 预警")
        display_alerts = alerts_df.copy()
        display_alerts['CPC_prev'] = display_alerts['CPC_prev'].apply(lambda x: f"${x:.3f}")
        display_alerts['CPC_latest'] = display_alerts['CPC_latest'].apply(lambda x: f"${x:.3f}")
        display_alerts['CPC_change'] = display_alerts['CPC_change'].apply(lambda x: f"+{x:.1f}%")
        display_alerts.columns = [*dims, 'CPC (监测日)', 'CPC (前3日均值)', '涨幅']
        st.dataframe(display_alerts, use_container_width=True, hide_index=True)

        # Pattern summary by dimension
        summaries = []
        for dim_name in ['Country', 'Platform', 'Product']:
            if dim_name not in alerts_df.columns:
                continue
            dim_total = merged.groupby(dim_name).size()
            dim_alert = alerts_df.groupby(dim_name).size()
            dim_ratio = (dim_alert / dim_total).dropna().sort_values(ascending=False)
            high_ratio = dim_ratio[dim_ratio >= 0.7]
            if len(high_ratio) > 0:
                items = [f"{name}({int(dim_alert[name])}/{int(dim_total[name])})" for name in high_ratio.index]
                summaries.append(f"**{dim_name}**: {', '.join(items)} 普遍上涨")
            else:
                top = dim_alert.sort_values(ascending=False)
                if len(top) > 0:
                    items = [f"{name}({int(top[name])}条)" for name in top.index[:3]]
                    summaries.append(f"**{dim_name}**: 非普遍性，集中在 {', '.join(items)}")
        if summaries:
            st.caption('📊 规律总结（预警占该维度总条目≥70%判定为"普遍上涨"）：')
            for s in summaries:
                st.caption(s)
    else:
        st.success("✅ 无 CPC 上涨 20%+ 的预警")
else:
    st.info("数据不足，无法进行 CPC 监测")

# --- VTR Monitoring ---
st.header("🚨 VTR 变动预警 (Country → Product → Channel → Landing Page → Platform → Objective → Creative → Creative Sub)")
st.caption("逻辑：监测日 VTR vs 前3日均值 VTR，下降 25%+ 触发预警（周一监测上周五六日，其余监测前一天）")

if len(monitor_data) > 0 and len(prev_dates) > 0:
    vtr_objectives = ['VVC Instream', 'VVC Instream TV', 'VVC Shorts', 'Videoview']
    vtr_df = filtered_df[filtered_df['Objective'].isin(vtr_objectives)]

    latest_vtr = vtr_df[vtr_df['Date'].isin(monitor_dates)].groupby(dims).agg(Views=('Views', 'sum'), Impr=('Impr.', 'sum')).reset_index()
    latest_vtr['VTR_latest'] = latest_vtr.apply(lambda r: r['Views'] / r['Impr'] if r['Impr'] > 0 else None, axis=1)

    prev_vtr = vtr_df[vtr_df['Date'].isin(prev_dates)].groupby(dims).agg(Views=('Views', 'sum'), Impr=('Impr.', 'sum')).reset_index()
    prev_vtr['VTR_prev'] = prev_vtr.apply(lambda r: r['Views'] / r['Impr'] if r['Impr'] > 0 else None, axis=1)

    merged_vtr = latest_vtr[dims + ['VTR_latest']].merge(prev_vtr[dims + ['VTR_prev']], on=dims, how='inner')
    merged_vtr = merged_vtr.dropna(subset=['VTR_latest', 'VTR_prev'])
    merged_vtr = merged_vtr[merged_vtr['VTR_prev'] > 0]
    merged_vtr['VTR_change'] = (merged_vtr['VTR_latest'] - merged_vtr['VTR_prev']) / merged_vtr['VTR_prev'] * 100
    vtr_alerts = merged_vtr[merged_vtr['VTR_change'] <= -25].sort_values('VTR_change', ascending=True)

    if len(vtr_alerts) > 0:
        st.warning(f"共 {len(vtr_alerts)} 条 VTR 下降 25%+ 预警")
        display_vtr = vtr_alerts.copy()
        display_vtr['VTR_prev'] = display_vtr['VTR_prev'].apply(lambda x: f"{x:.2%}")
        display_vtr['VTR_latest'] = display_vtr['VTR_latest'].apply(lambda x: f"{x:.2%}")
        display_vtr['VTR_change'] = display_vtr['VTR_change'].apply(lambda x: f"{x:.1f}%")
        display_vtr.columns = [*dims, 'VTR (监测日)', 'VTR (前3日均值)', '跌幅']
        st.dataframe(display_vtr, use_container_width=True, hide_index=True)
    else:
        st.success("✅ 无 VTR 下降 25%+ 的预警")
else:
    st.info("数据不足，无法进行 VTR 监测")

# --- Metrics ---
st.header("核心指标总览")
metrics = calculate_metrics(filtered_df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Cost ($)", f"${metrics['Cost']:,.2f}")
col2.metric("Impressions", f"{metrics['Impr']:,.0f}")
col3.metric("Views", f"{metrics['Views']:,.0f}")
col4.metric("Clicks", f"{metrics['Clicks']:,.0f}")

col5, col6, col7, col8, col9 = st.columns(5)
col5.metric("CPM", f"${metrics['CPM']:.2f}")
col6.metric("CPC", f"${metrics['CPC']:.3f}")
col7.metric("CTR", f"{metrics['CTR']:.2%}")
col8.metric("CPV", f"${metrics['CPV']:.4f}")
col9.metric("VTR", f"{metrics['VTR']:.2%}")

# --- Daily Trend ---
st.header("每日趋势")
daily = calculate_daily_metrics(filtered_df)

if len(daily) > 0:
    available_metrics = [c for c in ['Cost', 'Impr', 'Views', 'Clicks', 'CPM', 'CPC', 'CTR', 'CPV', 'VTR'] if c in daily.columns]
    metric_choice = st.selectbox("选择指标", available_metrics)
    fig = px.line(daily, x='Date', y=metric_choice, title=f"{metric_choice} 每日趋势")
    fig.update_layout(hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("维度对比")
    breakdown_dim = st.selectbox("按维度拆分", ['Platform', 'Country', 'Channel', 'Landing Page', 'Objective', 'Creative', 'Creative Sub'])
    breakdown_metric = st.selectbox("对比指标", ['Cost', 'Impr', 'Clicks', 'CPM', 'CPC', 'CTR'], key='bm')

    breakdown = filtered_df.groupby([filtered_df['Date'].dt.date, breakdown_dim]).agg(
        Cost=('Cost', 'sum'), Impr=('Impr.', 'sum'), Views=('Views', 'sum'), Clicks=('Clicks', 'sum')
    ).reset_index()
    breakdown['CPM'] = breakdown.apply(lambda r: r['Cost'] / r['Impr'] * 1000 if r['Impr'] > 0 else 0, axis=1)
    breakdown['CPC'] = breakdown.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else 0, axis=1)
    breakdown['CTR'] = breakdown.apply(lambda r: r['Clicks'] / r['Impr'] if r['Impr'] > 0 else 0, axis=1)
    fig2 = px.line(breakdown, x='Date', y=breakdown_metric, color=breakdown_dim, title=f"{breakdown_metric} by {breakdown_dim}")
    fig2.update_layout(hovermode='x unified')
    st.plotly_chart(fig2, use_container_width=True)

# --- Data Table ---
st.header("国家 × Channel × Landing Page × 平台 × 目标 数据表")
table_dims = ['Country', 'Channel', 'Landing Page', 'Platform', 'Objective']
table_dims = [d for d in table_dims if d in filtered_df.columns]
pivot = filtered_df.groupby(table_dims).agg(
    Cost=('Cost', 'sum'), Impr=('Impr.', 'sum'), Views=('Views', 'sum'), Clicks=('Clicks', 'sum')
).reset_index()
pivot['CPM'] = pivot.apply(lambda r: r['Cost'] / r['Impr'] * 1000 if r['Impr'] > 0 else 0, axis=1)
pivot['CPC'] = pivot.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else 0, axis=1)
pivot['CTR'] = pivot.apply(lambda r: r['Clicks'] / r['Impr'] if r['Impr'] > 0 else 0, axis=1)
pivot['CPV'] = pivot.apply(lambda r: r['Cost'] / r['Views'] if r['Views'] > 0 else 0, axis=1)
pivot['VTR'] = pivot.apply(lambda r: r['Views'] / r['Impr'] if r['Impr'] > 0 else 0, axis=1)
pivot = pivot.sort_values(table_dims, ascending=True)
st.dataframe(
    pivot.style.format({
        'Cost': '${:,.2f}', 'Impr': '{:,.0f}', 'Views': '{:,.0f}', 'Clicks': '{:,.0f}',
        'CPM': '${:.2f}', 'CPC': '${:.3f}', 'CTR': '{:.2%}', 'CPV': '${:.4f}', 'VTR': '{:.2%}'
    }),
    use_container_width=True, hide_index=True
)

# --- Insights ---
st.header("🔍 自动 Insight 总结")
insights = generate_insights(filtered_df, metrics, daily)
for insight in insights:
    st.markdown(f"- {insight}")

st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 点击右上角 Rerun 刷新数据")
