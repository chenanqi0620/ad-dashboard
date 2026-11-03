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
        'Platform': {'Google Search': 'Google SEM', 'OpenAI': 'OPEN AI'},
        'Country': {'N_ES': 'ES'},
        'Product': {
            # MP 的 SEM 大盘词包 = raw 里的品牌名
            'DB Collection': 'DEEBOT',
            'WB Collection': 'WINBOT',
            # MP 带套装/配色后缀，raw 只有主产品名（都是一对一，不会合并出错：
            # Care Complete 只在 DE，纯 X12 OmniCyclone 只在 IT）
            'T90 PRO OMNI Black': 'T90 PRO OMNI',
            'X12 OmniCyclone Care Complete': 'X12 OmniCyclone',
            # MP 的 X12S 套装后缀，raw 只有 X12S OmniCyclone，是同一个东西
            'X12S OmniCyclone Care Kit': 'X12S OmniCyclone',
        },
        # MP 里 IT 的 videoview 行写成 Video，DE/FR 写成 Videoview，raw 只有 Videoview
        'Objective': {'Video': 'Videoview'},
    },
    # Landing Page 两侧取值已对齐（Banner Page / Category Page / Listing / OZMO ROLLER Page），
    # Benefit Channel(=raw 的 Channel) 也对齐（AMZ / Official website），都进匹配维度
    extra_join_keys=['Channel'],
    exclude_platforms_plan=['PV', 'SEM'],
    # Google Search 监测单品(Product)和单品竞品词(Product Competitor)——两侧叫法一致，直接对得上。
    # 大盘词包仍不监测：Generic / Competitor(raw 把 plan 的 Generic&Competitor 拆成两行，对不上)、
    # Brand&Product(用户未要求)。要加这几个得先用 raw_name_mappings 合并 Generic+Competitor。
    monitor_creative_sub_filter={'Google SEM': ['Product', 'Product Competitor']},
)
