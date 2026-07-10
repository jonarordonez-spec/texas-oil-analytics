
"""
Bronze Layer: Raw data ingestion from .dsv files to Parquet.

This module handles the first stage of the Medallion Architecture:
- Reads raw .dsv files from the Texas Railroad Commission (RRC)
- Converts them to Parquet format with ZSTD compression
- Applies year filter (>= 2015) for large files
- Stores in data/bronze/ directory
"""

import duckdb
from pathlib import Path
from tqdm import tqdm
from src.config import config


def explore_data(con: duckdb.DuckDBPyConnection) -> None:
    """
    Explore raw data files to understand their structure.

    This function is used for initial data understanding before ingestion.
    It lists all files, shows their sizes, and displays sample data.

    Args:
        con: DuckDB connection object
    """

    print("="*80)
    print("DATA UNDERSTANDING & EXPLORATION")
    print("="*80)

    # List files
    files = list(config.DATA_RAW.glob("*.dsv"))
    print(f"\nTotal files found: {len(files)}\n")

    # Show file sizes (top 10)
    print("Top 10 Largest Files:")
    for f in sorted(files, key=lambda x: x.stat().st_size, reverse=True)[:10]:
        size_gb = f.stat().st_size / (1024**3)
        print(f"  {f.name:<50} {size_gb:8.2f} GB")

    # Explore key tables
    key_files = [
        "OG_LEASE_CYCLE_DATA_TABLE.dsv",
        "OG_DISTRICT_CYCLE_DATA_TABLE.dsv",
        "OG_OPERATOR_DW_DATA_TABLE.dsv"
    ]

    for filename in key_files:
        file_path = config.DATA_RAW / filename
        if not file_path.exists():
            continue

        print(f"\n{'='*80}")
        print(f"EXPLORING: {filename}")
        print(f"{'='*80}")

        query = f"""
        SELECT * FROM read_csv_auto('{file_path}', 
            delim='}}', 
            header=True, 
            sample_size=50000,
            ignore_errors=True)
        LIMIT 5
        """
        sample = con.execute(query).df()

        print(f"  Total columns: {len(sample.columns)}")
        print(f"  Sample shape: {sample.shape}")
        print(f"  Columns: {', '.join(sample.columns[:10])}...")


def ingest_bronze(con: duckdb.DuckDBPyConnection) -> None:
    """
    Convert raw .dsv files to Parquet format (Bronze layer).

    This function:
    1. Processes reference files (small to medium size)
    2. Processes the large lease cycle file with year filter
    3. Skips files that already exist to avoid reprocessing

    Args:
        con: DuckDB connection object
    """

    print("="*80)
    print("BRONZE LAYER - Raw Data Ingestion")
    print("="*80)

    # ==========================================================================
    # 1. Process reference files
    # ==========================================================================
    files_to_process = [
        "OG_DISTRICT_CYCLE_DATA_TABLE.dsv",
        "OG_OPERATOR_DW_DATA_TABLE.dsv",
        "OG_FIELD_DW_DATA_TABLE.dsv",
        "OG_WELL_COMPLETION_DATA_TABLE.dsv",
    ]

    print(f"\n[1] Processing {len(files_to_process)} reference files...\n")

    for filename in tqdm(files_to_process, desc="Bronze ingestion"):
        raw_path = config.DATA_RAW / filename
        bronze_path = config.DATA_BRONZE / filename.replace(".dsv", ".parquet")

        # Skip if file doesn't exist in raw
        if not raw_path.exists():
            print(f"  ⚠️ {filename} not found in raw folder, skipping")
            continue

        # Skip if bronze file already exists (avoid reprocessing)
        if bronze_path.exists():
            size_mb = bronze_path.stat().st_size / (1024*1024)
            print(f"  ⏭️ {filename} already exists in bronze ({size_mb:.1f} MB), skipping")
            continue

        try:
            query = f"""
            COPY (
                SELECT * FROM read_csv_auto('{raw_path}', 
                    delim='}}', 
                    header=True,
                    ignore_errors=True)
            ) TO '{bronze_path}' (FORMAT PARQUET, COMPRESSION 'zstd');
            """
            con.execute(query)
            size_mb = bronze_path.stat().st_size / (1024*1024)
            print(f"  ✅ {filename} → {size_mb:.1f} MB")
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {e}")

    # ==========================================================================
    # 2. Process large file with year filter
    # ==========================================================================
    print("\n[2] Processing large file with year filter...")

    large_file = config.DATA_RAW / "OG_LEASE_CYCLE_DATA_TABLE.dsv"
    bronze_large_path = config.DATA_BRONZE / "OG_LEASE_CYCLE_DATA_TABLE.parquet"

    if not large_file.exists():
        print(f"  ⚠️ Large file not found: {large_file}")
    elif bronze_large_path.exists():
        size_gb = bronze_large_path.stat().st_size / (1024**3)
        print(f"  ⏭️ Large file already exists in bronze ({size_gb:.2f} GB), skipping")
    else:
        query = f"""
        COPY (
            SELECT * FROM read_csv_auto('{large_file}', 
                delim='}}', 
                header=True,
                ignore_errors=True)
            WHERE TRY_CAST(CYCLE_YEAR AS INTEGER) >= {config.START_YEAR}
        ) TO '{bronze_large_path}' (FORMAT PARQUET, COMPRESSION 'zstd');
        """
        con.execute(query)
        size_gb = bronze_large_path.stat().st_size / (1024**3)
        print(f"  ✅ Large file processed: {size_gb:.2f} GB")

    # ==========================================================================
    # 3. Verify Bronze layer
    # ==========================================================================
    print("\n[3] Verifying Bronze layer...")
    bronze_files = list(config.DATA_BRONZE.glob("*.parquet"))
    print(f"  Bronze files created: {len(bronze_files)}")

    for f in sorted(bronze_files, key=lambda x: x.stat().st_size, reverse=True)[:5]:
        size_mb = f.stat().st_size / (1024*1024)
        print(f"    {f.name:<50} {size_mb:8.2f} MB")

    print("\n✅ Bronze layer complete!")
