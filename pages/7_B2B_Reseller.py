import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="B2B Reseller", layout="wide")

render_dashboard(
    page_name="B2B Reseller",
    sheet_key='1KkfxGlI59C6oHQ8V-DG0iEMhH8UpunnS_zIs8H71RSE',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI', 'T50 PRO GEN 3': 'T50 PRO Gen3'},
        'Platform': {'YTB': 'Google YTB'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
