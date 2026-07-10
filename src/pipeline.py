"""
Main Pipeline Orchestrator for Texas Oil & Gas Causal Analysis Project.

This module runs the complete ETL pipeline in the correct order:
1. Bronze Layer
2. Silver Layer  
3. Gold Layer

Does NOT modify any existing code or results.
"""

import duckdb
import pandas as pd
from src.config import config
from src.database import get_duckdb_connection, verify_connections
from src.etl.bronze import ingest_bronze
from src.etl.silver import run_silver_pipeline
from src.etl.gold import create_gold_aggregations


def run_full_pipeline() -> pd.DataFrame:
    """
    Run the complete ETL pipeline from Bronze to Gold.

    Returns:
        pd.DataFrame: The consistent modeling sample ready for causal analysis.
    """
    print("="*80)
    print("RUNNING FULL ETL PIPELINE")
    print("="*80)

    # 1. Verify database connections
    con, engine = verify_connections()

    # 2. Bronze Layer
    print("\n[1/3] Running Bronze Layer...")
    ingest_bronze(con)

    # 3. Silver Layer
    print("\n[2/3] Running Silver Layer...")
    run_silver_pipeline(con)

    # 4. Gold Layer
    print("\n[3/3] Running Gold Layer...")
    consistent_sample = create_gold_aggregations(con)

    print("\n" + "="*80)
    print("✅ FULL PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*80)
    print(f"📊 Consistent modeling sample ready: {len(consistent_sample):,} rows")

    return consistent_sample


def main():
    """Entry point when running as script"""
    consistent_sample = run_full_pipeline()
    print(f"\n🎯 Pipeline finished. Ready for causal analysis (Double ML, etc.)")
    return consistent_sample


if __name__ == "__main__":
    main()
