"""
ETL_v6.py — Pipeline SEAMAP v6 Finale
=============================================================
Fusion des traitements v4 (spatial/ptobs) et v5 (temporel/ptphoto).

Donnees sources :
    - Points : C:/MyPc/master/s4/stage-ird/dataset/baleine-seamap/data_source/data_sources_point
    - Tracks : C:/MyPc/master/s4/stage-ird/dataset/baleine-seamap/data_source/data_sources_survey_tracks

Sorties dans gold_data/ :
    - Modele en etoile complet
    - viz_facts_clean.csv (pret pour le dashboard)
"""

import os
import sys
import logging
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
INDEX_CSV  = HERE / "index.csv"
OUTPUT_DIR = HERE / "gold_data"

DATA_ROOT  = Path("c:/MyPc/master/s4/stage-ird/dataset/baleine-seamap/data_source")
POINTS_DIR = DATA_ROOT / "data_sources_point"
TRACKS_DIR = DATA_ROOT / "data_sources_survey_tracks"

BUFFER_M   = 500

GENERIC_NAMES = {"(no name)", "(unknown)", "unknown", "nan", "", "none"}

TARGET_COLS = [
    "dataset_id", "row_id", "latitude", "longitude",
    "scientific_name", "common_name", "itis_tsn",
    "date_time", "timezone", "organism_name", "individual_count", "group_size",
    "provider", "platform", "ds_type", "type"
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(HERE / "etl_v6_run.log", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

def _save(df: pd.DataFrame, name: str) -> None:
    path = OUTPUT_DIR / name
    df.to_csv(path, index=False, encoding="utf-8")
    log.info(f"    -> {name:<35} {len(df):>6,} lignes  {path.stat().st_size/1024:>8.1f} KB")

# ═════════════════════════════════════════════════════════════════════════════
def parse_individual_count(val):
    if pd.isna(val) or str(val).strip() == "":
        return np.nan
    s = str(val).strip()
    if "-" in s:
        parts = s.split("-")
        try:
            p1 = float(parts[0].strip())
            p2 = float(parts[1].strip())
            return (p1 + p2) / 2.0
        except ValueError:
            pass
    try:
        return float(s)
    except ValueError:
        return np.nan

# ═════════════════════════════════════════════════════════════════════════════
def phase1_load_index() -> pd.DataFrame:
    log.info("=" * 65)
    log.info("PHASE 1 — Lecture de index.csv")
    log.info("=" * 65)

    if not INDEX_CSV.exists():
        log.error(f"index.csv introuvable : {INDEX_CSV}")
        sys.exit(1)

    idx = pd.read_csv(INDEX_CSV, dtype=str)
    idx.columns = idx.columns.str.strip()

    idx["csv_path"] = idx["Dataset"].apply(
        lambda fn: POINTS_DIR / str(fn).strip()
        if isinstance(fn, str) and fn.strip().endswith(".csv") else None
    )
    idx["csv_exists"] = idx["csv_path"].apply(
        lambda p: p is not None and p.exists()
    )

    idx["gdb_path"] = idx["ID"].apply(
        lambda did: TRACKS_DIR / f"obis_seamap_dataset_{str(did).strip()}.gdb"
    )
    idx["gdb_exists"] = idx["gdb_path"].apply(lambda p: p.exists())

    ok = idx[idx["csv_exists"]]
    log.info(f"  Total dans index : {len(idx)}")
    log.info(f"  Fichiers bruts trouves : {len(ok)}")
    return ok.reset_index(drop=True)

# ═════════════════════════════════════════════════════════════════════════════
def phase2_extract_points(idx: pd.DataFrame) -> pd.DataFrame:
    log.info("=" * 65)
    log.info("PHASE 2 — Extraction des fichiers de points")
    log.info("=" * 65)

    chunks, ok_n, err_n = [], 0, 0

    for _, row in idx.iterrows():
        fp  = row["csv_path"]
        did = str(row["ID"]).strip()
        fn  = fp.name

        try:
            header = pd.read_csv(fp, nrows=0).columns.str.strip().str.lower().tolist()
            cols   = [c for c in TARGET_COLS if c in header]

            df = pd.read_csv(fp, usecols=cols, low_memory=False,
                             encoding="utf-8", encoding_errors="replace")
            df.columns = df.columns.str.strip().str.lower()

            for c in TARGET_COLS:
                if c not in df.columns:
                    df[c] = np.nan

            df["source_file"]     = fn
            df["source_region"]   = str(row.get("Region", "")).strip()
            df["source_provider"] = str(row.get("Provider", "")).strip()
            df["source_platform"] = str(row.get("Platform", "")).strip()
            
            ds_type = str(row.get("Data type", "")).strip().lower()
            df["source_type"] = ds_type
            
            if ds_type == "ptphoto":
                df["traitement_type"] = "v5_temporel"
            elif ds_type == "ptobs":
                df["traitement_type"] = "v4_spatial"
            else:
                df["traitement_type"] = "autre"
                
            df["has_track"] = row["gdb_exists"]
            df["index_id"]  = did

            chunks.append(df)
            ok_n += 1

        except Exception as exc:
            err_n += 1
            log.error(f"  [ERR] {fn}: {exc}")

    log.info(f"  Extraction : {ok_n} OK, {err_n} erreurs")
    return pd.concat(chunks, ignore_index=True)

# ═════════════════════════════════════════════════════════════════════════════
def phase3_extract_tracks(idx: pd.DataFrame) -> pd.DataFrame:
    log.info("=" * 65)
    log.info("PHASE 3 — Extraction des survey tracks (GDB)")
    log.info("=" * 65)

    try:
        import geopandas as gpd
    except ImportError:
        log.warning("geopandas non installe. L'effort spatial track ne sera pas calcule. Installez: pip install geopandas pyogrio")
        return pd.DataFrame(columns=["index_id", "has_track", "effort_length_km", "effort_area_km2", "nb_segments"])

    tracks_idx = idx[idx["gdb_exists"]].copy()
    effort_rows = []

    for _, row in tracks_idx.iterrows():
        gdb_path = row["gdb_path"]
        did      = str(row["ID"]).strip()
        layer    = f"obis_seamap_dataset_{did}_lines"

        gdf_lines = None
        for engine in ("pyogrio", "fiona"):
            try:
                gdf_lines = gpd.read_file(str(gdb_path), layer=layer, engine=engine)
                break
            except Exception:
                continue

        if gdf_lines is None or gdf_lines.empty:
            effort_rows.append({
                "index_id"       : did,
                "has_track"        : True,
                "effort_length_km" : np.nan,
                "effort_area_km2"  : np.nan,
                "nb_segments"      : 0,
            })
            continue

        if gdf_lines.crs is None:
            gdf_lines = gdf_lines.set_crs("EPSG:4326")
        elif gdf_lines.crs.to_epsg() != 4326:
            gdf_lines = gdf_lines.to_crs("EPSG:4326")

        if "length_km" in gdf_lines.columns:
            length_km = pd.to_numeric(gdf_lines["length_km"], errors="coerce").sum()
        else:
            gdf_m = gdf_lines.to_crs("EPSG:3035")
            length_km = gdf_m.geometry.length.sum() / 1000

        gdf_metr  = gdf_lines.to_crs("EPSG:3035")
        buffered  = gdf_metr.buffer(BUFFER_M)
        union_buf = buffered.union_all() if hasattr(buffered, "union_all") else buffered.unary_union
        area_km2  = union_buf.area / 1_000_000

        effort_rows.append({
            "index_id"       : did,
            "has_track"        : True,
            "effort_length_km" : round(length_km, 3),
            "effort_area_km2"  : round(area_km2, 3),
            "nb_segments"      : len(gdf_lines),
        })

    no_track_ids = idx[~idx["gdb_exists"]]["ID"].apply(lambda x: str(x).strip()).tolist()
    for did in no_track_ids:
        effort_rows.append({
            "index_id"       : did,
            "has_track"        : False,
            "effort_length_km" : np.nan,
            "effort_area_km2"  : np.nan,
            "nb_segments"      : 0,
        })

    return pd.DataFrame(effort_rows)

# ═════════════════════════════════════════════════════════════════════════════
def phase4_transform(full: pd.DataFrame) -> pd.DataFrame:
    log.info("=" * 65)
    log.info("PHASE 4 — Nettoyage et Deduplication selon Traitement")
    log.info("=" * 65)

    full["date_time_full"] = pd.to_datetime(full["date_time"], errors="coerce")
    full = full.dropna(subset=["date_time_full"])
    
    full["annee"] = full["date_time_full"].dt.year.astype(int)
    full["mois"] = full["date_time_full"].dt.month.astype(int)
    full["date_time_str"] = full["date_time_full"].dt.strftime("%Y-%m-%d %H:%M:%S")
    full["date_jour"] = full["date_time_str"].str[:10]
    full["dataset_jour"] = full["source_file"].astype(str) + "_" + full["date_jour"]

    full = full.sort_values(by="date_time_full").reset_index(drop=True)

    # Separation selon le traitement
    df_v5 = full[full["traitement_type"] == "v5_temporel"].copy()
    df_v4 = full[full["traitement_type"] == "v4_spatial"].copy()
    df_autre = full[full["traitement_type"] == "autre"].copy()
    
    log.info(f"  Observations ptphoto (v5) : {len(df_v5):,}")
    log.info(f"  Observations ptobs (v4)   : {len(df_v4):,}")

    # ==========================
    # LOGIQUE V5 (ptphoto)
    # ==========================
    if not df_v5.empty:
        # Fallback group_size
        df_v5["individual_count"] = df_v5["individual_count"].apply(parse_individual_count)
        df_v5["individual_count"] = df_v5["individual_count"].fillna(pd.to_numeric(df_v5["group_size"], errors="coerce"))
        df_v5["individual_count"] = df_v5["individual_count"].fillna(1).astype(int)
        
        df_v5["organism_name"] = df_v5["organism_name"].astype(str).str.strip()
        is_generic = df_v5["organism_name"].str.lower().isin(GENERIC_NAMES)
        
        df_generic = df_v5[is_generic].copy()
        df_named = df_v5[~is_generic].copy()
        
        n_named_before = len(df_named)
        df_named = df_named.drop_duplicates(subset=["organism_name", "annee"], keep="first")
        n_named_after = len(df_named)
        
        log.info(f"  V5 : Doublons annuels supprimes : {n_named_before - n_named_after:,}")
        df_v5_clean = pd.concat([df_named, df_generic], ignore_index=True)
        df_v5_clean["abondance"] = df_v5_clean["individual_count"]
    else:
        df_v5_clean = pd.DataFrame()

    # ==========================
    # LOGIQUE V4 (ptobs)
    # ==========================
    if not df_v4.empty:
        df_v4["group_size"] = pd.to_numeric(df_v4["group_size"], errors="coerce").fillna(1).astype(int)
        df_v4["abondance"] = df_v4["group_size"]
        # Pas de deduplication pour v4
        df_v4_clean = df_v4.copy()
    else:
        df_v4_clean = pd.DataFrame()
        
    # Autres
    if not df_autre.empty:
        df_autre["abondance"] = 1
        df_autre_clean = df_autre.copy()
    else:
        df_autre_clean = pd.DataFrame()

    full_clean = pd.concat([df_v5_clean, df_v4_clean, df_autre_clean], ignore_index=True)
    full_clean = full_clean.sort_values(by="date_time_full").reset_index(drop=True)
    
    # --- FILTRAGE DES VALEURS ABERRANTES ---
    whales = {
        'megaptera novaeangliae', 'balaenoptera physalus', 'balaenoptera musculus',
        'balaenoptera acutorostrata', 'balaenoptera bonaerensis', 'balaenoptera borealis',
        'balaenoptera edeni', 'physeter macrocephalus', 'eubalaena glacialis',
        'eubalaena australis', 'eubalaena japonica', 'balaena mysticetus',
        'eschrichtius robustus'
    }
    
    anomalies_rows = []
    clean_indices = []
    
    for idx, row in full_clean.iterrows():
        val = row["abondance"]
        is_anom = False
        reason = ""
        
        if pd.notna(val):
            # Valeur négative
            if val < 0:
                is_anom = True
                reason = f"Valeur negative ({val})"
            # Placeholder 9999
            elif val == 9999:
                is_anom = True
                reason = "Code placeholder 9999"
            # Seuils biologiques
            else:
                sp = str(row.get("scientific_name", "")).strip().lower()
                if any(w in sp for w in whales) and val >= 50:
                    is_anom = True
                    reason = f"Effectif irrealiste pour grand cetace (group_size/count = {val} >= 50)"
                elif "ursus" in sp and val > 10:
                    is_anom = True
                    reason = f"Effectif irrealiste pour ours polaire (group_size/count = {val} > 10)"
                elif val >= 3000:
                    is_anom = True
                    reason = f"Effectif extremement eleve (group_size/count = {val} >= 3000)"
                    
        if is_anom:
            anomalies_rows.append({
                "Dataset ID": row.get("index_id", "N/A"),
                "File": row.get("source_file", "N/A"),
                "Date Time": row.get("date_time_str", "N/A"),
                "Scientific Name": row.get("scientific_name", "N/A"),
                "Common Name": row.get("common_name", "N/A"),
                "Value": val,
                "Reason": reason
            })
        else:
            clean_indices.append(idx)
            
    # Sauvegarde des anomalies supprimées dans un fichier texte
    deleted_file = HERE / "deleted_anomalies.txt"
    with open(deleted_file, "w", encoding="utf-8") as f:
        f.write("================================================================================\n")
        f.write("                     RAPPORT DES VALEURS ABERRANTES SUPPRIMEES                  \n")
        f.write("================================================================================\n")
        f.write(f"Nombre total de valeurs aberrantes supprimees : {len(anomalies_rows)}\n\n")
        
        for idx_a, a in enumerate(anomalies_rows, 1):
            f.write(f"Suppression #{idx_a}\n")
            f.write(f"--------------------------------------------------------------------------------\n")
            f.write(f"  Dataset ID      : {a['Dataset ID']}\n")
            f.write(f"  File            : {a['File']}\n")
            f.write(f"  Date Time       : {a['Date Time']}\n")
            f.write(f"  Scientific Name : {a['Scientific Name']}\n")
            f.write(f"  Common Name     : {a['Common Name']}\n")
            f.write(f"  Value           : {a['Value']}\n")
            f.write(f"  Reason/Type     : {a['Reason']}\n")
            f.write("\n")
            
    log.info(f"  Valeurs aberrantes detectees et supprimees : {len(anomalies_rows)}")
    log.info(f"  Rapport des suppressions enregistre dans : {deleted_file.name}")
    
    # Conserver uniquement les lignes propres
    full_clean = full_clean.iloc[clean_indices].reset_index(drop=True)
    
    full_clean["latitude"] = pd.to_numeric(full_clean["latitude"], errors="coerce")
    full_clean["longitude"] = pd.to_numeric(full_clean["longitude"], errors="coerce")
    full_clean["row_id_clean"] = range(1, len(full_clean) + 1)
    
    log.info(f"  Total apres traitement mixte et filtrage : {len(full_clean):,} observations")
    return full_clean

# ═════════════════════════════════════════════════════════════════════════════
def phase5_export(full: pd.DataFrame, dim_effort: pd.DataFrame):
    log.info("=" * 65)
    log.info("PHASE 5 — Schema en etoile et Export")
    log.info("=" * 65)
    
    # Dimensions simplifiees
    dim_species = full[["organism_name", "scientific_name", "common_name"]].drop_duplicates().reset_index(drop=True)
    dim_species["species_id"] = dim_species.index + 1

    dim_dataset = full[["index_id", "source_file", "source_type", "traitement_type"]].drop_duplicates().reset_index(drop=True)
    dim_dataset["dim_dataset_id"] = dim_dataset.index + 1

    # Jointure avec dim_effort
    dim_dataset = dim_dataset.merge(dim_effort, on="index_id", how="left")

    dim_provider = full[["provider", "source_provider"]].drop_duplicates().reset_index(drop=True)
    dim_provider["provider_id"] = dim_provider.index + 1

    dim_platform = full[["platform", "source_platform"]].drop_duplicates().reset_index(drop=True)
    dim_platform["platform_id"] = dim_platform.index + 1

    dim_time = full[["date_jour", "annee", "mois"]].drop_duplicates().reset_index(drop=True)
    dim_time["time_id"] = dim_time.index + 1
    
    # Table de faits
    facts = full.merge(dim_species, on=["organism_name", "scientific_name", "common_name"], how="left")
    facts = facts.merge(dim_dataset, on=["index_id", "source_file", "source_type", "traitement_type"], how="left")
    facts = facts.merge(dim_provider, on=["provider", "source_provider"], how="left")
    facts = facts.merge(dim_platform, on=["platform", "source_platform"], how="left")
    facts = facts.merge(dim_time, on=["date_jour", "annee", "mois"], how="left")
    
    fact_cols = [
        "row_id_clean", "dim_dataset_id", "species_id", "provider_id", "platform_id", "time_id",
        "latitude", "longitude", "abondance", "traitement_type"
    ]
    facts_star = facts[fact_cols].copy()
    
    _save(dim_species, "dim_species.csv")
    _save(dim_dataset, "dim_dataset.csv")
    _save(dim_provider, "dim_provider.csv")
    _save(dim_platform, "dim_platform.csv")
    _save(dim_time, "dim_time.csv")
    _save(facts_star, "facts_observations.csv")

    # Flat viz
    viz_cols = [
        "row_id_clean", "index_id", "source_file",
        "date_time_str", "date_jour", "dataset_jour", "annee", "mois",
        "latitude", "longitude", 
        "scientific_name", "common_name", "organism_name", 
        "abondance", "provider", "platform", "source_platform", "source_provider",
        "source_type", "source_region", "traitement_type", "has_track"
    ]
    viz = full[[c for c in viz_cols if c in full.columns]].copy()
    
    # Merge effort km pour la viz (CPUE)
    viz = viz.merge(dim_dataset[["index_id", "effort_length_km"]], on="index_id", how="left")
    
    _save(viz, "viz_facts_clean.csv")

# ═════════════════════════════════════════════════════════════════════════════
def run_etl():
    idx = phase1_load_index()
    full = phase2_extract_points(idx)
    dim_effort = phase3_extract_tracks(idx)
    full = phase4_transform(full)
    phase5_export(full, dim_effort)
    log.info("\n[SUCCES] ETL v6 termine.")

if __name__ == "__main__":
    run_etl()
