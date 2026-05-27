import streamlit as st

st.set_page_config(page_title="Ad Performance Dashboard", layout="wide")

st.title("📊 Ad Performance Dashboard")
st.markdown("---")
st.markdown("""
### 看板列表

使用左侧导航栏切换不同 MP 看板：

| # | 看板名称 | 说明 |
|---|---------|------|
| 1 | X12&T50 | DEEBOT X12 & T50 Launch Campaign |
| 2 | ULTRAMARINE P1 | ULTRAMARINE Phase 1 |
| 3 | T90 | T90 Campaign |
| 4 | W3 | W3 Campaign |
| 5 | GOAT | GOAT Campaign |
| 6 | T80S&BCI | T80S & BCI Campaign |
| 7 | B2B Reseller | B2B Reseller Campaign |
| 8 | DE&NL Retailer | DE & NL Retailer Campaign |
| 9 | EMEA FR&IT | EMEA FR & IT Campaign |
| 10 | PD | PD Campaign |

---

**功能说明：**
- 每个看板实时连接对应的 Google Sheet，刷新即获取最新数据
- 核心指标：Cost (sum)、Impr (sum)、Views (sum)、Clicks (sum)、CPM、CPC、CTR、CPV、VTR（公式计算）
- 筛选器：Country、Platform、Objective、Creative、Creative Sub、Ad Group
- 每日趋势 + 维度对比
- CPC 变动预警（上涨 20%+）
- Plan vs 实际消耗监测（偏差 ±30%、漏投、超范围投放）
""")
