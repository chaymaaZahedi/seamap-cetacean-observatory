import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import logging

# --- CONFIGURATION ---
BASE_DIR = Path("/opt/airflow")
GOLD_DIR = BASE_DIR / "gold_data"
POINTS_DIR = BASE_DIR / "data_source" / "data_sources_point"
INDEX_CSV = BASE_DIR / "index.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

GENERIC_NAMES = {"(no name)", "(unknown)", "unknown", "nan", "", "none"}

def parse_individual_count(val):
    if pd.isna(val) or str(val).strip() == "": return np.nan
    s = str(val).strip()
    if "-" in s:
        parts = s.split("-")
        try: return (float(parts[0]) + float(parts[1])) / 2.0
        except: pass
    try: return float(s)
    except: return np.nan

def run_temporal_etl(dataset_id):
    log.info(f"--- ETL TEMPOREL (v5) : ID {dataset_id} ---")
    
    # 1. Chargement des points
    csv_path = POINTS_DIR / f"obis_seamap_dataset_{dataset_id}_points.csv"
    if not csv_path.exists():
        log.error(f"Fichier points manquant : {csv_path}")
        return

    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = df.columns.str.strip().str.lower()
    
    # 2. Transformation V5 (Temporelle + Déduplication)
    df["date_time_full"] = pd.to_datetime(df["date_time"], errors="coerce")
    df = df.dropna(subset=["date_time_full"])
    df["annee"] = df["date_time_full"].dt.year.astype(int)
    
    # Calcul abondance
    df["count_fixed"] = df["individual_count"].apply(parse_individual_count)
    df["count_fixed"] = df["count_fixed"].fillna(pd.to_numeric(df["group_size"], errors="coerce"))
    df["abondance"] = df["count_fixed"].fillna(1).astype(int)
    
    # Déduplication annuelle par organisme
    df["organism_name"] = df["organism_name"].astype(str).str.strip()
    is_generic = df["organism_name"].str.lower().isin(GENERIC_NAMES)
    df_generic = df[is_generic].copy()
    df_named = df[~is_generic].copy()
    
    df_named = df_named.drop_duplicates(subset=["organism_name", "annee"], keep="first")
    df_final = pd.concat([df_named, df_generic], ignore_index=True)
    
    df_final["index_id"] = str(dataset_id)
    df_final["traitement_type"] = "v5_temporel"

    # 3. MISE À JOUR INCREMENTALE DES FICHIERS GOLD
    update_gold_files(dataset_id, df_final)

def update_gold_files(dataset_id, df_new):
    # --- A. Mise à jour dim_dataset ---
    ds_path = GOLD_DIR / "dim_dataset.csv"
    dim_ds = pd.read_csv(ds_path, dtype=str) if ds_path.exists() else pd.DataFrame()
    if not dim_ds.empty:
        dim_ds = dim_ds[dim_ds['index_id'] != str(dataset_id)]
    
    new_ds_row = pd.DataFrame([{
        'dim_dataset_id': len(dim_ds) + 1,
        'index_id': str(dataset_id),
        'source_file': f"obis_seamap_dataset_{dataset_id}_points.csv",
        'source_type': 'ptphoto',
        'traitement_type': 'v5_temporel',
        'has_track': 'False',
        'effort_length_km': np.nan
    }])
    dim_ds = pd.concat([dim_ds, new_ds_row], ignore_index=True)
    dim_ds.to_csv(ds_path, index=False)

    # --- B. Mise à jour viz_facts_clean ---
    viz_path = GOLD_DIR / "viz_facts_clean.csv"
    if viz_path.exists():
        viz = pd.read_csv(viz_path, low_memory=False)
        viz = viz[viz['index_id'].astype(str) != str(dataset_id)]
        
        df_new["date_time_str"] = df_new["date_time_full"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df_new["effort_length_km"] = np.nan
        
        viz = pd.concat([viz, df_new], ignore_index=True)
        viz.to_csv(viz_path, index=False)
        log.info(f"Gold Data mise à jour (V5) : {len(df_new)} observations ajoutées.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_id", required=True)
    args = parser.parse_args()
    run_temporal_etl(args.dataset_id)
