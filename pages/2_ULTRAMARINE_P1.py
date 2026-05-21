import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="ULTRAMARINE P1", layout="wide")

render_dashboard(
    page_name="ULTRAMARINE P1",
    sheet_key='1BfxGEMiO0W05OEVLEe_UAdAcJ9IJk1wJ7qfMULTiQKU',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {'P1': 'ULTRAMARINE P1', 'T90 PRO OMNI Black': 'T90 PRO OMNI'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
