import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import warnings

# On ignore les warnings GeoPandas/Pandas
warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
BASE_DIR = Path("/opt/airflow")
GOLD_DIR = BASE_DIR / "gold_data"
POINTS_DIR = BASE_DIR / "data_source" / "data_sources_point"
TRACKS_DIR = BASE_DIR / "data_source" / "data_sources_survey_tracks"
INDEX_CSV = BASE_DIR / "index.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def run_spatial_etl(dataset_id):
    log.info(f"--- ETL SPATIAL : ID {dataset_id} ---")
    
    # 1. Chargement des points
    csv_path = POINTS_DIR / f"obis_seamap_dataset_{dataset_id}_points.csv"
    if not csv_path.exists():
        log.error(f"Fichier points manquant : {csv_path}")
        return

    df_new = pd.read_csv(csv_path, low_memory=False)
    df_new.columns = df_new.columns.str.strip().str.lower()
    
    # 2. Calcul de l'effort (Distance)
    effort_km = np.nan
    gdb_path = TRACKS_DIR / f"obis_seamap_dataset_{dataset_id}.gdb"
    if gdb_path.exists():
        try:
            import geopandas as gpd
            layer = f"obis_seamap_dataset_{dataset_id}_lines"
            gdf = gpd.read_file(str(gdb_path), layer=layer)
            if gdf.crs is None: gdf.set_crs("EPSG:4326", inplace=True)
            effort_km = gdf.to_crs("EPSG:3035").geometry.length.sum() / 1000
            log.info(f"Effort calculé : {effort_km:.2f} km")
        except Exception as e:
            log.warning(f"Erreur GDB : {e}")
    
    # 3. Préparation des données (Format Gold)
    df_new["date_time_full"] = pd.to_datetime(df_new["date_time"], errors="coerce")
    df_new = df_new.dropna(subset=["date_time_full"])
    df_new["abondance"] = pd.to_numeric(df_new["group_size"], errors="coerce").fillna(1).astype(int)
    df_new["index_id"] = str(dataset_id)
    df_new["traitement_type"] = "v4_spatial"

    # 4. MISE À JOUR INCREMENTALE DES FICHIERS GOLD
    update_gold_files(dataset_id, df_new, effort_km)

def update_gold_files(dataset_id, df_new, effort_km):
    # --- A. Mise à jour dim_dataset ---
    ds_path = GOLD_DIR / "dim_dataset.csv"
    dim_ds = pd.read_csv(ds_path, dtype=str) if ds_path.exists() else pd.DataFrame()
    
    # On retire l'ancien s'il existe
    if not dim_ds.empty:
        dim_ds = dim_ds[dim_ds['index_id'] != str(dataset_id)]
    
    new_ds_row = pd.DataFrame([{
        'dim_dataset_id': len(dim_ds) + 1,
        'index_id': str(dataset_id),
        'source_file': f"obis_seamap_dataset_{dataset_id}_points.csv",
        'source_type': 'ptobs',
        'traitement_type': 'v4_spatial',
        'has_track': 'True' if not np.isnan(effort_km) else 'False',
        'effort_length_km': effort_km
    }])
    dim_ds = pd.concat([dim_ds, new_ds_row], ignore_index=True)
    dim_ds.to_csv(ds_path, index=False)

    # --- B. Mise à jour viz_facts_clean (La table plate du dashboard) ---
    viz_path = GOLD_DIR / "viz_facts_clean.csv"
    if viz_path.exists():
        # Lecture par morceaux pour économiser la RAM si le fichier est gros
        viz = pd.read_csv(viz_path, low_memory=False)
        # Supprimer les anciennes observations de ce dataset
        viz = viz[viz['index_id'].astype(str) != str(dataset_id)]
        
        # Préparation des colonnes viz pour le nouveau
        df_new["date_time_str"] = df_new["date_time_full"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df_new["annee"] = df_new["date_time_full"].dt.year
        df_new["effort_length_km"] = effort_km
        
        # Concaténation
        viz = pd.concat([viz, df_new], ignore_index=True)
        viz.to_csv(viz_path, index=False)
        log.info(f"Gold Data mise à jour : {len(df_new)} nouvelles observations ajoutées.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_id", required=True)
    args = parser.parse_args()
    run_spatial_etl(args.dataset_id)
