import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="T90", layout="wide")

render_dashboard(
    page_name="T90",
    sheet_key='1uwmuTkF10Wqpo03mNm9pMbVwyfnzt4g5JI6YDb1StdA',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
