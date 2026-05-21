import streamlit as st
from dashboard_utils import render_dashboard, load_raw_data, load_spots_plan

st.set_page_config(page_title="X12&T50", layout="wide")

render_dashboard(
    page_name="X12&T50",
    sheet_key='1j0WLQj71oakiidJ1kqgNofo5UwoLhRG0GIC4tOb0L8o',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {'T50 PRO Gen3 Black': 'T50 PRO Gen3', 'T90 PRO OMNI Black': 'T90 PRO OMNI'},
        'Creative Sub': {'KV&ZAHA': 'KV'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
