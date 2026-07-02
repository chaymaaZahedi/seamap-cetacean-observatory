"""
data_loader.py — Dashboard SEAMAP Cétacés v6
============================================
Adaptateur pour faire fonctionner le dashboard v4 avec les données v6.
"""

from __future__ import annotations

import os
import glob
import warnings
import logging
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# CHEMINS DE BASE
# ─────────────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
_GOLD_LOCAL = _HERE / "gold_data"
GOLD = _GOLD_LOCAL

_DATA_LOCAL = _HERE / "data_source"
_DATA_REMOTE = Path("C:/MyPc/master/s4/stage-ird/dataset/baleine-seamap/data_source")

def get_data_path(dataset_id, file_type="points"):
    """ Retourne le chemin du fichier (Local en priorité, sinon Remote) """
    sub = "data_sources_point" if file_type == "points" else "data_sources_survey_tracks"
    ext = ".csv" if file_type == "points" else ".gdb"
    fname = f"obis_seamap_dataset_{dataset_id}_points{ext}" if file_type == "points" else f"obis_seamap_dataset_{dataset_id}{ext}"
    
    local_path = _DATA_LOCAL / sub / fname
    if local_path.exists():
        return local_path
    return _DATA_REMOTE / sub / fname

INDEX_CSV = _HERE / "index.csv"

def _gold(fname: str) -> str:
    return str(GOLD / fname)

def _sanitize_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)
        elif df[col].dtype == object:
            sample = df[col].dropna().head(5)
            if not sample.empty and hasattr(sample.iloc[0], "strftime"):
                df[col] = df[col].astype(str)
    return df

@st.cache_data(show_spinner="📂 Chargement des dimensions...")
def load_dimensions():
    # Only dim_dataset is truly needed by main.py
    dim_dataset = pd.read_csv(_gold("dim_dataset.csv"))
    dim_dataset["id_dataset_int"] = dim_dataset["index_id"]
    if "source_provider" not in dim_dataset.columns:
        dim_dataset["source_provider"] = "Inconnu" # To prevent key errors if missing
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), dim_dataset

@st.cache_data(show_spinner="🔭 Chargement des observations...")
def _load_clean_facts():
    df = pd.read_csv(_gold("viz_facts_clean.csv"), low_memory=False)
    df["group_size"] = pd.to_numeric(df["abondance"], errors="coerce").fillna(1)
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    df["nom_espece"] = df["scientific_name"].fillna("Inconnu")
    kpis = {
        "total_obs": len(df),
        "total_animaux": int(df["group_size"].sum()),
        "nb_especes": df["nom_espece"].nunique(),
        "nb_datasets": df["index_id"].nunique(),
    }
    return df, kpis

@st.cache_data(show_spinner="🔗 Construction de l'agrégat...")
def build_joined_agg():
    df = pd.read_csv(_gold("viz_facts_clean.csv"), low_memory=False)
    
    df["group_size"] = pd.to_numeric(df["abondance"], errors="coerce").fillna(1)
    df["count"] = 1
    df["id_dataset_int"] = df["index_id"]
    df["nom_espece"] = df["scientific_name"].fillna("Inconnu")
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    
    df["date_time_full"] = pd.to_datetime(df["date_time_str"], errors="coerce")
    df["trimestre"] = df["date_time_full"].dt.quarter.fillna(1).astype(int)
    
    if "source_provider" not in df.columns:
        df["source_provider"] = df["provider"]

    GROUP_BY_KEYS = ["source_region", "nom_espece", "id_dataset_int",
                     "annee", "trimestre", "source_platform", "source_type", "source_provider"]
    
    joined = (
        df.groupby(GROUP_BY_KEYS, as_index=False, dropna=False)
          .agg(count=("count", "sum"),
               sum_group_size=("group_size", "sum"),
               nb_jours=("dataset_jour", pd.Series.nunique))
    )
    
    geo_df = df[["latitude", "longitude", "group_size", "source_region", "nom_espece"]].copy()
                 
    kpis = {
        "total_count": len(df),
        "total_group_size": int(df["group_size"].sum()),
    }
    
    return joined, geo_df, kpis, {}

