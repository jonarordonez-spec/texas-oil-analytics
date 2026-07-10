
import streamlit as st
import pandas as pd
from src.database import get_duckdb_connection

st.set_page_config(page_title="Data Explorer", page_icon="🔍", layout="wide")

st.title("🔍 Data Explorer")

con = get_duckdb_connection()
df = con.execute("SELECT * FROM doubleml_ready_enhanced USING SAMPLE 10000 ROWS").df()

st.dataframe(df, use_container_width=True, height=400)
st.download_button("Download CSV", df.to_csv(index=False), "data.csv")
