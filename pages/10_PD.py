import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="PD", layout="wide")

render_dashboard(
    page_name="PD",
    sheet_key='1y51NSDHseMOFszEwZbpu4M8JvKBaV2YxFU_Tt7M-Sjc',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {
            'X12 OmniCyclone Care Complete': 'X12 OmniCyclone',
            'T90 PRO OMNI Black Care Kit': 'T90 PRO OMNI',
            'P1': 'ULTRAMARINE P1',
        },
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
