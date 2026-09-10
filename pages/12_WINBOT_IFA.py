import streamlit as st
from dashboard_utils import render_dashboard

st.set_page_config(page_title="WINBOT IFA", layout="wide")

render_dashboard(
    page_name="WINBOT IFA",
    sheet_key='13Z_PM_l7pZSIIh19sjX_mIk21Aha1eU-wgYG4C_yY9I',
    plan_tab='Spots Plan',
    plan_type='standard',
    name_mappings={
        # MP 用活动名占位，raw 里是具体机型（整个 MP 只有这一个产品）
        'Product': {'WINBOT Activation': 'W2S PRO OMNI'},
        # MP 写渠道全称/全大写，raw 用缩写
        'Channel': {'OTTO': 'Otto', 'Boulanger': 'BLG'},
        'Landing Page': {'Product page': 'Product Page'},
    },
    # Landing Page 与 Benefit Channel(=raw 的 Channel) 两侧取值映射后已对齐，都进匹配维度
    # 注意：MP 里 Google DG 行的 Landing Page 是空的（DG 没有落地页概念），
    # 目前 DG 还没起量；等 DG 开始消耗后需要核对 raw 给它的 Landing Page 取值
    extra_join_keys=['Channel'],
)
