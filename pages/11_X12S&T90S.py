import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="X12S&T90S", layout="wide")

render_dashboard(
    page_name="X12S&T90S",
    sheet_key='1c0KEIGnN003GV2DKUCBD4s9Rc3z0mElPWdmRgsGU2ss',
    plan_tab='Spots Plan',
    plan_type='standard',
    # raw data 早期把 T90S PRO OMNI 的 Meta campaign 命名成 T90S PRO，是同一个产品，
    # 统一成 MP 的叫法（MP 里写的是 T90S PRO OMNI）
    raw_name_mappings={
        'Product': {'T90S PRO': 'T90S PRO OMNI'},
    },
    name_mappings={
        'Platform': {'Google Search': 'Google SEM'},
        'Country': {'N_ES': 'ES'},
        'Product': {
            # MP 的 SEM 大盘词包 = raw 里的品牌名
            'DB Collection': 'DEEBOT',
            'WB Collection': 'WINBOT',
            # MP 带套装/配色后缀，raw 只有主产品名（都是一对一，不会合并出错：
            # Care Complete 只在 DE，纯 X12 OmniCyclone 只在 IT）
            'T90 PRO OMNI Black': 'T90 PRO OMNI',
            'X12 OmniCyclone Care Complete': 'X12 OmniCyclone',
        },
        # MP 里 IT 的 videoview 行写成 Video，DE/FR 写成 Videoview，raw 只有 Videoview
        'Objective': {'Video': 'Videoview'},
    },
    # Landing Page 两侧取值已对齐（Banner Page / Category Page / Listing / OZMO ROLLER Page），
    # Benefit Channel(=raw 的 Channel) 也对齐（AMZ / Official website），都进匹配维度
    extra_join_keys=['Channel'],
    exclude_platforms_plan=['PV', 'SEM'],
    # Google Search 只监测单品(Creative Sub=Product)，DB/WB Collection 的
    # Generic&Competitor / Brand&Product 不做监测
    monitor_creative_sub_filter={'Google SEM': ['Product']},
)