@st.cache_data(show_spinner="📊 Chargement CPUE datasets...")
def load_cpue():
    df = pd.read_csv(_gold("viz_facts_clean.csv"), low_memory=False)
    df["group_size"] = pd.to_numeric(df["abondance"], errors="coerce").fillna(1)
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    
    cpue = (
        df.groupby("index_id", as_index=False)
          .agg(nb_animaux=("group_size", "sum"),
               nb_sightings=("group_size", "count"),
               annee_debut=("annee", "min"),
               annee_fin=("annee", "max"),
               L_km=("effort_length_km", "first"),
               region=("source_region", "first"))
    )
    cpue["id_dataset_int"] = cpue["index_id"]
    cpue["dataset_id"] = cpue["index_id"]
    cpue["L_km"] = pd.to_numeric(cpue["L_km"], errors="coerce")
    cpue["cpue"] = np.where(cpue["L_km"] > 0, cpue["nb_animaux"] / cpue["L_km"], np.nan)
    return cpue

@st.cache_data(show_spinner=False)
def get_estimated_distances():
    df = pd.read_csv(_gold("viz_facts_clean.csv"), low_memory=False)
    df = df.sort_values(['index_id', 'date_time_str'])
    df['lat_prev'] = df.groupby('index_id')['latitude'].shift(1)
    df['lon_prev'] = df.groupby('index_id')['longitude'].shift(1)
    
    def haversine(lat1, lon1, lat2, lon2):
        import numpy as np
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c
        
    df['dist_km'] = haversine(df['lat_prev'], df['lon_prev'], df['latitude'], df['longitude'])
    res = df.groupby('index_id')['dist_km'].sum().reset_index()
    res["id_dataset_int"] = res["index_id"]
    return res

# ═════════════════════════════════════════════════════════════════════════════
# PARTIE 2 — FONCTIONS SPATIALES (nouvelles)
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="📋 Chargement de l'index...")
def load_index() -> pd.DataFrame:
    """
    Charge index.csv et retourne un DataFrame propre.
    Colonnes utiles : ID, Title, Provider, Data type, Platform,
                      Records, Effort, Region.
    """
    df = pd.read_csv(INDEX_CSV, dtype={"ID": str})
    # Nettoyage : supprimer les espaces dans les noms de colonnes
    df.columns = df.columns.str.strip()
    # Convertir ID en numérique (certains IDs sont des entiers longs)
    df["ID_num"] = pd.to_numeric(df["ID"], errors="coerce")
    # Filtrer les lignes sans fichier points disponible
    df["has_points"] = df["ID"].apply(
        lambda ds_id: get_data_path(ds_id, "points").exists()
    )
    return df


@st.cache_data(show_spinner="📍 Chargement des points...")
def load_dataset_points(dataset_id: int | str) -> pd.DataFrame:
    """
    Charge le fichier de points pour un dataset_id donné.
    - Toutes les colonnes datetime/Timestamp sont converties en str.
    - Retourne un DataFrame vide si le fichier n'existe pas.
    """
    fpath = get_data_path(dataset_id, "points")
    if not fpath.exists():
        return pd.DataFrame()

    df = pd.read_csv(fpath, low_memory=False)

    # Conversion forcée des colonnes temporelles → str
    datetime_cols = ["date_time", "last_mod"]
    for col in datetime_cols:
        if col in df.columns:
            # Parser puis re-stringifier pour normaliser le format
            parsed = pd.to_datetime(df[col], errors="coerce")
            df[col] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").where(parsed.notna(), "")

    # Conversion de toutes colonnes Timestamp restantes
    df = _sanitize_datetimes(df)
    return df


