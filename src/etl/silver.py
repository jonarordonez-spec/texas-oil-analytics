
"""
Silver Layer: Data cleaning, transformation, and feature engineering.

This module handles the second stage of the Medallion Architecture:
- Loads WTI oil prices from FRED
- Cleans and standardizes lease production data
- Creates derived metrics (BOE, liquid production, activity flags)
- Saves to data/silver/ as Parquet
"""

import duckdb
import pandas as pd
from src.config import config


def load_wti_prices(con: duckdb.DuckDBPyConnection) -> None:
    """
    Load WTI monthly prices from FRED or local Parquet file.

    If the Parquet file doesn't exist, downloads data from FRED.
    If it exists, loads from the cached file.

    Args:
        con: DuckDB connection object
    """

    print("\n[1] Loading WTI Monthly Prices...")
    wti_file = config.DATA_GOLD / "wti_monthly_price.parquet"

    if wti_file.exists():
        con.execute(f"""
            CREATE OR REPLACE TABLE wti_monthly_price AS 
            SELECT * FROM read_parquet('{wti_file}')
        """)
        wti_count = con.execute("SELECT COUNT(*) FROM wti_monthly_price").fetchone()[0]
        print(f"  ✅ WTI prices loaded from cache: {wti_count:,} rows")
    else:
        print("  ⚠️ WTI file not found. Downloading from FRED...")
        download_wti_data()
        con.execute(f"""
            CREATE OR REPLACE TABLE wti_monthly_price AS 
            SELECT * FROM read_parquet('{wti_file}')
        """)
        wti_count = con.execute("SELECT COUNT(*) FROM wti_monthly_price").fetchone()[0]
        print(f"  ✅ WTI prices downloaded and loaded: {wti_count:,} rows")


def download_wti_data() -> None:
    """
    Download WTI data from FRED and save as Parquet.

    Uses the FRED API to download monthly WTI prices.
    Saves to data/gold/wti_monthly_price.parquet for future use.
    """
    import pandas as pd

    url = "https://fred.stlouisfed.org/graph/fredgraph.xls?bgcolor=%23e1e9f0&chart_type=line&drp=0&fo=open%20sans&graph_bgcolor=%23ffffff&height=450&mode=fred&recession_bars=on&txtcolor=%23444444&ts=12&tts=12&width=1168&nt=0&thu=0&trc=0&show_legend=yes&show_axis_titles=yes&show_tooltip=yes&id=WTISPLC&scale=left&cosd=1986-01-01&coed=2026-06-12&line_color=%234572a7&link_values=false&line_style=solid&mark_type=none&mw=3&lw=3&ost=-99999&oet=99999&mma=0&fml=a&fq=Monthly&fam=avg&fgst=lin&fgsnd=2020-02-01&line_index=1&transformation=lin&vintage_date=2026-06-16&revision_date=2026-06-16&nd=1986-01-01"

    print("  📥 Downloading from FRED...")
    df_wti = pd.read_excel(url, sheet_name="Data 1", skiprows=2)
    df_wti.columns = ['cycle_date', 'wti_price_usd']
    df_wti['cycle_date'] = pd.to_datetime(df_wti['cycle_date'])
    df_wti = df_wti[df_wti['cycle_date'] >= f'{config.START_YEAR}-01-01'].copy()
    df_wti = df_wti.dropna(subset=['wti_price_usd'])
    df_wti.to_parquet(config.DATA_GOLD / "wti_monthly_price.parquet", index=False)
    print(f"  ✅ WTI data saved: {len(df_wti):,} rows")


