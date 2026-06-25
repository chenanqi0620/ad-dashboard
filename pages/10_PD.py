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
            'T90 PRO OMNI Black': 'T90 PRO OMNI',
            'T90 PRO OMNI Black Care Kit': 'T90 PRO OMNI',
            'A1600 LiDAR PRO': 'GOAT A1600 LiDAR PRO',
            'A1600 LiDAR PRO Care Kit': 'GOAT A1600 LiDAR PRO',
            'P1': 'ULTRAMARINE P1',
        },
        'Platform': {'Google Search': 'Google SEM'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV'],
    monitor_creative_sub_filter={'Google SEM': ['Product']},
)
