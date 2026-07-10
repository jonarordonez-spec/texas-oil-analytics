# ==============================================================================
# Texas Oil & Gas Dashboard - Standalone App
# ==============================================================================

import sys
import os

# Add project root to path so 'src' can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==============================================================================
# IMPORTS
# ==============================================================================

import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
import duckdb
from src.config import config

# ==============================================================================
# CONNECT TO DUCKDB (READ-ONLY MODE)
# ==============================================================================

con = duckdb.connect("texas_oil_analytics.duckdb", read_only=True)

# ==============================================================================
# LOAD DATA (500k sample)
# ==============================================================================

print("Loading data...")
df = con.execute("""
    SELECT 
        total_prod_boe,
        wti_price_usd,
        operator_size,
        DISTRICT_NAME,
        cycle_date,
        permian_dummy,
        high_price_treatment
    FROM doubleml_ready_enhanced
    USING SAMPLE 500000 ROWS
""").df()

print(f"Data loaded: {len(df):,} rows")

# ==============================================================================
# RESULTS FROM 500k SAMPLE
# ==============================================================================

results_data = {
    "Subgroup": ["General", "Permian", "Non-Permian", "Large Operators", "Small/Medium"],
    "ATE": [28.33, 189.31, 22.72, 5.66, 164.03],
    "Lower": [15.43, 158.58, 8.52, -10.21, 147.09],
    "Upper": [41.23, 220.04, 36.92, 21.52, 180.97],
    "Significant": [True, True, True, False, True]
}
df_results = pd.DataFrame(results_data)

# ==============================================================================
# DASHBOARD
# ==============================================================================

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("🛢️ Texas Oil & Gas Causal Analysis", style={"textAlign": "center"}),
    
    html.H3("Average Treatment Effects by Subgroup (500k Sample)"),
    dcc.Graph(
        figure=px.bar(
            df_results,
            x="Subgroup",
            y="ATE",
            error_y=df_results["Upper"] - df_results["ATE"],
            error_y_minus=df_results["ATE"] - df_results["Lower"],
            title="Double ML Treatment Effects (500k Sample)",
            labels={"ATE": "BOE per lease per month", "Subgroup": ""},
            color="Significant",
            color_discrete_map={True: "#1f77b4", False: "#d62728"}
        )
    ),
    
    html.H3("Production vs WTI Price"),
    dcc.Graph(
        figure=px.scatter(
            df,
            x="wti_price_usd",
            y="total_prod_boe",
            color="operator_size",
            title="Production vs WTI Price",
            labels={
                "wti_price_usd": "WTI Price (USD/BBL)",
                "total_prod_boe": "Production (BOE)",
                "operator_size": "Operator Size"
            },
            opacity=0.6
        )
    ),
    
    html.H3("Production by District"),
    dcc.Graph(
        figure=px.box(
            df,
            x="DISTRICT_NAME",
            y="total_prod_boe",
            title="Production Distribution by District",
            labels={"DISTRICT_NAME": "District", "total_prod_boe": "Production (BOE)"}
        )
    ),
    
    html.Hr(),
    html.P("Data: Texas Railroad Commission (RRC) | Sample: 500,000 rows | SEED=42"),
    html.P(f"ATE: 28.33 BOE/lease/month (p < 0.001) | Observations: {len(df):,}"),
], style={"maxWidth": "1200px", "margin": "auto", "padding": "20px"})

if __name__ == "__main__":
    app.run(debug=True, port=8050)