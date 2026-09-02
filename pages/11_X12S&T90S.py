import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="X12S&T90S", layout="wide")

render_dashboard(
    page_name="X12S&T90S",
    sheet_key='1c0KEIGnN003GV2DKUCBD4s9Rc3z0mElPWdmRgsGU2ss',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Platform': {'Google Search': 'Google SEM'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM'],
    # Google Search 只监测单品(Creative Sub=Product)，DB/WB Collection 的
    # Generic&Competitor / Brand&Product 不做监测
    monitor_creative_sub_filter={'Google SEM': ['Product']},
)
