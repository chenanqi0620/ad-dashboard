import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="GOAT", layout="wide")

render_dashboard(
    page_name="GOAT",
    sheet_key='1lYKiVjJueijIhjVnzjkh8lntVx0AwttdQDHSO8UCkOw',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        'Product': {
            'A1600 LiDAR PRO Care Kit': 'GOAT A1600 LiDAR PRO',
            'A1600 LiDAR PRO': 'GOAT A1600 LiDAR PRO',
            'O1200 LiDAR PRO Care Kit': 'GOAT O1200 LiDAR PRO',
            'O1200 LiDAR PRO': 'GOAT O1200 LiDAR PRO',
            'A3000 LiDAR PRO': 'GOAT A3000 LiDAR PRO',
            'O600 RTK Care Kit': 'O600 RTK',
            'O600 RTK': 'O600 RTK',
            'T90 PRO OMNI Black': 'T90 PRO OMNI',
        },
        'Country': {'N_ES': 'ES'},
    },
    exclude_platforms_plan=['PV', 'SEM']
)