def find_survey_track(dataset_id: int | str) -> Optional[str]:
    """
    Cherche un dossier .gdb pour le dataset_id (Local ou Remote).
    """
    gdb_path = get_data_path(dataset_id, "gdb")
    if gdb_path.exists() and gdb_path.is_dir():
        return str(gdb_path)
    return None


@st.cache_data(show_spinner="🛤️ Chargement des trajectoires...")
def load_track_lines(gdb_path: str):
    """
    Charge la couche de lignes depuis un .gdb.
    Moteur : pyogrio (prioritaire), fallback fiona.
    - Toutes les colonnes Timestamp sont converties en str (compatibilité Folium/JSON).
    Retourne un GeoDataFrame en EPSG:4326 ou None en cas d'erreur.
    """
    try:
        import geopandas as gpd
    except ImportError:
        st.warning("geopandas n'est pas installé.")
        return None

    def _clean_gdf(gdf):
        """Convertit les colonnes datetime du GeoDataFrame en str."""
        import pandas as pd
        for col in gdf.columns:
            if col == "geometry":
                continue
            if pd.api.types.is_datetime64_any_dtype(gdf[col]):
                gdf[col] = gdf[col].astype(str)
            elif gdf[col].dtype == object:
                sample = gdf[col].dropna().head(3)
                if not sample.empty and hasattr(sample.iloc[0], "strftime"):
                    gdf[col] = gdf[col].astype(str)
        return gdf

    def _ensure_4326(gdf):
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        return gdf

    # Détermination du nom de la couche
    dataset_id = Path(gdb_path).stem.replace("obis_seamap_dataset_", "")
    layer_name = f"obis_seamap_dataset_{dataset_id}_lines"

    # Essai des moteurs disponibles
    for engine in ("pyogrio", "fiona"):
        try:
            gdf = gpd.read_file(gdb_path, layer=layer_name, engine=engine)
            gdf = _ensure_4326(gdf)
            gdf = _clean_gdf(gdf)
            return gdf
        except Exception as e:
            logging.debug(f"Engine {engine} failed for {gdb_path}: {e}")
            continue

    # Fallback : essai sans spécifier la couche
    for engine in ("pyogrio", "fiona"):
        try:
            gdf = gpd.read_file(gdb_path, engine=engine)
            if gdf.geom_type.isin(["LineString", "MultiLineString"]).any():
                gdf = _ensure_4326(gdf)
                gdf = _clean_gdf(gdf)
                return gdf
        except Exception:
            continue

    return None



