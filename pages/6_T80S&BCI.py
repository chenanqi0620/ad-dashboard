import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="T80S&BCI", layout="wide")

render_dashboard(
    page_name="T80S&BCI",
    sheet_key='1uTVEaV89JXaKTKd2rM4RAIpAaul5pkUkueLXja-x2eo',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {'T90 PRO OMNI Black': 'T90 PRO OMNI'},
        'Country': {'N_ES': 'ES'},
        'Creative Sub': {
            'BCI Film H': 'BCI Film-H',
            'BCI Film H&V': 'BCI Film-H&V',
            'BCI Film V': 'BCI Film-V',
        },
    },
    exclude_platforms_plan=['PV', 'SEM']
)
