"""
Causal Analysis Module for Texas Oil & Gas Project

This module contains:
- Double Machine Learning (DoubleML) for causal inference
- Heterogeneity analysis (Permian Basin + Operator Size)
- Traditional Fixed Effects OLS econometric model
- Robustness checks and diagnostics
- Reproducibility with fixed random seed

All models use the consistent 500k modeling sample from the Gold layer.
"""

import pandas as pd
import numpy as np
import random
import doubleml as dml
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.utils import check_random_state
import statsmodels.formula.api as smf
from src.config import config
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# REPRODUCIBILITY
# =============================================================================

SEED = config.RANDOM_STATE
random.seed(SEED)
np.random.seed(SEED)
_ = check_random_state(SEED)

print(f"[Reproducibility] Random seed set to: {SEED}")
print("   All results will be reproducible across runs.")

# =============================================================================
# 1. LOAD MODELING SAMPLE (FIXED 500k)
# =============================================================================

def load_modeling_sample(con=None):
    """
    Load the fixed modeling sample with all features (including lags).
    Uses the 500k fixed sample for reproducibility.
    """
    import pandas as pd
    from pathlib import Path
    
    # Try the 500k fixed sample first
    fixed_sample_path = config.DATA_GOLD / "gold_fixed_sample_500k.parquet"
    
    if fixed_sample_path.exists():
        df = pd.read_parquet(fixed_sample_path)
        print(f"[OK] Loaded fixed 500k sample: {len(df):,} rows")
        print(f"   ✅ lag1_prod_boe available: {'lag1_prod_boe' in df.columns}")
        print(f"   ✅ operator_size available: {'operator_size' in df.columns}")
        return df
    
    # Fallback: create 500k sample from DuckDB
    if con is not None:
        try:
            df = con.execute(f"""
                SELECT *
                FROM doubleml_ready_enhanced
                USING SAMPLE 500000 ROWS
            """).df()
            df.to_parquet(fixed_sample_path, compression='zstd')
            print(f"[OK] Created 500k sample: {len(df):,} rows")
            print(f"   ✅ lag1_prod_boe available: {'lag1_prod_boe' in df.columns}")
            return df
        except Exception as e:
            print(f"[ERROR] Could not create 500k sample: {e}")
    
    # Fallback: old 100k sample
    old_sample_path = config.DATA_GOLD / "gold_consistent_modeling_sample.parquet"
    if old_sample_path.exists():
        df = pd.read_parquet(old_sample_path)
        print(f"[WARNING] Loaded old 100k sample: {len(df):,} rows")
        print("   ⚠️ lag1_prod_boe may not be available")
        return df
    
    print("[ERROR] No modeling sample found. Run Gold layer first.")
    return None


# =============================================================================
# 2. DOUBLE MACHINE LEARNING
# =============================================================================

def run_doubleml_analysis(df, model_name="Main Model"):
    """Run DoubleML IRM model with fixed random seed"""
    print(f"\n[START] Running Double ML - {model_name}")

    # Prepare data
    df_clean = df.dropna(subset=['total_prod_boe', 'high_price_treatment', 'wti_price_usd']).copy()
    df_clean['lag1_prod_boe'] = df_clean['lag1_prod_boe'].fillna(df_clean['lag1_prod_boe'].median())

    y = df_clean['total_prod_boe']
    d = df_clean['high_price_treatment']

    X = df_clean[['wti_price_usd', 'is_active_producing', 'lag1_prod_boe', 'permian_dummy']].copy()
    if 'year' in df_clean.columns:
        X = pd.get_dummies(X, columns=['year'], drop_first=True)

    print(f"   Final sample: {len(X):,} rows | Features: {X.shape[1]}")

    # Create DoubleML data object
    dml_data = dml.DoubleMLData(
        data=pd.concat([y.reset_index(drop=True), 
                        d.reset_index(drop=True), 
                        X.reset_index(drop=True)], axis=1),
        y_col='total_prod_boe',
        d_cols='high_price_treatment'
    )

    # Machine learning models with fixed random state
    ml_g = RandomForestRegressor(
        n_estimators=config.ML_ESTIMATORS,
        max_depth=config.ML_MAX_DEPTH,
        random_state=config.RANDOM_STATE
    )
    ml_m = RandomForestClassifier(
        n_estimators=config.ML_ESTIMATORS,
        max_depth=config.ML_MAX_DEPTH,
        random_state=config.RANDOM_STATE
    )

    # Double ML model
    dml_model = dml.DoubleMLIRM(
        obj_dml_data=dml_data,
        ml_g=ml_g,
        ml_m=ml_m,
        n_folds=config.N_FOLDS,
        n_rep=config.N_REP,
        trimming_threshold=0.05
    )

    print("   Fitting model... (this may take 1-3 minutes)")
    dml_model.fit()

    print(f"\n[TABLE] {model_name} Results:")
    print(dml_model.summary)

    return dml_model


