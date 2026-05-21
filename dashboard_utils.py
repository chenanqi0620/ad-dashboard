import gspread
import pandas as pd
import streamlit as st
import plotly.express as px
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
import time


def _retry_on_quota(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(15 * (attempt + 1))
            else:
                raise


def get_monitor_dates():
    """Determine monitoring dates based on Beijing time weekday.
    Tue-Fri: monitor yesterday only; Monday: monitor Fri+Sat+Sun."""
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz)
    today = now_beijing.date()
    weekday = now_beijing.weekday()  # 0=Monday

    if weekday == 0:  # Monday -> check Fri, Sat, Sun
        monitor_dates = [today - timedelta(days=i) for i in range(1, 4)]
    else:  # Tue-Fri -> check yesterday
        monitor_dates = [today - timedelta(days=1)]

    monitor_dates = [pd.Timestamp(d) for d in monitor_dates]
    return monitor_dates


def get_gspread_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
    return gspread.authorize(creds)


@st.cache_data(ttl=600)
def load_raw_data(sheet_key, worksheet_name='raw data by ad'):
    gc = get_gspread_client()
    spreadsheet = _retry_on_quota(gc.open_by_key, sheet_key)
    ws = spreadsheet.worksheet(worksheet_name)
    data = _retry_on_quota(ws.get_all_values)
    headers = data[0]
    df = pd.DataFrame(data[1:], columns=headers)

    numeric_cols = ['Cost', 'Impr.', 'Views', 'Clicks']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].str.replace('[$,]', '', regex=True), errors='coerce').fillna(0)

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    return df


