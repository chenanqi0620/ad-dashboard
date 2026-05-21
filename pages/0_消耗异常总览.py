import streamlit as st
import pandas as pd
from dashboard_utils import (
    load_raw_data, load_spots_plan, get_gspread_client, get_monitor_dates
)
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import time

st.set_page_config(page_title="消耗异常总览", layout="wide")
st.title("🚨 消耗异常总览 (全部子表)")
st.caption("汇总所有子表的 Plan vs 实际消耗监测，方便一目了然查看异常")

monitor_dates = get_monitor_dates()
monitor_date_strs_display = [d.strftime('%Y-%m-%d') for d in sorted(monitor_dates)]
st.subheader(f"监测日期: {', '.join(monitor_date_strs_display)}")

# All page configurations
PAGE_CONFIGS = [
    {
        'name': 'X12&T50',
        'sheet_key': '1j0WLQj71oakiidJ1kqgNofo5UwoLhRG0GIC4tOb0L8o',
        'plan_tab': 'Spots Plan',
        'plan_type': 'standard',
        'name_mappings': {
            'Product': {'T50 PRO Gen3 Black': 'T50 PRO Gen3', 'T90 PRO OMNI Black': 'T90 PRO OMNI'},
            'Creative Sub': {'KV&ZAHA': 'KV'},
            'Country': {'N_ES': 'ES'},
        },
    },
    {
        'name': 'ULTRAMARINE P1',
        'sheet_key': '1BfxGEMiO0W05OEVLEe_UAdAcJ9IJk1wJ7qfMULTiQKU',
        'plan_tab': 'Spots Plan',
        'plan_type': 'standard',
        'name_mappings': {
            'Product': {'P1': 'ULTRAMARINE P1', 'T90 PRO OMNI Black': 'T90 PRO OMNI'},
            'Country': {'N_ES': 'ES'},
        },
    },
    {
        'name': 'T90',
        'sheet_key': '1uwmuTkF10Wqpo03mNm9pMbVwyfnzt4g5JI6YDb1StdA',
        'plan_tab': 'Spots Plan',
        'plan_type': 'standard',
        'name_mappings': {
            'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI'},
            'Country': {'N_ES': 'ES'},
        },
    },
    {
        'name': 'W3',
        'sheet_key': '1yv3V9DmT7bxXDa3_auHfCjUEME-tgsGGZ2Ih3jDVqM4',
        'plan_tab': 'Spots Plan',
        'plan_type': 'standard',
        'name_mappings': {
            'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI'},
            'Country': {'N_ES': 'ES'},
        },
    },
    {
        'name': 'GOAT',
        'sheet_key': '1lYKiVjJueijIhjVnzjkh8lntVx0AwttdQDHSO8UCkOw',
        'plan_tab': 'Spots Plan',
        'plan_type': 'standard',
        'name_mappings': {
            'Product': {
                'A1600 LiDAR PRO Care Kit': 'GOAT A1600 LiDAR PRO',
                'A1600 LiDAR PRO': 'GOAT A1600 LiDAR PRO',
                'O1200 LiDAR PRO Care Kit': 'GOAT O1200 LiDAR PRO',
                'O1200 LiDAR PRO': 'GOAT O1200 LiDAR PRO',
                'A3000 LiDAR PRO': 'GOAT A3000 LiDAR PRO',
                'O600 RTK Care Kit': 'O600 RTK',
                'O600 RTK': 'O600 RTK',
                'T90 PRO OMNI Black': 'T90 PRO OMNI',
            },
            'Country': {'N_ES': 'ES'},
        },
    },
    {
        'name': 'T80S&BCI',
        'sheet_key': '1uTVEaV89JXaKTKd2rM4RAIpAaul5pkUkueLXja-x2eo',
        'plan_tab': 'Spots Plan',
        'plan_type': 'standard',
        'name_mappings': {
            'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI'},
            'Country': {'N_ES': 'ES'},
            'Creative Sub': {
                'BCI Film H': 'BCI Film-H',
                'BCI Film H&V': 'BCI Film-H&V',
                'BCI Film V': 'BCI Film-V',
            },
        },
    },
    {
        'name': 'B2B Reseller',
        'sheet_key': '1KkfxGlI59C6oHQ8V-DG0iEMhH8UpunnS_zIs8H71RSE',
        'plan_tab': 'Spots Plan',
        'plan_type': 'standard',
        'name_mappings': {
            'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI', 'T50 PRO GEN 3': 'T50 PRO Gen3'},
            'Platform': {'YTB': 'Google YTB'},
            'Country': {'N_ES': 'ES'},
        },
    },
    {
        'name': 'DE&NL Retailer',
        'sheet_key': '1gwiHqRQQycjXvpC-4qmiuAapTUKJa8FPSfhflDAdL5E',
        'plan_tab': 'MP Q2',
        'plan_type': 'de_nl',
        'name_mappings': {
            'Product': {
                'T90 PRO OMNI Black': 'T90 PRO OMNI',
                'A1600 LiDAR PRO': 'GOAT A1600 LiDAR PRO',
                'O1200 LiDAR PRO': 'GOAT O1200 LiDAR PRO',
                'A3000 LiDAR PRO': 'GOAT A3000 LiDAR PRO',
            },
            'Landing Page': {'Product page': 'Product Page'},
            'Country': {'N_ES': 'ES'},
        },
    },
]

