import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="W3", layout="wide")

render_dashboard(
    page_name="W3",
    sheet_key='1yv3V9DmT7bxXDa3_auHfCjUEME-tgsGGZ2Ih3jDVqM4',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