@st.cache_data(ttl=600)
def load_spots_plan(sheet_key, plan_tab='Spots Plan', plan_type='standard'):
    gc = get_gspread_client()
    spreadsheet = _retry_on_quota(gc.open_by_key, sheet_key)
    ws = spreadsheet.worksheet(plan_tab)
    data = _retry_on_quota(ws.get_all_values)

    if plan_type == 'standard':
        # Auto-detect: find the header row that contains 'Country' and 'Platform'
        header_row_idx = None
        for r_idx in range(min(5, len(data))):
            if 'Country' in data[r_idx] and 'Platform' in data[r_idx]:
                header_row_idx = r_idx
                break
        if header_row_idx is None:
            return pd.DataFrame()

        header = data[header_row_idx]
        # Auto-detect column positions by name
        col_map = {}
        for i, h in enumerate(header):
            h_clean = h.strip()
            if h_clean == 'Country':
                col_map['country'] = i
            elif h_clean == 'Product':
                col_map['product'] = i
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

        # Find first date column (format: M/D) in the same header row
        date_cols_start = None
        for i in range(len(header)):
            val = header[i].strip()
            if '/' in val:
                parts = val.split('/')
                try:
                    int(parts[0])
                    int(parts[1])
                    date_cols_start = i
                    break
                except ValueError:
                    continue

        if date_cols_start is None:
            return pd.DataFrame()

        date_header_row = header
        data_start = header_row_idx + 2  # skip header + day-of-week row
        country_idx = col_map.get('country', 0)
        product_idx = col_map.get('product', 2)
        lp_idx = col_map.get('landing_page')
        platform_idx = col_map.get('platform', 7)
        aip_idx = col_map.get('aip', 8)
        objective_idx = col_map.get('objective', 9)
        creative_idx = col_map.get('creative', 10)
        sub_idx = col_map.get('creative_sub', 11)
        has_landing_page = lp_idx is not None
    elif plan_type == 'b2b':
        # B2B: dates start after col 14 (Remark), row 2 is header, data from row 4
        # Find where dates start
        header = data[2]
        date_cols_start = None
        for i in range(14, len(header)):
            if '/' in header[i]:
                date_cols_start = i
                break
        if date_cols_start is None:
            # Try row below for dates
            if len(data) > 3:
                for i in range(14, len(data[3]) if len(data) > 3 else 0):
                    pass
            return pd.DataFrame()
        date_header_row = data[2]
        data_start = 4
        country_idx, product_idx, lp_idx, platform_idx, aip_idx, objective_idx, creative_idx, sub_idx = 0, 1, None, 4, 5, 6, 7, 8
        has_landing_page = False
    elif plan_type == 'de_nl':
        # DE&NL: auto-detect like standard
        header_row_idx = None
        for r_idx in range(min(5, len(data))):
            if 'Country' in data[r_idx] and 'Platform' in data[r_idx]:
                header_row_idx = r_idx
                break
        if header_row_idx is None:
            return pd.DataFrame()

        header = data[header_row_idx]
        col_map = {}
        for i, h in enumerate(header):
            h_clean = h.strip()
            if h_clean == 'Country':
                col_map['country'] = i
            elif h_clean == 'Product':
                col_map['product'] = i
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

        date_cols_start = None
        for i in range(len(header)):
            val = header[i].strip()
            if '/' in val:
                parts = val.split('/')
                try:
                    int(parts[0])
                    int(parts[1])
                    date_cols_start = i
                    break
                except ValueError:
                    continue

        if date_cols_start is None:
            return pd.DataFrame()

        date_header_row = header
        data_start = header_row_idx + 2
        country_idx = col_map.get('country', 0)
        product_idx = col_map.get('product', 2)
        lp_idx = col_map.get('landing_page')
        platform_idx = col_map.get('platform', 5)
        aip_idx = col_map.get('aip', 6)
        objective_idx = col_map.get('objective', 7)
        creative_idx = col_map.get('creative', 8)
        sub_idx = col_map.get('creative_sub', 9)
        has_landing_page = lp_idx is not None

    # Parse date columns
    date_map = {}
    for col_idx in range(date_cols_start, len(date_header_row)):
        raw = date_header_row[col_idx].strip()
        if '/' in raw:
            parts = raw.split('/')
            try:
                month = int(parts[0])
                day = int(parts[1])
                date_str = f"2026-{month:02d}-{day:02d}"
                date_map[col_idx] = date_str
            except ValueError:
                continue

    if not date_map:
        return pd.DataFrame()

    plan_records = []
    last_country = ''
    last_product = ''
    for row in data[data_start:]:
        country = row[country_idx].strip() if country_idx is not None and country_idx < len(row) else ''
        product = row[product_idx].strip() if product_idx is not None and product_idx < len(row) else ''

        # Forward-fill: inherit from previous row if empty
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
        platform = row[platform_idx].strip() if platform_idx is not None and platform_idx < len(row) else ''
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
                'AIP': row[aip_idx].strip() if aip_idx is not None and aip_idx < len(row) else '',
                'Objective': row[objective_idx].strip() if objective_idx is not None and objective_idx < len(row) else '',
                'Creative': row[creative_idx].strip() if creative_idx is not None and creative_idx < len(row) else '',
                'Creative Sub': row[sub_idx].strip() if sub_idx is not None and sub_idx < len(row) else '',
                'Date': date_str,
                'Plan_Cost': budget,
            }
            if has_landing_page and lp_idx is not None:
                record['Landing Page'] = row[lp_idx].strip() if lp_idx < len(row) else ''
            plan_records.append(record)

    plan_df = pd.DataFrame(plan_records)
    if len(plan_df) > 0:
        plan_df['Date'] = pd.to_datetime(plan_df['Date'], errors='coerce')
    return plan_df