def create_silver_table(con: duckdb.DuckDBPyConnection) -> None:
    """
    Create the main silver table with cleaned and enriched data.

    This function:
    1. Reads the main lease table from Bronze
    2. Standardizes dates from CYCLE_YEAR_MONTH
    3. Calculates production metrics (BOE, liquid, gas)
    4. Creates activity flags
    5. Standardizes column names
    6. Saves to Parquet and returns summary

    Args:
        con: DuckDB connection object
    """

    print("\n[2] Creating Silver Table (Cleaned + Enriched)...")

    lease_bronze_path = config.DATA_BRONZE / "OG_LEASE_CYCLE_DATA_TABLE.parquet"

    # Check if Bronze file exists
    if not lease_bronze_path.exists():
        print(f"  ❌ Bronze file not found: {lease_bronze_path}")
        print("  Please run Bronze layer first.")
        return

    # Check if Silver table already exists in DuckDB
    silver_exists = con.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'lease_cycle_silver'
        )
    """).fetchone()[0]

    if silver_exists:
        silver_count = con.execute("SELECT COUNT(*) FROM lease_cycle_silver").fetchone()[0]
        print(f"  ⏭️ Silver table already exists with {silver_count:,} rows, skipping creation")
        print("  If you want to recreate, drop the table first.")
        return

    print("  📦 Creating silver table from Bronze...")

    con.execute(f"""
    CREATE OR REPLACE TABLE lease_cycle_silver AS
    SELECT 
        *,
        -- Date standardization
        MAKE_DATE(
            CAST(SUBSTR(CAST(CYCLE_YEAR_MONTH AS VARCHAR), 1, 4) AS INTEGER),
            CAST(SUBSTR(CAST(CYCLE_YEAR_MONTH AS VARCHAR), 5, 2) AS INTEGER),
            1
        ) AS cycle_date,

        -- Production metrics
        COALESCE(LEASE_OIL_PROD_VOL, 0) + COALESCE(LEASE_COND_PROD_VOL, 0) AS total_liquid_prod,
        COALESCE(LEASE_GAS_PROD_VOL, 0) AS total_gas_prod,
        COALESCE(LEASE_CSGD_PROD_VOL, 0) AS total_csgd_prod,

        -- BOE (Barrel of Oil Equivalent) approximation
        (COALESCE(LEASE_OIL_PROD_VOL, 0) + 
         COALESCE(LEASE_COND_PROD_VOL, 0) + 
         COALESCE(LEASE_GAS_PROD_VOL, 0) / 6.0) AS total_prod_boe,

        -- Activity flag
        (COALESCE(LEASE_OIL_PROD_VOL, 0) + 
         COALESCE(LEASE_GAS_PROD_VOL, 0) + 
         COALESCE(LEASE_COND_PROD_VOL, 0) > 0) AS is_active_producing,

        -- Standardized names
        LOWER(REPLACE(OIL_GAS_CODE, ' ', '_')) AS oil_gas_code_std,
        LOWER(REPLACE(DISTRICT_NAME, ' ', '_')) AS district_name_std

    FROM '{lease_bronze_path}'
    WHERE TRY_CAST(CYCLE_YEAR AS INTEGER) >= {config.START_YEAR}
    """)

    silver_count = con.execute("SELECT COUNT(*) FROM lease_cycle_silver").fetchone()[0]
    print(f"  ✅ Silver table created: {silver_count:,} rows")

    # Save to Parquet
    silver_parquet_path = config.DATA_SILVER / "lease_cycle_silver.parquet"
    con.execute(f"""
    COPY lease_cycle_silver TO '{silver_parquet_path}' 
    (FORMAT PARQUET, COMPRESSION 'zstd')
    """)
    print(f"  ✅ Saved to: {silver_parquet_path}")

    # Show summary
    print("\n📊 Silver Layer Summary:")
    summary = con.execute("""
        SELECT 
            MIN(cycle_date) as first_date,
            MAX(cycle_date) as last_date,
            COUNT(DISTINCT LEASE_NO) as unique_leases,
            COUNT(DISTINCT OPERATOR_NO) as unique_operators,
            AVG(total_liquid_prod) as avg_liquid_prod,
            AVG(total_gas_prod) as avg_gas_prod,
            SUM(total_prod_boe)/1000000 as total_boe_millions
        FROM lease_cycle_silver
    """).df()
    print(summary.to_string(index=False))

    print("\n✅ Silver layer complete!")


def run_silver_pipeline(con: duckdb.DuckDBPyConnection) -> None:
    """
    Run the complete silver layer pipeline.

    Orchestrates the entire silver process:
    1. Load WTI prices
    2. Create silver table

    Args:
        con: DuckDB connection object
    """
    print("="*80)
    print("SILVER LAYER - Data Cleaning & Feature Engineering")
    print("="*80)

    load_wti_prices(con)
    create_silver_table(con)
