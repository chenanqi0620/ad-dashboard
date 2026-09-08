import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="X12S&T90S", layout="wide")

render_dashboard(
    page_name="X12S&T90S",
    sheet_key='1c0KEIGnN003GV2DKUCBD4s9Rc3z0mElPWdmRgsGU2ss',
    plan_tab='Spots Plan',
    plan_type='standard',
    # raw data 自己就有两套叫法：9/7 起新建的 Meta campaign 命名成 T90S PRO，
    # 之前的命名成 T90S PRO OMNI，是同一个产品，先统一成 MP 的叫法
    raw_name_mappings={
        'Product': {'T90S PRO OMNI': 'T90S PRO'},
    },
    name_mappings={
        'Platform': {'Google Search': 'Google SEM'},
        'Country': {'N_ES': 'ES'},
        # MP 的 SEM 大盘词包 = raw 里的品牌名
        'Product': {'DB Collection': 'DEEBOT', 'WB Collection': 'WINBOT'},
        # MP 里 IT 的 videoview 行写成 Video，DE/FR 写成 Videoview，raw 只有 Videoview
        'Objective': {'Video': 'Videoview'},
    },
    # MP 的 Landing Page 分类和 campaign 命名里带出来的对不上（MP 的 Listing 在 raw 里
    # 既是 Listing 又是 Banner Page，OZMO ROLLER Page 在 raw 里是 Banner Page），
    # 且 raw 侧它不区分任何一行，参与匹配只会造成成对误报
    exclude_join_keys=['Landing Page'],
    exclude_platforms_plan=['PV', 'SEM'],
    # Google Search 只监测单品(Creative Sub=Product)，DB/WB Collection 的
    # Generic&Competitor / Brand&Product 不做监测
    monitor_creative_sub_filter={'Google SEM': ['Product']},
)