def calculate_metrics(df):
    metrics = {}
    metrics['Cost'] = df['Cost'].sum()
    metrics['Impr'] = df['Impr.'].sum() if 'Impr.' in df.columns else 0
    metrics['Views'] = df['Views'].sum() if 'Views' in df.columns else 0
    metrics['Clicks'] = df['Clicks'].sum() if 'Clicks' in df.columns else 0
    metrics['CPM'] = (metrics['Cost'] / metrics['Impr'] * 1000) if metrics['Impr'] > 0 else 0
    metrics['CPC'] = (metrics['Cost'] / metrics['Clicks']) if metrics['Clicks'] > 0 else 0
    metrics['CTR'] = (metrics['Clicks'] / metrics['Impr']) if metrics['Impr'] > 0 else 0
    metrics['CPV'] = (metrics['Cost'] / metrics['Views']) if metrics['Views'] > 0 else 0
    metrics['VTR'] = (metrics['Views'] / metrics['Impr']) if metrics['Impr'] > 0 else 0
    return metrics


def calculate_daily_metrics(df):
    agg_dict = {'Cost': ('Cost', 'sum')}
    if 'Impr.' in df.columns:
        agg_dict['Impr'] = ('Impr.', 'sum')
    if 'Views' in df.columns:
        agg_dict['Views'] = ('Views', 'sum')
    if 'Clicks' in df.columns:
        agg_dict['Clicks'] = ('Clicks', 'sum')

    daily = df.groupby('Date').agg(**agg_dict).reset_index()
    if 'Impr' in daily.columns:
        daily['CPM'] = daily.apply(lambda r: r['Cost'] / r['Impr'] * 1000 if r['Impr'] > 0 else 0, axis=1)
        daily['CTR'] = daily.apply(lambda r: r['Clicks'] / r['Impr'] if r.get('Clicks', 0) > 0 and r['Impr'] > 0 else 0, axis=1)
    if 'Clicks' in daily.columns:
        daily['CPC'] = daily.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else 0, axis=1)
    if 'Views' in daily.columns:
        daily['CPV'] = daily.apply(lambda r: r['Cost'] / r['Views'] if r['Views'] > 0 else 0, axis=1)
        if 'Impr' in daily.columns:
            daily['VTR'] = daily.apply(lambda r: r['Views'] / r['Impr'] if r['Impr'] > 0 else 0, axis=1)
    return daily


def generate_insights(df, metrics, daily):
    insights = []
    if len(daily) >= 2:
        latest = daily.iloc[-1]
        prev = daily.iloc[-2]
        if prev['Cost'] > 0:
            cost_change = (latest['Cost'] - prev['Cost']) / prev['Cost'] * 100
            if abs(cost_change) > 20:
                direction = "上升" if cost_change > 0 else "下降"
                insights.append(f"⚠️ 最近一天花费较前一天{direction} {abs(cost_change):.1f}%")
        if 'CPC' in daily.columns and prev.get('CPC', 0) > 0:
            cpc_change = (latest['CPC'] - prev['CPC']) / prev['CPC'] * 100
            if abs(cpc_change) > 15:
                direction = "上升" if cpc_change > 0 else "下降"
                insights.append(f"⚠️ CPC 较前一天{direction} {abs(cpc_change):.1f}%")

    if len(daily) >= 7:
        last_7 = daily.tail(7)
        prev_7 = daily.iloc[-14:-7] if len(daily) >= 14 else daily.head(7)
        wow_cost = ((last_7['Cost'].sum() - prev_7['Cost'].sum()) / prev_7['Cost'].sum() * 100) if prev_7['Cost'].sum() > 0 else 0
        insights.append(f"📊 近7天 vs 前7天花费变化: {wow_cost:+.1f}%")

    by_platform = df.groupby('Platform').agg(Cost=('Cost', 'sum'), Clicks=('Clicks', 'sum'), Impr=('Impr.', 'sum')).reset_index()
    by_platform['CTR'] = by_platform.apply(lambda r: r['Clicks'] / r['Impr'] if r['Impr'] > 0 else 0, axis=1)
    if len(by_platform) > 0:
        best = by_platform.loc[by_platform['CTR'].idxmax()]
        worst = by_platform.loc[by_platform['CTR'].idxmin()]
        insights.append(f"🏆 CTR 最高平台: {best['Platform']} ({best['CTR']:.2%})")
        if len(by_platform) > 1:
            insights.append(f"📉 CTR 最低平台: {worst['Platform']} ({worst['CTR']:.2%})")

    by_country = df.groupby('Country').agg(Cost=('Cost', 'sum'), Clicks=('Clicks', 'sum')).reset_index()
    by_country['CPC'] = by_country.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else 0, axis=1)
    by_country = by_country[by_country['CPC'] > 0]
    if len(by_country) > 0:
        cheapest = by_country.loc[by_country['CPC'].idxmin()]
        most_expensive = by_country.loc[by_country['CPC'].idxmax()]
        insights.append(f"💰 CPC 最低国家: {cheapest['Country']} (${cheapest['CPC']:.3f})")
        if len(by_country) > 1:
            insights.append(f"💸 CPC 最高国家: {most_expensive['Country']} (${most_expensive['CPC']:.3f})")

    return insights


