import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="DE Borussia", layout="wide")

render_dashboard(
    page_name="DE Borussia",
    sheet_key='1wgm1P-N4ZHp94m_sncl_XqRf3SQDc-zKQoJzmM-bCe4',
    plan_tab='Spots Plan',
    plan_type='standard',
    # Meta 的这条广告命名漏了 "1/2/3 ... (Reel)" 后缀且带前导空格，TT 用的是全名，
    # 统一成 MP 的叫法（同时让筛选器/CPC/VTR 也不再拆成两条）
    raw_name_mappings={
        'Creative Sub': {' Interview with Timo': 'Interview 1/2/3 with Timo (Reel)'},
    },
    name_mappings={
        'Channel': {'otto': 'Otto'},
        # MP 用 Awareness/Engagement，raw 落到投放层的 Reach/Videoview
        'Objective': {'Awareness': 'Reach', 'Engagement': 'Videoview'},
        # MP 带时长/人名后缀，raw 只有主名（都是一对一）
        'Creative Sub': {
            'Highlight Video 90s': 'Highlight Video',
            'Player Posts carrousel Timo & FZD': 'Player Posts carrousel',
        },
    },
    # Landing Page(Brand Store) 与 Benefit Channel(=raw 的 Channel) 两侧已对齐，都进匹配维度
    extra_join_keys=['Channel'],
)