def compute_study_zone(
    pts_df: pd.DataFrame,
    gdb_path: Optional[str],
    buffer_m: int = 500,
) -> Tuple[object, str, float]:
    """
    Calcule la zone d'étude selon la disponibilité du survey track.

    Cas 1 — Track disponible :
        Buffer de `buffer_m` mètres autour des lignes en EPSG:3035.

    Cas 2 — Points seulement :
        Enveloppe convexe (Convex Hull) des points d'observation.

    Retourne :
        (zone_gdf, confidence, area_km2)
        - zone_gdf   : GeoDataFrame en EPSG:4326 (ou None si impossible)
        - confidence : "Haute" | "Modérée"
        - area_km2   : superficie estimée en km²
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        return None, "Inconnue", 0.0

    # ── Cas 1 : Survey track présent ──────────────────────────────────────
    if gdb_path is not None:
        track_gdf = load_track_lines(gdb_path)
        if track_gdf is not None and not track_gdf.empty:
            # Projection métrique LAEA Europe pour buffer précis
            track_metr = track_gdf.to_crs("EPSG:3035")
            buffered   = track_metr.buffer(buffer_m)
            union_buf  = buffered.union_all() if hasattr(buffered, "union_all") \
                         else buffered.unary_union
            area_m2    = union_buf.area
            area_km2   = area_m2 / 1_000_000

            # Reprojection 4326 pour affichage
            zone_gdf = gpd.GeoDataFrame(geometry=[union_buf], crs="EPSG:3035")
            zone_gdf = zone_gdf.to_crs("EPSG:4326")
            return zone_gdf, "Haute", round(area_km2, 2)

    # ── Cas 2 : Convex Hull des points ────────────────────────────────────
    pts_clean = pts_df.dropna(subset=["latitude", "longitude"])
    if len(pts_clean) < 3:
        # Pas assez de points pour un hull → cercle autour du centroïde
        if len(pts_clean) == 0:
            return None, "Modérée", 0.0

        center_lat = pts_clean["latitude"].mean()
        center_lon = pts_clean["longitude"].mean()
        center_pt  = gpd.GeoDataFrame(
            geometry=[Point(center_lon, center_lat)], crs="EPSG:4326"
        )
        center_metr = center_pt.to_crs("EPSG:3035")
        buf_geom    = center_metr.buffer(10_000)  # 10 km autour du point unique
        area_km2    = buf_geom.area.sum() / 1_000_000
        zone_gdf    = gpd.GeoDataFrame(geometry=buf_geom, crs="EPSG:3035").to_crs("EPSG:4326")
        return zone_gdf, "Modérée", round(area_km2, 2)

    # Hull normal
    import geopandas as gpd
    from shapely.geometry import MultiPoint

    points_geom = [Point(row["longitude"], row["latitude"])
                   for _, row in pts_clean.iterrows()]
    hull        = MultiPoint(points_geom).convex_hull
    hull_gdf    = gpd.GeoDataFrame(geometry=[hull], crs="EPSG:4326")

    # Calcul de superficie en projection métrique
    hull_metr   = hull_gdf.to_crs("EPSG:3035")
    area_km2    = hull_metr.geometry.area.sum() / 1_000_000

    return hull_gdf, "Modérée", round(area_km2, 2)


def compute_density_indicator(pts_df: pd.DataFrame, area_km2: float) -> float:
    """
    Calcule la densité : nombre total d'individus / km² de la zone d'étude.
    Retourne 0.0 si area_km2 == 0 ou si la colonne group_size est absente.
    """
    if area_km2 <= 0 or "group_size" not in pts_df.columns:
        return 0.0
    total_individus = pd.to_numeric(pts_df["group_size"], errors="coerce").sum()
    return round(float(total_individus) / area_km2, 4)


def parse_bounds(bounds_str) -> Tuple[Optional[float], Optional[float]]:
    """ Parse les coordonnées sous forme de chaîne de caractères (ex: '40.11 - 48.30') """
    if not isinstance(bounds_str, str) or pd.isna(bounds_str) or bounds_str.strip() == "":
        return None, None
    parts = bounds_str.split(" - ")
    if len(parts) == 2:
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            pass
    try:
        val = float(bounds_str.strip())
        return val, val
    except ValueError:
        pass
    return None, None


def map_to_standard_region(name: str) -> Optional[str]:
    """ Associe un nom brut retourné par l'API à une région normalisée du dashboard """
    n = name.lower()
    if "north atlantic" in n:
        return "North Atlantic Ocean"
    elif "south atlantic" in n:
        return "South Atlantic Ocean"
    elif "atlantic" in n:
        return "Atlantic Ocean"
    elif "north pacific" in n:
        return "North Pacific Ocean"
    elif "south pacific" in n:
        return "South Pacific Ocean"
    elif "pacific" in n:
        return "North Pacific Ocean"
    elif "indian" in n:
        return "Indian Ocean"
    elif "southern ocean" in n or "antarctic" in n:
        return "Southern Ocean"
    elif "arctic" in n:
        return "Arctic Ocean"
    elif "mediterranean" in n:
        return "Mediterranean Sea"
    elif "black sea" in n:
        return "Black Sea"
    elif "north sea" in n:
        return "North Sea"
    elif "norwegian sea" in n:
        return "Norwegian Sea"
    elif "baltic" in n:
        return "Baltic Sea"
    elif "caribbean" in n:
        return "Caribbean Sea"
    elif "arabian sea" in n:
        return "Arabian Sea"
    elif "persian gulf" in n:
        return "Persian Gulf"
    elif "gulf of mexico" in n:
        return "Gulf of Mexico"
    elif "english channel" in n:
        return "English Channel"
    elif "philippine sea" in n:
        return "Philippine Sea"
    return None


