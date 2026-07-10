# src/etl/gold.py
"""
Gold Layer: Aggregations, feature engineering, and modeling sample.
"""

import duckdb
import pandas as pd
from src.config import config


def table_exists(con, table_name):
    """Check if a table exists in DuckDB."""
    result = con.execute(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """).fetchone()[0]
    return result


def create_gold_aggregations(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Create all gold layer aggregations and modeling sample.
    Skips steps that are already completed.
    """
    print("="*80)
    print("GOLD LAYER - Aggregations & Modeling Sample")
    print("="*80)

    # Check if silver table exists
    if not table_exists(con, 'lease_cycle_silver'):
        print("ERROR: Silver table 'lease_cycle_silver' not found!")
        print("   Please run the Silver layer first.")
        return None

    # ==========================================================================
    # 1. Monthly Production by District
    # ==========================================================================
    print("\n[1] Creating gold_monthly_district...")

    if table_exists(con, 'gold_monthly_district'):
        district_count = con.execute("SELECT COUNT(*) FROM gold_monthly_district").fetchone()[0]
        print(f"  SKIP: gold_monthly_district already exists with {district_count:,} rows")
    else:
        con.execute("""
        CREATE TABLE gold_monthly_district AS
        SELECT
            DISTRICT_NO,
            DISTRICT_NAME,
            cycle_date,
            EXTRACT(YEAR FROM cycle_date) AS year,
            EXTRACT(MONTH FROM cycle_date) AS month,
            COUNT(DISTINCT LEASE_NO) AS num_leases,
            SUM(total_liquid_prod) AS total_liquid_prod,
            SUM(total_gas_prod) AS total_gas_prod,
            SUM(total_prod_boe) AS total_prod_boe,
            AVG(total_prod_boe) AS avg_prod_boe_per_lease,
            SUM(CASE WHEN is_active_producing THEN 1 ELSE 0 END) AS active_leases
        FROM lease_cycle_silver
        GROUP BY DISTRICT_NO, DISTRICT_NAME, cycle_date, year, month
        ORDER BY cycle_date
        """)
        district_count = con.execute("SELECT COUNT(*) FROM gold_monthly_district").fetchone()[0]
        print(f"  CREATED: {district_count:,} rows")

    # ==========================================================================
    # 2. Monthly Production by Operator
    # ==========================================================================
    print("\n[2] Creating gold_monthly_operator...")

    if table_exists(con, 'gold_monthly_operator'):
        operator_count = con.execute("SELECT COUNT(*) FROM gold_monthly_operator").fetchone()[0]
        print(f"  SKIP: gold_monthly_operator already exists with {operator_count:,} rows")
    else:
        con.execute("""
        CREATE TABLE gold_monthly_operator AS
        SELECT
            OPERATOR_NO,
            OPERATOR_NAME,
            cycle_date,
            SUM(total_liquid_prod) AS total_liquid_prod,
            SUM(total_gas_prod) AS total_gas_prod,
            SUM(total_prod_boe) AS total_prod_boe,
            COUNT(DISTINCT LEASE_NO) AS num_leases
        FROM lease_cycle_silver
        GROUP BY OPERATOR_NO, OPERATOR_NAME, cycle_date
        ORDER BY cycle_date
        """)
        print("  CREATED: gold_monthly_operator")

    # ==========================================================================
    # 3. Save Gold tables to Parquet
    # ==========================================================================
    print("\n[3] Saving Gold tables to Parquet...")

    district_parquet = config.DATA_GOLD / "gold_monthly_district.parquet"
    operator_parquet = config.DATA_GOLD / "gold_monthly_operator.parquet"

    if district_parquet.exists() and operator_parquet.exists():
        print("  SKIP: Gold tables already saved to Parquet")
    else:
        con.execute(f"""
        COPY gold_monthly_district TO '{district_parquet}'
        (FORMAT PARQUET, COMPRESSION 'zstd')
        """)
        con.execute(f"""
        COPY gold_monthly_operator TO '{operator_parquet}'
        (FORMAT PARQUET, COMPRESSION 'zstd')
        """)
        print("  CREATED: Gold tables saved to Parquet")

    # ==========================================================================
    # 4. Enriched Table with WTI prices
    # ==========================================================================
    print("\n[4] Creating enriched_lease_cycle with WTI prices...")

    if table_exists(con, 'enriched_lease_cycle'):
        enriched_count = con.execute("SELECT COUNT(*) FROM enriched_lease_cycle").fetchone()[0]
        print(f"  SKIP: enriched_lease_cycle already exists with {enriched_count:,} rows")
    else:
        con.execute("""
        CREATE TABLE enriched_lease_cycle AS
        SELECT
            s.*,
            w.wti_price_usd,
            CASE WHEN COALESCE(w.wti_price_usd, 0) >= 80 THEN 1 ELSE 0 END AS high_price_treatment,
            CASE
                WHEN COALESCE(w.wti_price_usd, 0) >= 80 THEN 'High_Price'
                WHEN COALESCE(w.wti_price_usd, 0) >= 60 THEN 'Medium_Price'
                ELSE 'Low_Price'
            END AS price_regime,
            CASE WHEN s.DISTRICT_NO IN ('08', '10') THEN 1 ELSE 0 END AS permian_dummy
        FROM lease_cycle_silver s
        LEFT JOIN wti_monthly_price w
            ON DATE_TRUNC('month', s.cycle_date) = DATE_TRUNC('month', w.cycle_date)
        """)
        enriched_count = con.execute("SELECT COUNT(*) FROM enriched_lease_cycle").fetchone()[0]
        print(f"  CREATED: Enriched table with {enriched_count:,} rows")

    # ==========================================================================
    # 5. Consistent Modeling Sample
    # ==========================================================================
        
    
    print("\n[5] Creating consistent modeling sample...")

    sample_path = config.DATA_GOLD / "gold_consistent_modeling_sample.parquet"

    if sample_path.exists() and sample_path.stat().st_size > 100_000:  # Small file check
        size_mb = sample_path.stat().st_size / (1024 * 1024)
        print(f"  SKIP: Modeling sample already exists ({size_mb:.1f} MB)")
        consistent_sample = pd.read_parquet(sample_path)
    else:
        print(f"  Creating new consistent sample with {config.SAMPLE_SIZE:,} rows...")
        consistent_sample = con.execute(f"""
            SELECT
                LEASE_NO,
                OPERATOR_NO,
                OPERATOR_NAME,
                DISTRICT_NO,
                DISTRICT_NAME,
                cycle_date,
                total_prod_boe,
                total_liquid_prod,
                total_gas_prod,
                is_active_producing,
                wti_price_usd,
                high_price_treatment,
                price_regime,
                permian_dummy,
                operator_size,
                EXTRACT(YEAR FROM cycle_date) AS year,
                lag1_prod_boe,
                lag2_prod_boe
            FROM doubleml_ready_enhanced
            USING SAMPLE {config.SAMPLE_SIZE} ROWS
        """).df()
        
        consistent_sample.to_parquet(sample_path, compression='zstd')
        print(f"  CREATED: Consistent sample with {len(consistent_sample):,} rows")

    return consistent_sample
    # ==========================================================================
    # 6. Feature Engineering: Operator Size
    # ==========================================================================
    print("\n[6] Feature Engineering: Operator Size...")

    if table_exists(con, 'operator_size'):
        operator_count = con.execute("SELECT COUNT(*) FROM operator_size").fetchone()[0]
        print(f"  SKIP: operator_size already exists with {operator_count:,} rows")
    else:
        operator_size = con.execute("""
            SELECT
                OPERATOR_NO,
                OPERATOR_NAME,
                COUNT(DISTINCT LEASE_NO) as num_leases,
                CASE
                    WHEN COUNT(DISTINCT LEASE_NO) <= 10 THEN 'Small'
                    WHEN COUNT(DISTINCT LEASE_NO) <= 100 THEN 'Medium'
                    ELSE 'Large'
                END as operator_size
            FROM lease_cycle_silver
            GROUP BY OPERATOR_NO, OPERATOR_NAME
        """).df()
        con.execute("CREATE TABLE operator_size AS SELECT * FROM operator_size")
        print(f"  CREATED: Operator size table with {len(operator_size):,} unique operators")

    # ==========================================================================
    # 7. Enhanced Table with operator_size and lags
    # ==========================================================================
    print("\n[7] Creating enhanced table with operator_size and lags...")

    if table_exists(con, 'doubleml_ready_enhanced'):
        enhanced_count = con.execute("SELECT COUNT(*) FROM doubleml_ready_enhanced").fetchone()[0]
        print(f"  SKIP: doubleml_ready_enhanced already exists with {enhanced_count:,} rows")
    else:
        con.execute("""
            CREATE TABLE doubleml_ready_enhanced AS
            SELECT
                e.*,
                COALESCE(o.operator_size, 'Medium') as operator_size,
                LAG(e.total_prod_boe, 1) OVER (PARTITION BY e.LEASE_NO ORDER BY e.cycle_date) AS lag1_prod_boe,
                LAG(e.total_prod_boe, 2) OVER (PARTITION BY e.LEASE_NO ORDER BY e.cycle_date) AS lag2_prod_boe
            FROM enriched_lease_cycle e
            LEFT JOIN operator_size o
                ON e.OPERATOR_NO = o.OPERATOR_NO
        """)

        enhanced_parquet = config.DATA_GOLD / "doubleml_ready_enhanced.parquet"
        con.execute(f"""
        COPY doubleml_ready_enhanced TO '{enhanced_parquet}'
        (FORMAT PARQUET, COMPRESSION 'zstd')
        """)
        print("  CREATED: Enhanced table with operator_size, lag1_prod_boe, lag2_prod_boe")

    print("\n" + "="*80)
    print("GOLD LAYER COMPLETE")
    print("="*80)
    return consistent_sample


def verify_gold_layer(con: duckdb.DuckDBPyConnection) -> None:
    """Verify all gold layer tables exist and show summary statistics."""
    print("="*60)
    print("GOLD LAYER VERIFICATION")
    print("="*60)

    tables = [
        "gold_monthly_district",
        "gold_monthly_operator",
        "enriched_lease_cycle",
        "operator_size",
        "doubleml_ready_enhanced"
    ]

    print("\n[1] Table Status:")
    for table in tables:
        exists = table_exists(con, table)
        if exists:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  [OK] {table}: {count:,} rows")
        else:
            print(f"  [MISSING] {table}: not found")

    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)