def render_dashboard(page_name, sheet_key, plan_tab=None, plan_type='standard',
                     name_mappings=None, exclude_platforms_plan=None):
    """
    Main dashboard rendering function.
    name_mappings: dict with keys like 'Product', 'Creative Sub', 'Country' mapping plan values to raw data values
    exclude_platforms_plan: list of platform names to exclude from plan comparison
    """
    st.title(f"📊 {page_name} Dashboard")
    st.caption("数据来源: Google Sheet (实时连接，每次刷新自动更新)")
    st.markdown("""<style>[data-testid="stMetricValue"] { font-size: 1.2rem; }</style>""", unsafe_allow_html=True)

    df = load_raw_data(sheet_key)

    # --- Sidebar Filters ---
    st.sidebar.header("筛选条件")
    date_range = st.sidebar.date_input(
        "日期范围",
        value=(df['Date'].min().date(), df['Date'].max().date()),
        min_value=df['Date'].min().date(),
        max_value=df['Date'].max().date()
    )

    filter_cols = ['Country', 'Platform', 'Objective', 'Creative', 'Creative Sub', 'Ad Group']
    filters = {}
    for col in filter_cols:
        if col in df.columns:
            unique_vals = sorted(df[col].unique())
            filters[col] = st.sidebar.multiselect(col, options=unique_vals, default=unique_vals)

    # --- Apply Filters ---
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
    dims = ['Country', 'Product', 'Platform', 'Objective', 'Creative', 'Creative Sub']
    dims = [d for d in dims if d in filtered_df.columns]

    # --- Plan vs Actual ---
    if plan_tab:
        st.header("🎯 Plan vs 实际消耗监测")
        st.caption("逻辑：监测日实际消耗 vs Plan 计划值，偏差 ±30% 预警（周一监测上周五六日，其余监测前一天）")

        plan_df = load_spots_plan(sheet_key, plan_tab=plan_tab, plan_type=plan_type)

        if len(plan_df) > 0:
            # Exclude platforms
            if exclude_platforms_plan:
                for p in exclude_platforms_plan:
                    plan_df = plan_df[plan_df['Platform'] != p]

            # Apply name mappings
            if name_mappings:
                for col, mapping in name_mappings.items():
                    if col in plan_df.columns:
                        plan_df[col] = plan_df[col].replace(mapping)

            # Determine join keys based on available columns
            base_keys = ['Country', 'Product', 'Platform', 'AIP', 'Objective', 'Creative', 'Creative Sub']
            if 'Landing Page' in plan_df.columns and 'Landing Page' in filtered_df.columns:
                base_keys.insert(2, 'Landing Page')
            join_keys = [k for k in base_keys if k in plan_df.columns and k in filtered_df.columns]

            # Normalize raw data mappings
            compare_df = filtered_df.copy()
            if name_mappings:
                for col, mapping in name_mappings.items():
                    if col in compare_df.columns:
                        compare_df[col] = compare_df[col].replace(mapping)

            monitor_date_strs = [d.strftime('%Y-%m-%d') for d in sorted(monitor_dates) if d in compare_df['Date'].values]
            if monitor_date_strs:
                st.subheader(f"监测日期: {', '.join(monitor_date_strs)}")

                actual_day = compare_df[compare_df['Date'].isin(monitor_dates)].groupby(join_keys).agg(
                    Actual_Cost=('Cost', 'sum')
                ).reset_index()

                plan_day = plan_df[plan_df['Date'].isin(monitor_dates)].groupby(join_keys).agg(
                    Plan_Cost=('Plan_Cost', 'sum')
                ).reset_index()

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
                col_b.metric("有计划无消耗", f"{len(no_spend)} 条", help="Plan 有预算但实际消耗为 0")
                col_c.metric("无计划有消耗", f"{len(no_plan)} 条", help="Plan 无预算但实际有消耗")

                if len(no_spend) > 0:
                    st.error("⚠️ 有计划预算但无实际消耗（漏投）")
                    display_no_spend = no_spend[join_keys + ['Plan_Cost']].copy()
                    display_no_spend['_learning'] = no_spend.apply(is_learning, axis=1)
                    display_no_spend['Plan_Cost'] = display_no_spend.apply(
                        lambda r: f"${r['Plan_Cost']:,.2f} ⭐️" if r['_learning'] else f"${r['Plan_Cost']:,.2f}", axis=1)
                    display_no_spend = display_no_spend.drop(columns=['_learning'])
                    display_no_spend.columns = [*join_keys, 'Plan 预算']
                    st.dataframe(display_no_spend, use_container_width=True, hide_index=True)
                    has_learning_no_spend = no_spend.apply(is_learning, axis=1).any()
                    if has_learning_no_spend:
                        st.caption("⭐️ = Google DG Conversion 广告最近3天内新增，处于系统学习期（3~4天），消耗少属正常现象")

                if len(no_plan) > 0:
                    st.error("⚠️ 无计划预算但有实际消耗（超范围投放）")
                    display_no_plan = no_plan[join_keys + ['Actual_Cost']].copy()
                    display_no_plan['Actual_Cost'] = display_no_plan['Actual_Cost'].apply(lambda x: f"${x:,.2f}")
                    display_no_plan.columns = [*join_keys, '实际消耗']
                    st.dataframe(display_no_plan, use_container_width=True, hide_index=True)

                if len(deviation_alerts) > 0:
                    st.warning("⚠️ 消耗偏差 ±30% 以上")
                    display_dev = deviation_alerts[join_keys + ['Plan_Cost', 'Actual_Cost', 'Deviation']].copy()
                    display_dev['_learning'] = deviation_alerts.apply(is_learning, axis=1)
                    display_dev['Plan_Cost'] = display_dev['Plan_Cost'].apply(lambda x: f"${x:,.2f}")
                    display_dev['Actual_Cost'] = display_dev['Actual_Cost'].apply(lambda x: f"${x:,.2f}")
                    display_dev['Deviation'] = display_dev.apply(
                        lambda r: f"{float(r['Deviation']):+.1f}% ⭐️" if r['_learning'] else f"{float(r['Deviation']):+.1f}%", axis=1)
                    display_dev = display_dev.drop(columns=['_learning'])
                    display_dev.columns = [*join_keys, 'Plan 预算', '实际消耗', '偏差']
                    st.dataframe(display_dev, use_container_width=True, hide_index=True)
                    has_learning_dev = deviation_alerts.apply(is_learning, axis=1).any()
                    if has_learning_dev:
                        st.caption("⭐️ = Google DG Conversion 广告最近3天内新增，处于系统学习期（3~4天），消耗少属正常现象")

                if len(deviation_alerts) == 0 and len(no_spend) == 0 and len(no_plan) == 0:
                    st.success("✅ 所有投放与 Plan 一致，无异常")
            else:
                st.info("监测日期无数据")
        else:
            st.info("Plan 数据为空或无法解析")

    # --- CPC Monitoring ---
    st.header("🚨 CPC 上涨预警")
    st.caption("逻辑：监测日 CPC vs 前3日均值 CPC，上涨 20%+ 触发预警（周一监测上周五六日，其余监测前一天）")

    if len(monitor_data) > 0 and len(prev_dates) > 0:
        monitor_date_strs = [d.strftime('%Y-%m-%d') for d in sorted(monitor_dates) if d in filtered_df['Date'].values]
        st.caption(f"监测日期: {', '.join(monitor_date_strs)}")

        cpc_df = filtered_df[filtered_df['Objective'].isin(['Traffic', 'Conversion'])]

        latest_group = cpc_df[cpc_df['Date'].isin(monitor_dates)].groupby(dims).agg(
            Cost=('Cost', 'sum'), Clicks=('Clicks', 'sum')
        ).reset_index()
        latest_group['CPC_latest'] = latest_group.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else None, axis=1)

        prev_group = cpc_df[cpc_df['Date'].isin(prev_dates)].groupby(dims).agg(
            Cost=('Cost', 'sum'), Clicks=('Clicks', 'sum')
        ).reset_index()
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
            total_rows = len(merged)
            alert_count = len(alerts_df)
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
    st.header("🚨 VTR 下降预警")
    st.caption("逻辑：监测日 VTR vs 前3日均值 VTR，下降 25%+ 触发预警（周一监测上周五六日，其余监测前一天）")

    if len(monitor_data) > 0 and len(prev_dates) > 0:
        vtr_objectives = ['VVC Instream', 'VVC Instream TV', 'VVC Shorts', 'Videoview']
        vtr_df = filtered_df[filtered_df['Objective'].isin(vtr_objectives)]

        latest_vtr = vtr_df[vtr_df['Date'].isin(monitor_dates)].groupby(dims).agg(
            Views=('Views', 'sum'), Impr=('Impr.', 'sum')
        ).reset_index()
        latest_vtr['VTR_latest'] = latest_vtr.apply(lambda r: r['Views'] / r['Impr'] if r['Impr'] > 0 else None, axis=1)

        prev_vtr = vtr_df[vtr_df['Date'].isin(prev_dates)].groupby(dims).agg(
            Views=('Views', 'sum'), Impr=('Impr.', 'sum')
        ).reset_index()
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

    # --- Metrics Overview ---
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
        breakdown_dims = [c for c in ['Platform', 'Country', 'Objective', 'Creative', 'Creative Sub'] if c in filtered_df.columns]
        breakdown_dim = st.selectbox("按维度拆分", breakdown_dims)
        breakdown_metric = st.selectbox("对比指标", ['Cost', 'Impr', 'Clicks', 'CPM', 'CPC', 'CTR'], key='breakdown_metric')

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
    st.header("国家 × 平台 × 目标 数据表")
    pivot = filtered_df.groupby(['Country', 'Platform', 'Objective']).agg(
        Cost=('Cost', 'sum'), Impr=('Impr.', 'sum'), Views=('Views', 'sum'), Clicks=('Clicks', 'sum')
    ).reset_index()
    pivot['CPM'] = pivot.apply(lambda r: r['Cost'] / r['Impr'] * 1000 if r['Impr'] > 0 else 0, axis=1)
    pivot['CPC'] = pivot.apply(lambda r: r['Cost'] / r['Clicks'] if r['Clicks'] > 0 else 0, axis=1)
    pivot['CTR'] = pivot.apply(lambda r: r['Clicks'] / r['Impr'] if r['Impr'] > 0 else 0, axis=1)
    pivot['CPV'] = pivot.apply(lambda r: r['Cost'] / r['Views'] if r['Views'] > 0 else 0, axis=1)
    pivot['VTR'] = pivot.apply(lambda r: r['Views'] / r['Impr'] if r['Impr'] > 0 else 0, axis=1)
    pivot = pivot.sort_values(['Country', 'Platform', 'Objective'], ascending=True)
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
