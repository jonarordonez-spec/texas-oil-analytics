# 🛢️ Texas Oil & Gas Causal Inference Analysis

**Quantifying the Causal Effect of High Oil Prices on Production using Double Machine Learning**

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![DuckDB](https://img.shields.io/badge/DuckDB-000000?style=for-the-badge&logo=duckdb&logoColor=white)](https://duckdb.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![DoubleML](https://img.shields.io/badge/DoubleML-FF6F00?style=for-the-badge)](https://docs.doubleml.org)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com)

---

## 📊 Project Overview

Production-grade causal inference project analyzing **31.9 million observations** from the Texas Railroad Commission to estimate the causal impact of high oil prices on production.

### Key Results
- **Average Treatment Effect (ATE)**: +28.33 BOE per lease/month (p < 0.001)
- **Permian Basin**: Much stronger response (+189 BOE)
- **Small/Medium Operators**: Highly responsive

---

## 🏗️ Architecture

### Medallion Architecture
```mermaid
graph LR
    A[BRONZE<br/>Raw .dsv files] --> B[SILVER<br/>Cleaning & Feature Engineering]
    B --> C[GOLD<br/>Aggregations & Modeling Sample]
    C --> D[Analysis<br/>DoubleML + Econometrics]

---

## 5 Keys Framework

CONNECT — RRC data + EIA WTI prices
BUFFER — Raw data as Parquet (Bronze)
PROCESS — Cleaning & Feature Engineering (Silver + Gold)
STORE — PostgreSQL with indexes and views
VISUALIZE — Interactive Plotly dashboards

---

## 🛠️ Tech Stack
<div align="center">
Layer	Technology	Purpose
⚡ Processing	DuckDB	Fast analytics on 30M+ rows
💾 Storage	Parquet + PostgreSQL	Efficient & production-ready
🔧 Pipeline	Python + Modular ETL	Reproducible & idempotent
🎯 Causal Inference	DoubleML + scikit-learn	Modern causal estimation
📊 Econometrics	statsmodels	Traditional robustness
📈 Visualization	Plotly, Matplotlib, Seaborn	Interactive dashboards
🐳 Container	Docker	PostgreSQL containerization
</div>


---

## 📁 Project Structure
text
texas-oil-gas-analytics/
├── 📁 src/                     # Source code
│   ├── ⚙️ config.py            # Centralized configuration
│   ├── 🗄️ database.py          # DuckDB + PostgreSQL connections
│   ├── 🔄 pipeline.py          # Main orchestrator
│   ├── 📁 etl/                 # ETL pipeline
│   │   ├── bronze.py           # Raw data ingestion
│   │   ├── silver.py           # Data cleaning & transformation
│   │   └── gold.py             # Aggregations & feature engineering
│   └── 📁 analysis/            # Causal analysis
│       └── causal_models.py    # Double ML, OLS, robustness checks
├── 📁 dashboard/               # Interactive dashboard
│   ├── app.py                  # Dash application
│   └── pages/                  # Multi-page layout
├── 📁 data/                    # Data layers
│   ├── 📁 bronze/              # Raw data in Parquet
│   ├── 📁 silver/              # Cleaned data
│   └── 📁 gold/                # Aggregations & modeling sample
├── 📁 docs/                    # Documentation
├── 📁 outputs/                 # Generated reports
├── 📁 logs/                    # Structured logs
├── 📄 .gitignore
├── 📄 README.md
├── 📄 requirements.txt
└── 📓 01_texas_oil_causal_analysis_final.ipynb

---

## 🚀 Quick Start
### Prerequisites

Python 3.9+  |  Docker (optional)  |  16GB+ RAM  |  Git

---

## Installation

# Clone repository
git clone https://github.com/jonarordonez-spec/texas-oil-analytics.git
cd texas-oil-analytics

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

---

## Run the Analysis

# Run the full analysis
jupyter notebook 01_texas_oil_causal_analysis_final.ipynb

# Or run specific components
python -c "from src.pipeline import run_full_pipeline; run_full_pipeline()"
python -c "from src.analysis.causal_models import run_full_causal_analysis; run_full_causal_analysis()"

---

## Launch Dashboard

# Windows
run_dashboard.bat

# Or directly
python dashboard\app.py

Open your browser at http://localhost:8050

---

## 📊 Methodology

Research Design
Component	Specification
Treatment (T)	High oil price (WTI ≥ $80/barrel)
Outcome (Y)	Monthly production per lease (BOE)
Confounders (X)	Year, district, lagged production, active status, operator size
ML Models	Random Forest (n=60, depth=5)
Cross-fitting	3 folds, 2 repetitions


---

## Why Double ML?
Issue	OLS	Double ML
🔴 Confounding bias	❌ Sensitive	✅ Robust via ML
🔴 Non-linear relationships	❌ Linear only	✅ Flexible ML
🔴 Causal interpretation	❌ Correlational	✅ Causal

---

## 📚 References
Chernozhukov, V., et al. (2018). "Double/Debiased Machine Learning for Treatment and Causal Parameters." The Econometrics Journal, 21(1), C1-C68.

Hamilton, J. D. (2009). "Causes and Consequences of the Oil Shock of 2007-08." Brookings Papers on Economic Activity.

Kilian, L. (2009). "Not All Oil Price Shocks Are Alike." American Economic Review, 99(3), 1053-1069.

Data Sources
Texas Railroad Commission (RRC). Production Data Query.

U.S. Energy Information Administration (EIA). WTI Crude Oil Prices.

Federal Reserve Economic Data (FRED). WTI Spot Price.

---

## 👤 Author
<div align="center">
Jonathan Ruiz Ordoñez

https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white
https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white

</div>

---

## 📄 License
MIT © Jonathan Ruiz Ordoñez

<div align="center">
⭐ If you found this project useful, please consider starring the repository!
</div> ```
























LayerTechnologyPurposeProcessingDuckDBFast analytics on 30M+ rowsStorageParquet + PostgreSQLEfficient & production-readyPipelinePython + Modular ETLReproducible & idempotentCausal InferenceDoubleML + scikit-learnModern causal estimationEconometricsstatsmodelsTraditional robustnessVisualizationPlotlyInteractive dashboards
