"""
Centralized configuration for the Texas Oil & Gas Analytics Pipeline.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration for the entire pipeline"""

    def __init__(self):
        # ======================================================================
        # Paths
        # ======================================================================
        self.DATA_RAW = Path("data/raw")
        self.DATA_BRONZE = Path("data/bronze")
        self.DATA_SILVER = Path("data/silver")
        self.DATA_GOLD = Path("data/gold")
        self.DOCS = Path("docs")

        # ======================================================================
        # PostgreSQL Configuration (from environment variables)
        # ======================================================================
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mi_secreto")

        # ======================================================================
        # Data Parameters
        # ======================================================================
        self.START_YEAR = 2015
        self.SAMPLE_SIZE = 500000
        self.PRICE_THRESHOLD = 80.0
        self.CHUNK_SIZE = 500000

        # ======================================================================
        # Model Parameters (Double ML)
        # ======================================================================
        self.N_FOLDS = 3
        self.N_REP = 2
        self.ML_ESTIMATORS = 60
        self.ML_MAX_DEPTH = 5
        self.RANDOM_STATE = 42

        # ======================================================================
        # Feature Engineering
        # ======================================================================
        self.OPERATOR_SIZE_THRESHOLDS = {"small": 10, "medium": 100}

    @property
    def DATABASE_URL(self) -> str:
        """PostgreSQL connection URL for SQLAlchemy"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def all_paths(self) -> list:
        """List of all data paths for directory creation"""
        return [
            self.DATA_RAW,
            self.DATA_BRONZE,
            self.DATA_SILVER,
            self.DATA_GOLD,
            self.DOCS,
        ]


# ==============================================================================
# Create singleton instance
# ==============================================================================
config = Config()