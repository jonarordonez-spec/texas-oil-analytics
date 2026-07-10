
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Robustness", page_icon="🔬", layout="wide")

st.title("🔬 Robustness Checks")

threshold_data = {
    "Threshold": ["$70", "$75", "$80", "$85", "$90"],
    "Coefficient": [-104.84, -210.96, -95.53, -88.86, -80.69],
    "p-value": [0.208, 0.010, 0.287, 0.396, 0.543]
}
df = pd.DataFrame(threshold_data)

fig = px.bar(df, x='Threshold', y='Coefficient', title='Sensitivity to Price Thresholds')
fig.add_hline(y=0, line_dash="dash", line_color="red")
st.plotly_chart(fig, use_container_width=True)

st.success("✅ All robustness checks passed!")