# =============================================================================
# 3. HETEROGENEITY ANALYSIS
# =============================================================================

def run_heterogeneity_analysis(df):
    """Run Double ML by subgroups (Permian and Operator Size)"""
    print("\n" + "="*80)
    print("HETEROGENEITY ANALYSIS")
    print("="*80)

    # Permian vs Non-Permian
    for permian_value, name in [(0, "Non-Permian"), (1, "Permian")]:
        subgroup = df[df['permian_dummy'] == permian_value].copy()
        if len(subgroup) < 3000:
            print(f"   [WARNING] {name} sample too small ({len(subgroup):,} rows), skipping")
            continue
        run_doubleml_analysis(subgroup, f"{name} Operators")

    # Large vs Medium/Small Operators
    large = df[df['operator_size'] == 'Large'].copy()
    medium_small = df[df['operator_size'].isin(['Medium', 'Small'])].copy()

    if len(large) > 3000:
        run_doubleml_analysis(large, "Large Operators")
    if len(medium_small) > 3000:
        run_doubleml_analysis(medium_small, "Medium & Small Operators")


# =============================================================================
# 4. TRADITIONAL ECONOMETRIC MODEL (Fixed Effects)
# =============================================================================

def run_econometric_model(df):
    """Run Fixed Effects OLS model with robust standard errors (HC3)"""
    print("\n" + "="*80)
    print("TRADITIONAL ECONOMETRIC MODEL (Fixed Effects OLS)")
    print("="*80)

    model_df = df.copy()
    model_df['year'] = pd.to_datetime(model_df['cycle_date']).dt.year

    # Prepare data: ensure lag1_prod_boe is not null
    model_df['lag1_prod_boe'] = model_df['lag1_prod_boe'].fillna(model_df['lag1_prod_boe'].median())

    formula = "total_prod_boe ~ wti_price_usd + is_active_producing + lag1_prod_boe + C(DISTRICT_NO) + C(year)"

    model = smf.ols(formula, data=model_df).fit(cov_type='HC3')

    print(model.summary())
    return model


# =============================================================================
# 5. ROBUSTNESS CHECKS & DIAGNOSTICS
# =============================================================================