EXCLUDE_PLATFORMS = ['PV', 'SEM']


@st.cache_data(ttl=600)
def load_emea_mp_plans():
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key('1Tpo3CHtniaKz050T_5mD3ewAGONVjfrDvqeSPt01gZI')

    mp_tabs = [ws.title for ws in spreadsheet.worksheets() if ws.title.startswith('MP-')]
    all_records = []
    for tab_name in mp_tabs:
        ws = spreadsheet.worksheet(tab_name)
        data = ws.get_all_values()
        header_row_idx = None
        for r_idx in range(min(5, len(data))):
            row_text = [cell.strip() for cell in data[r_idx]]
            if 'Platform' in row_text or 'Campaign Type' in row_text:
                header_row_idx = r_idx
                break
        if header_row_idx is None:
            continue
        header = data[header_row_idx]
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
        country_idx = col_map.get('country', 0)
        product_idx = col_map.get('product', 2)
        bc_idx = col_map.get('benefit_channel')
        lp_idx = col_map.get('landing_page')
        platform_idx = col_map.get('platform', 6)
        aip_idx = col_map.get('aip', 7)
        objective_idx = col_map.get('objective', 8)
        creative_idx = col_map.get('creative', 9)
        sub_idx = col_map.get('creative_sub', 10)
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


def run_plan_comparison(page_name, raw_df, plan_df, join_keys, monitor_dates):
    """Run Plan vs Actual comparison and return results."""
    monitor_data_actual = raw_df[raw_df['Date'].isin(monitor_dates)]
    monitor_data_plan = plan_df[plan_df['Date'].isin(monitor_dates)]

    if len(monitor_data_actual) == 0 and len(monitor_data_plan) == 0:
        return None

    actual_day = monitor_data_actual.groupby(join_keys).agg(Actual_Cost=('Cost', 'sum')).reset_index()
    plan_day = monitor_data_plan.groupby(join_keys).agg(Plan_Cost=('Plan_Cost', 'sum')).reset_index()

    comparison = actual_day.merge(plan_day, on=join_keys, how='outer')
    comparison['Actual_Cost'] = comparison['Actual_Cost'].fillna(0)
    comparison['Plan_Cost'] = comparison['Plan_Cost'].fillna(0)

    no_spend = comparison[(comparison['Plan_Cost'] > 0) & (comparison['Actual_Cost'] == 0)]
    no_plan = comparison[(comparison['Plan_Cost'] == 0) & (comparison['Actual_Cost'] > 0)]
    both_exist = comparison[(comparison['Plan_Cost'] > 0) & (comparison['Actual_Cost'] > 0)].copy()
    both_exist['Deviation'] = (both_exist['Actual_Cost'] - both_exist['Plan_Cost']) / both_exist['Plan_Cost'] * 100
    deviation_alerts = both_exist[both_exist['Deviation'].abs() >= 30].sort_values('Deviation', key=abs, ascending=False)

    # Google DG Conversion learning period detection
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

    return {
        'no_spend': no_spend,
        'no_plan': no_plan,
        'deviation_alerts': deviation_alerts,
        'join_keys': join_keys,
        'is_learning': is_learning,
    }


# --- Process all pages ---
total_no_spend = 0
total_no_plan = 0
total_deviation = 0
all_results = []