def get_region_from_api(lat: float, lon: float) -> Optional[str]:
    """ Interroge l'API Marine Regions pour déterminer la région marine """
    import requests
    url = f"https://www.marineregions.org/rest/getGazetteerRecordsByLatLong.json/{lat}/{lon}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            records = response.json()
            # 1er passage : filtrer sur les placeType mer/océan/golfe
            for r in records:
                place_type = str(r.get('placeType', '')).lower()
                name = str(r.get('preferredGazetteerName', '')).strip()
                if 'ocean' in place_type or 'sea' in place_type or 'gulf' in place_type:
                    mapped = map_to_standard_region(name)
                    if mapped:
                        return mapped
            # 2e passage : mapping direct du nom
            for r in records:
                name = str(r.get('preferredGazetteerName', '')).strip()
                mapped = map_to_standard_region(name)
                if mapped:
                    return mapped
    except Exception as e:
        logging.warning(f"Erreur API Marine Regions pour lat={lat}, lon={lon} : {e}")
    return None


def get_region_from_bbox(lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> str:
    """ Méthode de repli (Bounding Box) si l'API échoue """
    try:
        lat = (lat_min + lat_max) / 2.0
        lon = (lon_min + lon_max) / 2.0
    except:
        return "Atlantic Ocean"

    if lat > 65:
        return "Arctic Ocean"
    elif lat < -60:
        return "Southern Ocean"

    if -80 <= lon <= -20:
        return "North Atlantic Ocean" if lat >= 0 else "South Atlantic Ocean"
    elif -100 <= lon < -80:
        if 10 <= lat <= 30:
            return "Gulf of Mexico"
        return "North Atlantic Ocean" if lat >= 0 else "South Atlantic Ocean"
    elif -20 <= lon <= 20:
        if 30 <= lat <= 48 and -6 <= lon <= 36:
            return "Mediterranean Sea"
        return "North Atlantic Ocean" if lat >= 0 else "South Atlantic Ocean"
    elif 20 < lon <= 120:
        if lat < 0:
            return "South Indian Ocean"
        else:
            if 10 <= lat <= 25 and 45 <= lon <= 60:
                return "Arabian Sea"
            return "Indian Ocean"
    elif (120 < lon <= 180) or (-180 <= lon < -100):
        return "North Pacific Ocean" if lat >= 0 else "South Pacific Ocean"

    return "Atlantic Ocean"


def suggest_region_for_dataset(dataset_id: str) -> Tuple[str, str]:
    """ Suggère la région du dataset et retourne (région, source) """
    df = load_index()
    row = df[df['ID'].astype(str).str.strip() == str(dataset_id).strip()]
    if row.empty:
        return "Atlantic Ocean", "Default (Dataset non trouvé dans l'index)"

    lat_str = row.iloc[0].get('Latitude', '')
    lon_str = row.iloc[0].get('Longitude', '')

    lat_min, lat_max = parse_bounds(lat_str)
    lon_min, lon_max = parse_bounds(lon_str)

    if lat_min is None or lon_min is None:
        return "Atlantic Ocean", "Default (Coordonnées manquantes)"

    lat_center = (lat_min + lat_max) / 2.0
    lon_center = (lon_min + lon_max) / 2.0

    # 1. API Marine Regions
    region_api = get_region_from_api(lat_center, lon_center)
    if region_api:
        return region_api, "API Marine Regions"

    # 2. Fallback Bounding Box
    region_bbox = get_region_from_bbox(lat_min, lat_max, lon_min, lon_max)
    return region_bbox, "Calcul par boîte géographique (fallback)"
