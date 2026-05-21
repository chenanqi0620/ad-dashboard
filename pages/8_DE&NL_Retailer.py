import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="DE&NL Retailer", layout="wide")

render_dashboard(
    page_name="DE&NL Retailer",
    sheet_key='1gwiHqRQQycjXvpC-4qmiuAapTUKJa8FPSfhflDAdL5E',
    plan_tab='MP Q2',
    plan_type='de_nl',
    name_mappings={
        'Product': {
            'T90 PRO OMNI Black': 'T90 PRO OMNI',
            'A1600 LiDAR PRO': 'GOAT A1600 LiDAR PRO',
            'O1200 LiDAR PRO': 'GOAT O1200 LiDAR PRO',
            'A3000 LiDAR PRO': 'GOAT A3000 LiDAR PRO',
        },
        'Landing Page': {'Product page': 'Product Page'},
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