def run_robustness_checks(df):
    """Run all robustness checks: VIF, Wald, Breusch-Pagan, Threshold analysis"""
    print("\n" + "="*80)
    print("ROBUSTNESS CHECKS & DIAGNOSTICS")
    print("="*80)
    
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    
    # Prepare data
    diag_df = df.copy()
    diag_df['year'] = pd.to_datetime(diag_df['cycle_date']).dt.year
    diag_df['is_active'] = diag_df['is_active_producing'].astype(int)
    diag_df['lag1_prod_boe'] = diag_df['lag1_prod_boe'].fillna(diag_df['lag1_prod_boe'].median())
    diag_df = diag_df.dropna(subset=['total_prod_boe', 'wti_price_usd', 'lag1_prod_boe'])
    
    print(f"Sample size: {len(diag_df):,} rows")
    
    # Test 1: Baseline Model
    print("\n[1] Baseline Fixed Effects Model...")
    model_base = smf.ols(
        "total_prod_boe ~ wti_price_usd + is_active + lag1_prod_boe + C(DISTRICT_NO) + C(year)",
        data=diag_df
    ).fit()
    print("  Key Coefficients:")
    print(model_base.summary().tables[1])
    
    # Test 2: Threshold Analysis
    print("\n[2] Threshold Analysis (Different High-Price Thresholds)...")
    thresholds = [70, 75, 80, 85, 90]
    for threshold in thresholds:
        temp_df = diag_df.copy()
        temp_df['high_price_treat'] = (temp_df['wti_price_usd'] >= threshold).astype(int)
        model = smf.ols(
            "total_prod_boe ~ high_price_treat + wti_price_usd + lag1_prod_boe + C(year)",
            data=temp_df
        ).fit()
        coef = model.params.get('high_price_treat', np.nan)
        pval = model.pvalues.get('high_price_treat', np.nan)
        significant = "✅" if pval < 0.05 else "❌"
        print(f"  Threshold = ${threshold}: Coef = {coef:.3f}, p-value = {pval:.4f} {significant}")
    
    # Test 3: Breusch-Pagan
    print("\n[3] Breusch-Pagan Test (Heteroskedasticity)...")
    bp_test = het_breuschpagan(model_base.resid, model_base.model.exog)
    print(f"  LM Statistic: {bp_test[0]:.4f}")
    print(f"  p-value: {bp_test[1]:.4f}")
    if bp_test[1] < 0.05:
        print("  -> Heteroskedasticity present (use robust SE)")
    else:
        print("  -> No significant heteroskedasticity")
    
    # Test 4: VIF
    print("\n[4] VIF (Multicollinearity)...")
    numeric_cols = ['wti_price_usd', 'is_active', 'lag1_prod_boe']
    X_vif = diag_df[numeric_cols].copy()
    vif_data = pd.DataFrame()
    vif_data["Variable"] = numeric_cols
    vif_data["VIF"] = [variance_inflation_factor(X_vif.values, i) for i in range(X_vif.shape[1])]
    print(vif_data.round(2).to_string(index=False))
    print("  -> VIF < 5 indicates no serious multicollinearity")
    
    # Test 5: Wald Test
    print("\n[5] Wald Test - Joint Significance of District Effects...")
    district_terms = [term for term in model_base.params.index if 'C(DISTRICT_NO)[T.' in term]
    if len(district_terms) > 0:
        wald_formula = " = ".join(district_terms) + " = 0"
        wald_test = model_base.wald_test(wald_formula, scalar=True)
        f_stat = wald_test.statistic[0] if hasattr(wald_test.statistic, '__len__') else wald_test.statistic
        p_val = wald_test.pvalue[0] if hasattr(wald_test.pvalue, '__len__') else wald_test.pvalue
        print(f"  F-statistic: {float(f_stat):.4f}")
        print(f"  p-value: {float(p_val):.4f}")
        if float(p_val) < 0.05:
            print("  -> District fixed effects are jointly significant")
        else:
            print("  -> District effects not significant")
    
    print("\n✅ All robustness checks completed.")
    return model_base


# =============================================================================
# 6. COMPLETE CAUSAL ANALYSIS
# =============================================================================

def run_full_causal_analysis(con=None):
    """Run all causal analysis including robustness checks"""
    df = load_modeling_sample(con=con)
    if df is None:
        return None, None, None
    
    print(f"\n🚀 Starting complete causal analysis with {len(df):,} observations")
    
    # 1. Main Double ML
    main_model = run_doubleml_analysis(df, "Main Double ML Model")
    
    # 2. Heterogeneity Analysis
    run_heterogeneity_analysis(df)
    
    # 3. Traditional Econometric Model
    ols_model = run_econometric_model(df)
    
    # 4. Robustness Checks
    robustness_model = run_robustness_checks(df)
    
    print("\n" + "="*80)
    print("✅ COMPLETE CAUSAL ANALYSIS FINISHED")
    print("="*80)
    
    return main_model, ols_model, robustness_model


# =============================================================================
# 7. VISUALIZATION HELPERS
# =============================================================================

def create_results_dataframe():
    """
    Create a DataFrame with all treatment effects for visualization.
    Uses the 500k reproducible results.
    """
    results_data = {
        "Subgroup": ["General", "Permian", "Non-Permian", "Large Operators", "Small/Medium"],
        "ATE": [28.33, 189.31, 22.72, 5.66, 164.03],
        "Lower": [15.43, 158.58, 8.52, -10.21, 147.09],
        "Upper": [41.23, 220.04, 36.92, 21.52, 180.97],
        "Significant": [True, True, True, False, True]
    }
    return pd.DataFrame(results_data)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_full_causal_analysis()