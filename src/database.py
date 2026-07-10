# src/database.py
"""
Database connection management for the Texas Oil & Gas Analytics Pipeline.
Handles connections to DuckDB (persistent) and PostgreSQL.
"""

import duckdb
from sqlalchemy import create_engine, text
from src.config import config
import os

# ==============================================================================
# PERSISTENT DUCKDB FILE (TABLES SURVIVE REBOOTS)
# ==============================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUCKDB_FILE = os.path.join(PROJECT_ROOT, "texas_oil_analytics.duckdb")

print(f"DuckDB persistent file: {DUCKDB_FILE}")

def get_duckdb_connection():
    """
    Create a DuckDB connection using a PERSISTENT file on disk.
    Tables survive across notebook sessions and system reboots.
    """
    con = duckdb.connect(DUCKDB_FILE)
    con.execute("SELECT 1").df()
    print("DuckDB connected (persistent mode)")
    print(f"  File: {DUCKDB_FILE}")
    return con


def get_postgresql_engine():
    """Create a SQLAlchemy engine for PostgreSQL."""
    try:
        engine = create_engine(config.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0][:50]
            print(f"PostgreSQL connected: {version}...")
        return engine
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        print("  Continuing with DuckDB only...")
        return None


def verify_connections():
    """Verify both database connections."""
    print("="*60)
    print("DATABASE CONNECTIONS")
    print("="*60)

    print("\n[1] DuckDB Connection:")
    con = get_duckdb_connection()

    print("\n[2] PostgreSQL Connection:")
    engine = get_postgresql_engine()

    print("\nDatabase connections verified!")
    return con, engine