def load_with_retry(func, *args, max_retries=3, **kwargs):
    """Retry API calls with exponential backoff on 429 errors."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if '429' in str(e) and attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))
            else:
                raise


with st.spinner("正在加载所有子表数据（约30秒）..."):
    # Pages 1-8
    for i, config in enumerate(PAGE_CONFIGS):
        try:
            if i > 0:
                time.sleep(5)
            raw_df = load_with_retry(load_raw_data, config['sheet_key'])
            time.sleep(3)
            plan_df = load_with_retry(load_spots_plan, config['sheet_key'], plan_tab=config['plan_tab'], plan_type=config['plan_type'])

            if len(plan_df) == 0:
                continue

            for p in EXCLUDE_PLATFORMS:
                plan_df = plan_df[plan_df['Platform'] != p]

            mappings = config.get('name_mappings', {})
            if mappings:
                for col, mapping in mappings.items():
                    if col in plan_df.columns:
                        plan_df[col] = plan_df[col].replace(mapping)
                    if col in raw_df.columns:
                        raw_df[col] = raw_df[col].replace(mapping)

            base_keys = ['Country', 'Product', 'Platform', 'AIP', 'Objective', 'Creative', 'Creative Sub']
            if 'Landing Page' in plan_df.columns and 'Landing Page' in raw_df.columns:
                base_keys.insert(2, 'Landing Page')
            join_keys = [k for k in base_keys if k in plan_df.columns and k in raw_df.columns]

            result = run_plan_comparison(config['name'], raw_df, plan_df, join_keys, monitor_dates)
            if result:
                all_results.append((config['name'], result))
                total_no_spend += len(result['no_spend'])
                total_no_plan += len(result['no_plan'])
                total_deviation += len(result['deviation_alerts'])
        except Exception as e:
            st.warning(f"⚠️ {config['name']} 加载失败: {str(e)[:100]}")

    # Page 9: EMEA FR&IT
    try:
        time.sleep(5)
        emea_raw = load_with_retry(load_raw_data, '1Tpo3CHtniaKz050T_5mD3ewAGONVjfrDvqeSPt01gZI')
        time.sleep(3)
        emea_plan = load_with_retry(load_emea_mp_plans)
        if len(emea_plan) > 0:
            emea_plan = emea_plan[~emea_plan['Platform'].isin(EXCLUDE_PLATFORMS)]
            emea_plan['Country'] = emea_plan['Country'].replace({'N_ES': 'ES'})
            emea_plan['Product'] = emea_plan['Product'].replace({
                'T90 PRO OMNI Black': 'T90 PRO OMNI',
                'X12 PRO OMNI Black': 'X12 PRO',
                'T50 OMNI Gen3 Black': 'T50 OMNI Gen3',
            })
            emea_plan['Creative Sub'] = emea_plan['Creative Sub'].replace({
                'KV&ZAHA': 'KV',
                'Pieter - T90 Carousel Post': 'Pieter',
                'T90 designers ambassadors - Pieter': 'Pieter',
            })
            emea_raw_copy = emea_raw.copy()
            emea_raw_copy['Creative Sub'] = emea_raw_copy['Creative Sub'].replace({'KV&ZAHA': 'KV'})

            join_keys_emea = ['Country', 'Product', 'Channel', 'Landing Page', 'Platform', 'AIP', 'Objective', 'Creative', 'Creative Sub']
            join_keys_emea = [k for k in join_keys_emea if k in emea_plan.columns and k in emea_raw_copy.columns]

            result = run_plan_comparison('EMEA FR&IT', emea_raw_copy, emea_plan, join_keys_emea, monitor_dates)
            if result:
                all_results.append(('EMEA FR&IT', result))
                total_no_spend += len(result['no_spend'])
                total_no_plan += len(result['no_plan'])
                total_deviation += len(result['deviation_alerts'])
    except Exception as e:
        st.warning(f"⚠️ EMEA FR&IT 加载失败: {str(e)[:100]}")

# --- Summary metrics ---
st.divider()
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("异常子表", f"{len([r for r in all_results if len(r[1]['no_spend']) + len(r[1]['no_plan']) + len(r[1]['deviation_alerts']) > 0])} / {len(all_results)}")
col_b.metric("偏差 ±30%", f"{total_deviation} 条")
col_c.metric("有计划无消耗", f"{total_no_spend} 条")
col_d.metric("无计划有消耗", f"{total_no_plan} 条")

# --- Per-page details ---
for page_name, result in all_results:
    no_spend = result['no_spend']
    no_plan = result['no_plan']
    deviation_alerts = result['deviation_alerts']
    join_keys = result['join_keys']
    is_learning = result['is_learning']

    alert_count = len(no_spend) + len(no_plan) + len(deviation_alerts)
    if alert_count == 0:
        continue

    st.divider()
    st.subheader(f"📋 {page_name}")
    c1, c2, c3 = st.columns(3)
    c1.metric("偏差 ±30%", f"{len(deviation_alerts)} 条")
    c2.metric("有计划无消耗", f"{len(no_spend)} 条")
    c3.metric("无计划有消耗", f"{len(no_plan)} 条")

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

# All clean
if all(len(r[1]['no_spend']) + len(r[1]['no_plan']) + len(r[1]['deviation_alerts']) == 0 for r in all_results):
    st.success("✅ 所有子表投放与 Plan 一致，无异常")

st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 点击右上角 Rerun 刷新数据")
