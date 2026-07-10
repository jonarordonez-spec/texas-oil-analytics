
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Causal Analysis", page_icon="📊", layout="wide")

st.title("📊 Causal Analysis Results")

# Results from your Double ML models
results = {
    "Model": ["Double ML", "Permian", "Non-Permian", "Large Operators", "Medium/Small"],
    "ATE": [186.27, 1120.24, 161.07, 344.42, 257.19],
    "p-value": ["5.5e-21", "1.76e-71", "8.56e-18", "5.79e-47", "3.15e-15"]
}
df = pd.DataFrame(results)

st.dataframe(df)

fig = px.bar(df, x='Model', y='ATE', title='Treatment Effects by Subgroup')
st.plotly_chart(fig, use_container_width=True)

st.info("""
**Key Finding**: High oil prices cause a **186.27 BOE** increase per lease per month.
The effect is **7x larger** in the Permian Basin.
""")
