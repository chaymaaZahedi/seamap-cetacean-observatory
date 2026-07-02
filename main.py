"""
main.py — Dashboard SEAMAP Cétacés
Lancez avec : streamlit run main.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

from data_loader import (
    load_dimensions, build_joined_agg, load_cpue,
    load_index, load_dataset_points, find_survey_track,
    compute_study_zone, compute_density_indicator, get_estimated_distances
)

try:
    import folium
    from streamlit_folium import st_folium
    _FOLIUM_OK = True
except ImportError:
    _FOLIUM_OK = False

try:
    import geopandas as gpd
    _GPD_OK = True
except ImportError:
    _GPD_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEAMAP · Observatoire des Cétacés",
    page_icon="🐋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main .block-container { padding-top: 1rem; padding-bottom: 2rem; }

.kpi-card {
    background: linear-gradient(135deg, #061528 0%, #0a2240 100%);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
}
.kpi-card:hover { transform: translateY(-3px); border-color: rgba(0,212,255,0.5); }
.kpi-card::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 100px; height: 100px;
    background: radial-gradient(circle, rgba(0,212,255,0.13) 0%, transparent 70%);
    border-radius: 50%;
}
.kpi-icon  { font-size: 2rem; margin-bottom: 0.2rem; }
.kpi-value { font-size: 2.2rem; font-weight: 800; color: #00D4FF; letter-spacing: -1px; }
.kpi-label { font-size: 0.82rem; color: #8ABDD4; text-transform: uppercase; letter-spacing: 1px; margin-top: 0.3rem; }

.section-title {
    font-size: 1.25rem; font-weight: 700; color: #E8F4FD;
    border-left: 4px solid #00D4FF;
    padding-left: 0.75rem;
    margin: 1.5rem 0 0.8rem 0;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020B18 0%, #061528 100%);
    border-right: 1px solid rgba(0,212,255,0.1);
}
.stTabs [data-baseweb="tab-list"] { gap: 0.5rem; background: transparent; }
.stTabs [data-baseweb="tab"] {
    background: #061528;
    border-radius: 10px 10px 0 0;
    border: 1px solid rgba(0,212,255,0.2);
    color: #8ABDD4; font-weight: 600; padding: 0.5rem 1.2rem;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(0,212,255,0.13), rgba(0,123,255,0.13));
    border-bottom-color: transparent; color: #00D4FF !important;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #020B18; }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.3); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────────────────────────────────────
OCEAN_COLORS = ["#00D4FF","#0099CC","#007BFF","#00E5C3",
                "#33B5E5","#0055AA","#66D9F0","#003D80"]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(6,21,40,0.6)",
    font=dict(family="Inter, sans-serif", color="#E8F4FD"),
    margin=dict(l=20, r=20, t=40, b=20),
    colorway=OCEAN_COLORS,
    hoverlabel=dict(bgcolor="#061528", bordercolor="#00D4FF", font_color="#E8F4FD"),
)

def apply_theme(fig, height=360):
    fig.update_layout(**CHART_LAYOUT, height=height)
    fig.update_xaxes(gridcolor="#0A2240", linecolor="#0A2240")
    fig.update_yaxes(gridcolor="#0A2240", linecolor="#0A2240")
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────────────────────────────────────
dim_region, dim_espece, dim_date, dim_dataset = load_dimensions()
agg_all, geo_all, kpis_total, id_maps = build_joined_agg()
cpue_df = load_cpue()

# ─────────────────────────────────────────────────────────────────────────────
# TRADUCTION DES RÉGIONS EN FRANÇAIS
# ─────────────────────────────────────────────────────────────────────────────
REGION_FR = {
    "North Atlantic Ocean"   : "Océan Atlantique Nord",
    "South Atlantic Ocean"   : "Océan Atlantique Sud",
    "Atlantic Ocean"         : "Océan Atlantique",
    "North Pacific Ocean"    : "Océan Pacifique Nord",
    "South Pacific Ocean"    : "Océan Pacifique Sud",
    "Southern Pacific Ocean" : "Océan Pacifique Sud",
    "North Pacific Region"   : "Région Pacifique Nord",
    "Indian Ocean"           : "Océan Indien",
    "Southern Indian Ocean"  : "Océan Indien Sud",
    "South Indian Ocean"     : "Océan Indien Sud",
    "Southern Ocean"         : "Océan Austral",
    "Arctic Ocean"           : "Océan Arctique",
    "Mediterranean Sea"      : "Mer Méditerranée",
    "Black Sea"              : "Mer Noire",
    "North Sea"              : "Mer du Nord",
    "Norwegian Sea"          : "Mer de Norvège",
    "Baltic Sea"             : "Mer Baltique",
    "Caribbean Sea"          : "Mer des Caraïbes",
    "Arabian Sea"            : "Mer d'Arabie",
    "Persian Gulf"           : "Golfe Persique",
    "Gulf of Mexico"         : "Golfe du Mexique",
    "English Channel"        : "Manche",
    "Philippine Sea"         : "Mer des Philippines",
    "Central Pacific Ocean"  : "Océan Pacifique Central",
}
agg_all["source_region"] = agg_all["source_region"].map(lambda r: REGION_FR.get(r, r))
geo_all["source_region"] = geo_all["source_region"].map(lambda r: REGION_FR.get(r, r))

total_lignes = kpis_total['total_count']

# ─────────────────────────────────────────────────────────────────────────────
# CATÉGORISATION DES ESPÈCES
# ─────────────────────────────────────────────────────────────────────────────
BALEINES = ["Balaenoptera", "Physeter", "Megaptera", "Eubalaena", "Balaena", "Eschrichtius",
            "Hyperoodon", "Mesoplodon", "Ziphius", "Berardius", "Indopacetus", "Kogia",
            "Mysticeti", "Balaenopteridae", "Balaenidae"]
NON_BALEINES = ["Delphinus", "Tursiops", "Globicephala", "Stenella", "Orcinus", "Steno",
                "Grampus", "Lagenodelphis", "Pseudorca", "Feresa", "Peponocephala",
                "Lagenorhynchus", "Phocoena", "Lissodelphis", "Phocoenoides", "Cephalorhynchus",
                "Sousa", "Sotalia", "Delphinapterus", "Monodon", "Orcaella", "Inia",
                "Delphinidae", "Phocoenidae", "Odontoceti"]

def categoriser_espece(nom):
    if not isinstance(nom, str) or nom == "Inconnu":
        return "Non baleine"
    for b in BALEINES:
        if b in nom: return "Baleine"
    return "Non baleine"

agg_all["groupe"] = agg_all["nom_espece"].apply(categoriser_espece)
geo_all["groupe"] = geo_all["nom_espece"].apply(categoriser_espece)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("<div style='font-size:4rem;padding-top:0.2rem;'>🐋</div>", unsafe_allow_html=True)
with col_title:
    st.markdown(f"""
    <div style='padding-top:0.5rem'>
        <div style='font-size:2rem;font-weight:800;color:#00D4FF;letter-spacing:-1px;'>
            SEAMAP · Observatoire des Cétacés
        </div>
        <div style='font-size:0.95rem;color:#8ABDD4;margin-top:0.2rem;'>
            Visualisation des observations de mammifères marins — {total_lignes:,} observations
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);margin:0.5rem 0 1rem 0;'>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — FILTRES GLOBAUX
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Filtres")
    st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);'>", unsafe_allow_html=True)

    region_list = sorted(agg_all["source_region"].dropna().unique().tolist())
    region_sel  = st.multiselect("🌍 Région", region_list, placeholder="Toutes les régions")

    st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);'>", unsafe_allow_html=True)

    groupe_sel = st.radio("🏷️ Groupe d'espèces", ["Tous", "Baleine", "Non baleine"], horizontal=True)

    st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);'>", unsafe_allow_html=True)

    if groupe_sel != "Tous":
        espece_list = sorted(agg_all[agg_all["groupe"] == groupe_sel]["nom_espece"].dropna().unique().tolist())
    else:
        espece_list = sorted(agg_all["nom_espece"].dropna().unique().tolist())
    espece_sel  = st.multiselect("🐬 Espèce", espece_list, placeholder="Toutes les espèces")

    st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);'>", unsafe_allow_html=True)

    years = agg_all["annee"].dropna().astype(int)
    yr_min, yr_max = int(years.min()), int(years.max())
    annee_range = st.slider("📅 Années", yr_min, yr_max, (yr_min, yr_max))

    st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);'>", unsafe_allow_html=True)

    platforms   = sorted(agg_all["source_platform"].dropna().unique().tolist())
    platform_sel = st.multiselect("🚢 Plateforme", platforms, placeholder="Toutes")

    st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);'>", unsafe_allow_html=True)
    st.info(f"📊 **{kpis_total['total_count']:,}** observations\n\n(données nettoyées)")

# ─────────────────────────────────────────────────────────────────────────────
# FILTRAGE SUR L'AGRÉGAT
# ─────────────────────────────────────────────────────────────────────────────
agg = agg_all.copy()
geo = geo_all.copy()

if groupe_sel != "Tous":
    agg = agg[agg["groupe"] == groupe_sel]
    geo = geo[geo["groupe"] == groupe_sel]
if region_sel:
    agg = agg[agg["source_region"].isin(region_sel)]
    geo = geo[geo["source_region"].isin(region_sel)]
if espece_sel:
    agg = agg[agg["nom_espece"].isin(espece_sel)]
    geo = geo[geo["nom_espece"].isin(espece_sel)]
if platform_sel:
    agg = agg[agg["source_platform"].isin(platform_sel)]
agg = agg[agg["annee"].between(annee_range[0], annee_range[1])]


def obs(df):
    """Somme la colonne count."""
    return int(df["count"].sum())

def mean_gs(df):
    """Taille de groupe moyenne pondérée."""
    total = df["count"].sum()
    return df["sum_group_size"].sum() / total if total > 0 else 0.0

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌐 Vue Globale", "🌍 Par Région", "🐬 Par Espèce", "📡 Datasets",
    "🗺️ Analyse Spatiale (Par Dataset)", "⚙️ Gestion des Régions"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VUE GLOBALE
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    # Initialisation de secours pour éviter les NameError
    pop_yr_std = pd.DataFrame(columns=["annee", "pop_std", "individus", "effort", "tendance"])

    # — KPIs —
    k1, k2, k3, k4 = st.columns(4)
    kpi_data = [
        (k1, "🔭", f"{obs(agg):,}",                        "Observations"),
        (k2, "🐋", f"{agg['nom_espece'].nunique():,}",      "Espèces uniques"),
        (k3, "🌍", f"{agg['source_region'].nunique():,}",   "Régions couvertes"),
        (k4, "📐", f"{mean_gs(agg):.2f}",                   "Individus par observation (moy.)"),
    ]
    for col, icon, val, label in kpi_data:
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")

    # — CARTE —
    st.markdown('<div class="section-title">🗺️ Carte des Observations</div>',
                unsafe_allow_html=True)
    map_data = geo.dropna(subset=["latitude", "longitude"])
    if len(map_data) > 50_000:
        map_data = map_data.sample(50_000, random_state=42)

    fig_map = px.scatter_mapbox(
        map_data, lat="latitude", lon="longitude",
        color="source_region", size="group_size", size_max=12,
        opacity=0.65, zoom=1, height=520,
        color_discrete_sequence=px.colors.qualitative.Bold,
        hover_data={"source_region": True, "nom_espece": True,
                    "group_size": True, "latitude": False, "longitude": False},
    )
    fig_map.update_layout(
        mapbox_style="carto-darkmatter",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(bgcolor="#061528", bordercolor="#00D4FF",
                    font=dict(color="#E8F4FD", size=11),
                    title=dict(text="Région", font=dict(color="#00D4FF"))),
        hoverlabel=dict(bgcolor="#061528", bordercolor="#00D4FF", font_color="#E8F4FD"),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # — TIMELINE + TREEMAP —
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown('<div class="section-title">📈 Observations par Année</div>',
                    unsafe_allow_html=True)
        yearly = (agg.groupby("annee", as_index=False)["count"].sum()
                     .rename(columns={"count": "observations"}))
        yearly = yearly[yearly["annee"].between(1990, 2026)]
        fig_yr = go.Figure()
        fig_yr.add_trace(go.Scatter(
            x=yearly["annee"], y=yearly["observations"],
            mode="lines+markers",
            line=dict(color="#00D4FF", width=2.5),
            marker=dict(color="#00D4FF", size=6),
            fill="tozeroy", fillcolor="rgba(0,212,255,0.12)",
            hovertemplate="<b>%{x}</b><br>%{y:,} obs.<extra></extra>",
        ))
        apply_theme(fig_yr)
        fig_yr.update_xaxes(title_text="Année", showgrid=False)
        fig_yr.update_yaxes(title_text="Observations")
        st.plotly_chart(fig_yr, use_container_width=True)

    with c_right:
        st.markdown('<div class="section-title">🗂️ Répartition des Observations par Zone</div>',
                    unsafe_allow_html=True)

        effort = (agg.groupby("source_region", as_index=False)["count"].sum()
                     .sort_values("count", ascending=False))
        effort["pct"] = (effort["count"] / effort["count"].sum() * 100).round(1)

        yr_range = (agg.groupby("source_region")["annee"]
                       .agg(annee_min="min", annee_max="max")
                       .reset_index())
        effort = effort.merge(yr_range, on="source_region", how="left")
        effort["annee_min"] = effort["annee_min"].astype("Int64")
        effort["annee_max"] = effort["annee_max"].astype("Int64")

        fig_tm = px.treemap(
            effort,
            path=[px.Constant("Toutes les zones"), "source_region"],
            values="count",
            color="count",
            color_continuous_scale=[[0, "#003D80"], [0.4, "#0099CC"], [1, "#00D4FF"]],
            custom_data=["pct", "annee_min", "annee_max"],
        )
        fig_tm.update_traces(
            texttemplate=(
                "<b>%{label}</b><br>"
                "%{value:,} obs.<br>"
                "%{customdata[1]}–%{customdata[2]}"
            ),
            textfont=dict(color="#E8F4FD", size=11),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "%{value:,} observations<br>"
                "%{customdata[0]:.1f} % du total<br>"
                "Période : %{customdata[1]}–%{customdata[2]}"
                "<extra></extra>"
            ),
        )
        fig_tm.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), height=360,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_tm, use_container_width=True)

    # — SAISONNALITÉ —
    st.markdown('<div class="section-title">📅 Observations par Trimestre</div>',
                unsafe_allow_html=True)
    TRIMESTRE_MOIS = {
        1: ("Trimestre 1", "Jan · Fév · Mar"),
        2: ("Trimestre 2", "Avr · Mai · Juin"),
        3: ("Trimestre 3", "Juil · Août · Sep"),
        4: ("Trimestre 4", "Oct · Nov · Déc"),
    }
    season = (agg.groupby("trimestre", as_index=False)["count"].sum()
                 .rename(columns={"count": "observations"}))
    season["label"]  = season["trimestre"].map(lambda q: TRIMESTRE_MOIS.get(q, ("?","?"))[0])
    season["mois"]   = season["trimestre"].map(lambda q: TRIMESTRE_MOIS.get(q, ("?","?"))[1])
    season["xlabel"] = season["trimestre"].map(
        lambda q: f"{TRIMESTRE_MOIS.get(q,('?','?'))[0]}<br><sub>{TRIMESTRE_MOIS.get(q,('?','?'))[1]}</sub>"
    )
    fig_s = px.bar(season, x="xlabel", y="observations",
                   color="observations",
                   color_continuous_scale=["#003D80","#0099CC","#00D4FF","#00E5C3"],
                   labels={"observations": "Observations", "xlabel": ""})
    fig_s.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br><br>%{y:,} obs.<extra></extra>",
        customdata=season[["label", "mois"]].values,
    )
    apply_theme(fig_s, height=300)
    fig_s.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_s, use_container_width=True)

    # --- FILTRE ANNÉE EN COURS (Masquer N si incomplet) ---
    from datetime import datetime
    max_display_year = datetime.now().year - 1

    st.markdown('<div class="section-title">👥 Évolution de la Population Observée par Année</div>',
                unsafe_allow_html=True)
    st.caption(f"• **Effort :** Non appliqué (Données brutes).<br>• **Note :** Affichage limité à fin {max_display_year} (données 2026 incomplètes).", unsafe_allow_html=True)

    pop_yr = (agg.groupby("annee", as_index=False)
                 .agg(individus=("sum_group_size", "sum"), nb_obs=("count", "sum")))
    pop_yr = pop_yr[pop_yr["annee"].between(1900, max_display_year)].sort_values("annee")
    pop_yr["tendance"] = pop_yr["individus"].rolling(window=5, center=True, min_periods=1).mean()

    # Ajout des années manquantes pour forcer les lignes en pointillés (connectgaps)
    if not pop_yr.empty:
        all_years = pd.DataFrame({"annee": range(pop_yr["annee"].min(), pop_yr["annee"].max() + 1)})
        pop_yr = all_years.merge(pop_yr, on="annee", how="left")

    fig_pop = go.Figure()
    fig_pop.add_trace(go.Scatter(
        x=pop_yr["annee"], y=pop_yr["individus"],
        mode="lines",
        name="Individus observés",
        line=dict(color="#00D4FF", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0,212,255,0.08)",
        connectgaps=False,
        customdata=pop_yr[["nb_obs"]].values,
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} individus<br>%{customdata[0]:,.0f} observations<extra></extra>",
    ))
    fig_pop.add_trace(go.Scatter(
        x=pop_yr["annee"], y=pop_yr["individus"],
        mode="lines",
        name="Pas de données",
        line=dict(color="#00D4FF", width=1.0, dash="dot"),
        connectgaps=True,
        showlegend=False,
        hoverinfo="skip"
    ))
    fig_pop.add_trace(go.Scatter(
        x=pop_yr["annee"], y=pop_yr["tendance"],
        mode="lines",
        name="Tendance (moy. 5 ans)",
        line=dict(color="#00E5C3", width=2.5, dash="solid"),
        connectgaps=True,
        hovertemplate="<b>%{x}</b><br>Tendance : %{y:,.0f}<extra></extra>",
    ))
    apply_theme(fig_pop, height=380)
    fig_pop.update_layout(
        legend=dict(bgcolor="#061528", bordercolor="#00D4FF",
                    font=dict(color="#E8F4FD", size=12),
                    orientation="h", x=0, y=1.08),
        hovermode="x unified",
    )
    fig_pop.update_xaxes(title_text="Année", showgrid=False, range=[pop_yr["annee"].min(), max_display_year + 2])
    fig_pop.update_yaxes(title_text="Individus observés (total group_size)")
    st.plotly_chart(fig_pop, use_container_width=True)

    import numpy as np
    
    # Fusion avec dim_dataset pour récupérer le type de traitement
    agg_std = agg.merge(dim_dataset[["index_id", "traitement_type"]].drop_duplicates(), left_on="id_dataset_int", right_on="index_id", how="left")
    
    # 1. Calcul Temporel (v5_temporel)
    agg_temp = agg_std[agg_std["traitement_type"] == "v5_temporel"]
    pop_yr_time = (agg_temp.groupby("annee", as_index=False)
                   .agg(individus=("sum_group_size", "sum"), effort=("nb_jours", "sum")))
    effort_moyen_time = pop_yr_time["effort"].mean() if not pop_yr_time.empty else 0
    pop_yr_time["pop_std"] = np.where(pop_yr_time["effort"] > 0, 
                                      (pop_yr_time["individus"] / pop_yr_time["effort"]) * effort_moyen_time, 0)
    
    # 2. Calcul Spatial (v4_spatial)
    agg_spat = agg_std[agg_std["traitement_type"] == "v4_spatial"]
    if not agg_spat.empty:
        dist_df = get_estimated_distances()
        agg_spat = agg_spat.merge(cpue_df[["id_dataset_int", "L_km", "nb_sightings"]].drop_duplicates(), on="id_dataset_int", how="left")
        agg_spat = agg_spat.merge(dist_df, on="id_dataset_int", how="left")
        agg_spat["final_km"] = np.where(agg_spat["L_km"].notna() & (agg_spat["L_km"] > 0), agg_spat["L_km"], agg_spat.get("dist_km", 0))
        agg_spat = agg_spat.dropna(subset=["final_km", "nb_sightings"])
        agg_spat = agg_spat[(agg_spat["nb_sightings"] > 0) & (agg_spat["final_km"] > 0)]
        agg_spat["km_per_sighting"] = agg_spat["final_km"] / agg_spat["nb_sightings"]
        agg_spat["effort"] = agg_spat["count"] * agg_spat["km_per_sighting"]
        
        pop_yr_spat = (agg_spat.groupby("annee", as_index=False)
                       .agg(individus=("sum_group_size", "sum"), effort=("effort", "sum")))
        effort_moyen_spat = pop_yr_spat["effort"].mean() if not pop_yr_spat.empty else 0
        pop_yr_spat["pop_std"] = np.where(pop_yr_spat["effort"] > 0, 
                                          (pop_yr_spat["individus"] / pop_yr_spat["effort"]) * effort_moyen_spat, 0)
    else:
        pop_yr_spat = pd.DataFrame(columns=["annee", "pop_std", "individus", "effort"])

    # 3. Combinaison pour le graph Global
    try:
        pop_comb = pd.concat([pop_yr_time[["annee", "pop_std", "individus", "effort"]], 
                             pop_yr_spat[["annee", "pop_std", "individus", "effort"]]])
        pop_yr_std = pop_comb.groupby("annee", as_index=False).sum()
        pop_yr_std = pop_yr_std[pop_yr_std["annee"].between(1900, max_display_year)].sort_values("annee")
        pop_yr_std["tendance"] = pop_yr_std["pop_std"].rolling(window=5, center=True, min_periods=1).mean()
        
        if not pop_yr_std.empty:
            all_years_std = pd.DataFrame({"annee": range(int(pop_yr_std["annee"].min()), int(pop_yr_std["annee"].max()) + 1)})
            pop_yr_std = all_years_std.merge(pop_yr_std, on="annee", how="left")
    except Exception as e:
        st.warning(f"Erreur lors de la préparation des données globales : {e}")

    st.markdown('<div class="section-title">📉 Évolution de la Population Standardisée (Globale)</div>',
                unsafe_allow_html=True)
    st.caption(f"• **Effort :** Appliqué (Fusion spatiale/temporelle).<br>• **Note :** Affichage limité à fin {max_display_year}.", unsafe_allow_html=True)

    fig_std = go.Figure()
    fig_std.add_trace(go.Scatter(
        x=pop_yr_std["annee"], y=pop_yr_std["pop_std"],
        mode="lines", name="Pop. Standardisée",
        line=dict(color="#33B5E5", width=1.5),
        fill="tozeroy", fillcolor="rgba(51,181,229,0.08)",
        connectgaps=False,
        customdata=pop_yr_std[["individus", "effort"]].values,
        hovertemplate="<b>%{x}</b><br>Pop. Standardisée : %{y:,.0f}<extra></extra>",
    ))
    fig_std.add_trace(go.Scatter(
        x=pop_yr_std["annee"], y=pop_yr_std["tendance"],
        mode="lines", name="Tendance (moy. 5 ans)",
        line=dict(color="#00E5C3", width=2.5),
        connectgaps=True,
        hovertemplate="<b>%{x}</b><br>Tendance : %{y:,.0f}<extra></extra>",
    ))
    apply_theme(fig_std, height=380)
    fig_std.update_xaxes(title_text="Année", showgrid=False, tickformat="d", range=[pop_yr_std["annee"].min(), max_display_year + 2])
    fig_std.update_yaxes(title_text="Individus Standardisés")
    st.plotly_chart(fig_std, use_container_width=True)

    # --- ÉVOLUTION PAR TYPE DE DONNÉES (SPLIT PTOBS / PTPHOTO) ---
    st.markdown('<div class="section-title">📊 Évolution de la Population par Méthode de Collecte</div>',
                unsafe_allow_html=True)
    st.caption(f"• **Effort :** Appliqué (Spécifique à chaque méthode).<br>• **Note :** Affichage limité à fin {max_display_year}.", unsafe_allow_html=True)

    col_obs, col_photo = st.columns(2)

    # 1. Graphique PTOBS (Spatial)
    with col_obs:
        st.markdown('<div style="color:#00D4FF; font-weight:600; margin-bottom:5px;">🔭 Relevés Systématiques (ptobs)</div>', unsafe_allow_html=True)
        if not pop_yr_spat.empty:
            pop_yr_spat = pop_yr_spat[pop_yr_spat["annee"].between(1900, max_display_year)].sort_values("annee")
            fig_spat = go.Figure()
            fig_spat.add_trace(go.Scatter(
                x=pop_yr_spat["annee"], y=pop_yr_spat["pop_std"],
                mode="lines+markers", name="CPUE (KM)",
                line=dict(color="#00D4FF", width=2),
                fill="tozeroy", fillcolor="rgba(0,212,255,0.1)",
                hovertemplate="<b>%{x}</b><br>Pop. Std : %{y:,.0f} indiv/km<extra></extra>"
            ))
            apply_theme(fig_spat, height=300)
            fig_spat.update_xaxes(range=[pop_yr_spat["annee"].min(), max_display_year + 2], tickformat="d")
            st.plotly_chart(fig_spat, use_container_width=True)
        else:
            st.info("Aucune donnée systématique disponible.")

    # 2. Graphique PTPHOTO (Temporel)
    with col_photo:
        st.markdown('<div style="color:#00E5C3; font-weight:600; margin-bottom:5px;">📸 Photo-Identification (ptphoto)</div>', unsafe_allow_html=True)
        if not pop_yr_time.empty:
            pop_yr_time = pop_yr_time[pop_yr_time["annee"].between(1900, max_display_year)].sort_values("annee")
            fig_time = go.Figure()
            fig_time.add_trace(go.Scatter(
                x=pop_yr_time["annee"], y=pop_yr_time["pop_std"],
                mode="lines+markers", name="SPUE (Jours)",
                line=dict(color="#00E5C3", width=2),
                fill="tozeroy", fillcolor="rgba(0,229,195,0.1)",
                hovertemplate="<b>%{x}</b><br>Pop. Std : %{y:,.0f} indiv/jour<extra></extra>"
            ))
            apply_theme(fig_time, height=300)
            fig_time.update_xaxes(range=[pop_yr_time["annee"].min(), max_display_year + 2], tickformat="d")
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("Aucune donnée de photo-ID disponible.")

    # =========================================================================
    # TESTS : GRAPHIQUES SANS FILTRE D'ORGANISATION (SANS DÉDUPLICATION)
    # =========================================================================
    st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15); margin: 3rem 0;'>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🧪 TESTS : Analyse Sans Filtre d\'Organisation</div>', unsafe_allow_html=True)
    st.caption("Ces graphiques sont générés à partir des données brutes, **sans la règle de déduplication** des observations de la même organisation la même année.")
    
    @st.cache_data(show_spinner="Calcul des données brutes en cours...")
    def get_raw_ptphoto(dataset_ids):
        from data_loader import load_dataset_points
        import pandas as pd
        import numpy as np
        def parse_ic(val):
            if pd.isna(val) or str(val).strip() == "": return np.nan
            s = str(val).strip()
            if "-" in s:
                try: return (float(s.split("-")[0]) + float(s.split("-")[1])) / 2.0
                except: pass
            try: return float(s)
            except: return np.nan
            
        all_raw = []
        for ds_id in dataset_ids:
            df = load_dataset_points(ds_id)
            if not df.empty:
                df.columns = df.columns.str.strip().str.lower()
                df["date_time_full"] = pd.to_datetime(df.get("date_time", ""), errors="coerce")
                df = df.dropna(subset=["date_time_full"])
                if df.empty: continue
                df["annee"] = df["date_time_full"].dt.year.astype(int)
                
                if "individual_count" in df.columns:
                    df["abondance"] = df["individual_count"].apply(parse_ic)
                else:
                    df["abondance"] = np.nan
                
                if "group_size" in df.columns:
                    df["abondance"] = df["abondance"].fillna(pd.to_numeric(df["group_size"], errors="coerce"))
                df["abondance"] = df["abondance"].fillna(1).astype(int)
                
                df["jour"] = df["date_time_full"].dt.date
                agg_ds = df.groupby("annee", as_index=False).agg(
                    individus=("abondance", "sum"),
                    nb_jours=("jour", pd.Series.nunique)
                )
                all_raw.append(agg_ds)
        if all_raw:
            res = pd.concat(all_raw, ignore_index=True)
            return res.groupby("annee", as_index=False).sum()
        return pd.DataFrame(columns=["annee", "individus", "nb_jours"])
        
    ptphoto_ids = dim_dataset[dim_dataset["traitement_type"] == "v5_temporel"]["index_id"].unique()
    raw_time = get_raw_ptphoto(ptphoto_ids)
    
    if not raw_time.empty:
        raw_time = raw_time[raw_time["annee"].between(1900, max_display_year)].sort_values("annee")
        em = raw_time["nb_jours"].mean()
        raw_time["pop_std"] = np.where(raw_time["nb_jours"] > 0, (raw_time["individus"] / raw_time["nb_jours"]) * em, 0)
        
        # --- 1. Graphique GLOBAL SANS DÉDUPLICATION ---
        st.markdown('<div style="color:#33B5E5; font-weight:600; margin-bottom:5px; margin-top:1.5rem;">📉 Évolution de la Population Standardisée (Globale) — SANS FILTRE</div>', unsafe_allow_html=True)
        raw_comb = pd.concat([raw_time[["annee", "pop_std", "individus", "nb_jours"]].rename(columns={"nb_jours": "effort"}), 
                              pop_yr_spat[["annee", "pop_std", "individus", "effort"]]])
        raw_global = raw_comb.groupby("annee", as_index=False).sum()
        raw_global = raw_global[raw_global["annee"].between(1900, max_display_year)].sort_values("annee")
        raw_global["tendance"] = raw_global["pop_std"].rolling(window=5, center=True, min_periods=1).mean()
        
        if not raw_global.empty:
            all_years_raw = pd.DataFrame({"annee": range(int(raw_global["annee"].min()), int(raw_global["annee"].max()) + 1)})
            raw_global = all_years_raw.merge(raw_global, on="annee", how="left")

        fig_std_raw = go.Figure()
        fig_std_raw.add_trace(go.Scatter(
            x=raw_global["annee"], y=raw_global["pop_std"],
            mode="lines", name="Pop. Standardisée (Sans Filtre)",
            line=dict(color="#FF4B4B", width=1.5),
            fill="tozeroy", fillcolor="rgba(255,75,75,0.08)",
            connectgaps=False,
            customdata=raw_global[["individus", "effort"]].values,
            hovertemplate="<b>%{x}</b><br>Pop. Standardisée : %{y:,.0f}<br>Brut : %{customdata[0]:,.0f}<br>Effort : %{customdata[1]:,.0f}<extra></extra>",
        ))
        fig_std_raw.add_trace(go.Scatter(
            x=raw_global["annee"], y=raw_global["tendance"],
            mode="lines", name="Tendance",
            line=dict(color="#FF8A8A", width=2.5),
            connectgaps=True,
            hovertemplate="<b>%{x}</b><br>Tendance : %{y:,.0f}<extra></extra>",
        ))
        if not pop_yr_std.empty:
            fig_std_raw.add_trace(go.Scatter(
                x=pop_yr_std["annee"], y=pop_yr_std["pop_std"],
                mode="lines+markers", name="AVEC Filtre (Officiel)",
                line=dict(color="#33B5E5", width=2, dash="dot"),
                hovertemplate="<b>%{x}</b><br>Avec Filtre : %{y:,.0f}<extra></extra>",
            ))

        apply_theme(fig_std_raw, height=380)
        fig_std_raw.update_layout(
            legend=dict(bgcolor="#061528", bordercolor="#00D4FF", font=dict(color="#E8F4FD", size=12), orientation="h", x=0, y=1.08),
            hovermode="x unified"
        )
        fig_std_raw.update_xaxes(title_text="Année", showgrid=False, tickformat="d", range=[raw_global["annee"].min(), max_display_year + 2])
        fig_std_raw.update_yaxes(title_text="Individus Standardisés")
        st.plotly_chart(fig_std_raw, use_container_width=True)

        # --- 2. Graphique PTPHOTO SANS DÉDUPLICATION ---
        st.markdown('<div style="color:#00E5C3; font-weight:600; margin-bottom:5px; margin-top:1.5rem;">📸 Photo-Identification (ptphoto) — SANS FILTRE</div>', unsafe_allow_html=True)
        fig_time_raw = go.Figure()
        fig_time_raw.add_trace(go.Scatter(
            x=raw_time["annee"], y=raw_time["pop_std"],
            mode="lines+markers", name="SANS Filtre (Brut)",
            line=dict(color="#FF4B4B", width=2),
            fill="tozeroy", fillcolor="rgba(255,75,75,0.1)",
            hovertemplate="<b>%{x}</b><br>Brut : %{y:,.0f} indiv/jour<extra></extra>"
        ))
        if not pop_yr_time.empty:
            fig_time_raw.add_trace(go.Scatter(
                x=pop_yr_time["annee"], y=pop_yr_time["pop_std"],
                mode="lines+markers", name="AVEC Filtre (Officiel)",
                line=dict(color="#00E5C3", width=2, dash="dot"),
                hovertemplate="<b>%{x}</b><br>Avec Filtre : %{y:,.0f} indiv/jour<extra></extra>"
            ))

        apply_theme(fig_time_raw, height=300)
        fig_time_raw.update_xaxes(range=[raw_time["annee"].min(), max_display_year + 2], tickformat="d")
        st.plotly_chart(fig_time_raw, use_container_width=True)

    # — ÉVOLUTION DE LA POPULATION OBSERVÉE (ÉCHELLE LOG) —
    st.markdown('<div class="section-title">📉 Évolution Standardisée (Échelle Logarithmique)</div>',
                unsafe_allow_html=True)
    st.caption(f"• **Effort :** Appliqué (Standardisation CPUE/SPUE).<br>• **Note :** Affichage limité à fin {max_display_year}.", unsafe_allow_html=True)

    fig_pop_log = go.Figure()
    fig_pop_log.add_trace(go.Scatter(
        x=pop_yr_std["annee"], y=pop_yr_std["pop_std"],
        mode="lines",
        name="Pop. Standardisée",
        line=dict(color="#00D4FF", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0,212,255,0.08)",
        connectgaps=False,
        customdata=pop_yr_std[["individus", "effort"]].values,
        hovertemplate="<b>%{x}</b><br>Pop. Std (Log) : %{y:,.0f}<br>Pop. Brute : %{customdata[0]:,.0f} individus<br>Effort : %{customdata[1]:,.0f} unités<extra></extra>",
    ))
    fig_pop_log.add_trace(go.Scatter(
        x=pop_yr_std["annee"], y=pop_yr_std["pop_std"],
        mode="lines",
        line=dict(color="#00D4FF", width=1.0, dash="dot"),
        connectgaps=True,
        showlegend=False,
        hoverinfo="skip"
    ))
    fig_pop_log.add_trace(go.Scatter(
        x=pop_yr_std["annee"], y=pop_yr_std["tendance"],
        mode="lines",
        name="Tendance (moy. 5 ans)",
        line=dict(color="#00E5C3", width=2.5, dash="solid"),
        connectgaps=True,
        hovertemplate="<b>%{x}</b><br>Tendance : %{y:,.0f}<extra></extra>",
    ))
    apply_theme(fig_pop_log, height=380)
    fig_pop_log.update_layout(
        legend=dict(bgcolor="#061528", bordercolor="#00D4FF",
                    font=dict(color="#E8F4FD", size=12),
                    orientation="h", x=0, y=1.08),
        hovermode="x unified",
    )
    fig_pop_log.update_xaxes(title_text="Année", showgrid=False, range=[pop_yr_std["annee"].min(), max_display_year + 2])
    fig_pop_log.update_yaxes(title_text="Individus Standardisés (Log)", type="log")
    st.plotly_chart(fig_pop_log, use_container_width=True)

    # — ÉVOLUTION DU NOMBRE D'OBSERVATIONS —
    st.markdown('<div class="section-title">📈 Évolution du Nombre d\'Observations par Année</div>',
                unsafe_allow_html=True)
    st.caption("• **Données :** Nombre d'événements d'observation (lignes dans le jeu de données) par année.", unsafe_allow_html=True)

    pop_yr["tendance_obs"] = pop_yr["nb_obs"].rolling(window=5, center=True, min_periods=1).mean()

    fig_obs = go.Figure()
    fig_obs.add_trace(go.Scatter(
        x=pop_yr["annee"], y=pop_yr["nb_obs"],
        mode="lines",
        name="Observations",
        line=dict(color="#00D4FF", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0,212,255,0.08)",
        connectgaps=False,
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} observations<extra></extra>",
    ))
    fig_obs.add_trace(go.Scatter(
        x=pop_yr["annee"], y=pop_yr["nb_obs"],
        mode="lines",
        line=dict(color="#00D4FF", width=1.0, dash="dot"),
        connectgaps=True,
        showlegend=False,
        hoverinfo="skip"
    ))
    fig_obs.add_trace(go.Scatter(
        x=pop_yr["annee"], y=pop_yr["tendance_obs"],
        mode="lines",
        name="Tendance (moy. 5 ans)",
        line=dict(color="#00E5C3", width=2.5, dash="solid"),
        connectgaps=True,
        hovertemplate="<b>%{x}</b><br>Tendance : %{y:,.0f}<extra></extra>",
    ))
    apply_theme(fig_obs, height=380)
    fig_obs.update_layout(
        legend=dict(bgcolor="#061528", bordercolor="#00D4FF",
                    font=dict(color="#E8F4FD", size=12),
                    orientation="h", x=0, y=1.08),
        hovermode="x unified",
    )
    fig_obs.update_xaxes(title_text="Année", showgrid=False)
    fig_obs.update_yaxes(title_text="Nombre d'observations")
    st.plotly_chart(fig_obs, use_container_width=True)



# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PAR RÉGION
# ══════════════════════════════════════════════════════════════════════════════
with tab2:

    st.markdown('<div class="section-title">🏆 Top 20 Régions — Nombre d\'Observations</div>',
                unsafe_allow_html=True)
    top_pays = (agg.groupby("source_region", as_index=False)["count"].sum()
                   .sort_values("count", ascending=True).tail(20))
    fig_pays = go.Figure(go.Bar(
        x=top_pays["count"], y=top_pays["source_region"], orientation="h",
        marker=dict(color=top_pays["count"],
                    colorscale=[[0,"#003D80"],[0.5,"#0099CC"],[1,"#00D4FF"]]),
        hovertemplate="<b>%{y}</b><br>%{x:,} obs.<extra></extra>",
    ))
    apply_theme(fig_pays, height=520)
    fig_pays.update_xaxes(title_text="Observations")
    st.plotly_chart(fig_pays, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-title">🚢 Plateforme par Région (Top 10)</div>',
                    unsafe_allow_html=True)
        top10 = agg.groupby("source_region")["count"].sum().nlargest(10).index
        plat = (agg[agg["source_region"].isin(top10)]
                .groupby(["source_region","source_platform"], as_index=False)["count"].sum())
        fig_pp = px.bar(plat, x="count", y="source_region", color="source_platform",
                        orientation="h", color_discrete_sequence=OCEAN_COLORS,
                        labels={"count": "Observations", "source_region": "",
                                "source_platform": "Plateforme"})
        apply_theme(fig_pp, height=400)
        st.plotly_chart(fig_pp, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">📊 Évolution Annuelle — Top 6 Régions</div>',
                    unsafe_allow_html=True)
        top6 = agg.groupby("source_region")["count"].sum().nlargest(6).index
        yr_p = (agg[agg["source_region"].isin(top6)]
                .groupby(["annee","source_region"], as_index=False)["count"].sum())
        yr_p = yr_p[yr_p["annee"].between(1990, 2026)]
        fig_yp = px.line(yr_p, x="annee", y="count", color="source_region",
                         color_discrete_sequence=OCEAN_COLORS, markers=True,
                         labels={"annee":"Année","count":"Observations","source_region":"Région"})
        apply_theme(fig_yp, height=400)
        st.plotly_chart(fig_yp, use_container_width=True)

    st.markdown('<div class="section-title">🗂️ Treemap : Région → Plateforme</div>',
                unsafe_allow_html=True)
    tree = (agg.groupby(["source_region","source_platform"], as_index=False)["count"].sum())
    fig_tree = px.treemap(tree,
                          path=[px.Constant("Monde"), "source_region", "source_platform"],
                          values="count", color="count",
                          color_continuous_scale=["#003D80","#0099CC","#00D4FF"])
    fig_tree.update_traces(
        textfont=dict(color="#E8F4FD"),
        hovertemplate="<b>%{label}</b><br>%{value:,} obs.<extra></extra>",
    )
    fig_tree.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0), height=450,
        coloraxis_colorbar=dict(tickfont=dict(color="#E8F4FD"),
                                title=dict(text="Obs.", font=dict(color="#00D4FF"))),
    )
    st.plotly_chart(fig_tree, use_container_width=True)





# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PAR ESPÈCE
# ══════════════════════════════════════════════════════════════════════════════
with tab3:

    st.markdown('<div class="section-title">🐋 Top 20 Espèces les Plus Observées</div>',
                unsafe_allow_html=True)
    top_sp = (agg.groupby("nom_espece", as_index=False)["count"].sum()
                 .sort_values("count", ascending=True).tail(20))
    fig_sp = go.Figure(go.Bar(
        x=top_sp["count"], y=top_sp["nom_espece"], orientation="h",
        marker=dict(color=top_sp["count"],
                    colorscale=[[0,"#003D80"],[0.5,"#00E5C3"],[1,"#00D4FF"]]),
        hovertemplate="<b>%{y}</b><br>%{x:,} obs.<extra></extra>",
    ))
    apply_theme(fig_sp, height=560)
    fig_sp.update_xaxes(title_text="Observations")
    st.plotly_chart(fig_sp, use_container_width=True)

    st.markdown('<div class="section-title">🔬 Analyse Individuelle</div>',
                unsafe_allow_html=True)
    espece_opts = (agg.groupby("nom_espece")["count"].sum()
                      .sort_values(ascending=False).index.tolist())
    if espece_opts:
        chosen = st.selectbox("Choisir une espèce", espece_opts, key="sp_sel")
        sp_agg = agg[agg["nom_espece"] == chosen]

        ce1, ce2 = st.columns(2)
        with ce1:
            sp_pays = (sp_agg.groupby("source_region", as_index=False)["count"].sum()
                             .sort_values("count", ascending=False).head(15))
            fig_spp = px.bar(sp_pays, x="source_region", y="count",
                             color="count",
                             color_continuous_scale=["#003D80","#0099CC","#00D4FF"],
                             labels={"source_region":"Région","count":"Observations"},
                             title=f"Distribution — {chosen.split('(')[0].strip()}")
            apply_theme(fig_spp, height=380)
            fig_spp.update_layout(coloraxis_showscale=False, title_font_color="#00D4FF")
            st.plotly_chart(fig_spp, use_container_width=True)

        with ce2:
            sp_yr = (sp_agg.groupby("annee", as_index=False)["count"].sum())
            sp_yr = sp_yr[sp_yr["annee"].between(1990, 2026)]
            fig_syr = go.Figure()
            fig_syr.add_trace(go.Scatter(
                x=sp_yr["annee"], y=sp_yr["count"],
                mode="lines+markers",
                line=dict(color="#00E5C3", width=2.5),
                marker=dict(color="#00E5C3", size=7),
                fill="tozeroy", fillcolor="rgba(0,229,195,0.1)",
                hovertemplate="<b>%{x}</b><br>%{y:,} obs.<extra></extra>",
            ))
            apply_theme(fig_syr, height=380)
            fig_syr.update_layout(
                title=f"Évolution — {chosen.split('(')[0].strip()}",
                title_font_color="#00E5C3"
            )
            fig_syr.update_xaxes(title_text="Année", showgrid=False)
            fig_syr.update_yaxes(title_text="Observations")
            st.plotly_chart(fig_syr, use_container_width=True)

        # Carte espèce
        st.markdown(f'<div class="section-title">🗺️ Carte — {chosen.split("(")[0].strip()}</div>',
                    unsafe_allow_html=True)
        geo_sp = geo[geo["nom_espece"] == chosen].dropna(subset=["latitude","longitude"])
        if len(geo_sp) > 20_000:
            geo_sp = geo_sp.sample(20_000, random_state=42)
        if not geo_sp.empty:
            fig_msp = px.scatter_mapbox(
                geo_sp, lat="latitude", lon="longitude",
                color="source_region", size="group_size", size_max=14,
                opacity=0.75, zoom=1, height=450,
                color_discrete_sequence=OCEAN_COLORS,
            )
            fig_msp.update_layout(
                mapbox_style="carto-darkmatter",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(bgcolor="#061528", bordercolor="#00D4FF",
                            font=dict(color="#E8F4FD")),
                hoverlabel=dict(bgcolor="#061528", bordercolor="#00E5C3"),
            )
            st.plotly_chart(fig_msp, use_container_width=True)
        else:
            st.info("Pas assez de points pour cette espèce avec les filtres actuels.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DATASETS & PLATEFORMES
# ══════════════════════════════════════════════════════════════════════════════
with tab4:


    cd1, cd2 = st.columns(2)

    with cd1:
        st.markdown('<div class="section-title">🎯 Type de Données</div>',
                    unsafe_allow_html=True)
        type_df = (agg.groupby("source_type", as_index=False)["count"].sum()
                      .rename(columns={"count": "observations"}))
        fig_type = go.Figure(go.Pie(
            labels=type_df["source_type"], values=type_df["observations"],
            hole=0.5,
            marker=dict(colors=OCEAN_COLORS, line=dict(color="#020B18", width=2)),
            textfont=dict(color="#E8F4FD", size=12),
            hovertemplate="<b>%{label}</b><br>%{value:,} obs. (%{percent})<extra></extra>",
        ))
        fig_type.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=30, b=20), height=360,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#E8F4FD")),
            annotations=[dict(text="Type", showarrow=False,
                              font=dict(color="#00D4FF", size=14))],
        )
        st.plotly_chart(fig_type, use_container_width=True)

    with cd2:
        st.markdown('<div class="section-title">🚢 Plateformes d\'Observation</div>',
                    unsafe_allow_html=True)
        plat_df = (agg.groupby("source_platform", as_index=False)["count"].sum()
                      .sort_values("count", ascending=False))
        fig_plat = go.Figure(go.Bar(
            x=plat_df["source_platform"], y=plat_df["count"],
            marker=dict(color=plat_df["count"],
                        colorscale=[[0,"#003D80"],[0.5,"#0099CC"],[1,"#00D4FF"]]),
            hovertemplate="<b>%{x}</b><br>%{y:,} obs.<extra></extra>",
        ))
        apply_theme(fig_plat, height=360)
        fig_plat.update_layout(coloraxis_showscale=False)
        fig_plat.update_xaxes(title_text="Plateforme")
        fig_plat.update_yaxes(title_text="Observations")
        st.plotly_chart(fig_plat, use_container_width=True)

    st.markdown('<div class="section-title">📅 Évolution du Type de Données par Année</div>',
                unsafe_allow_html=True)
    
    type_yr = (agg.groupby(["annee", "source_type"], as_index=False)["count"].sum()
                  .rename(columns={"count": "observations"}))
    type_yr["source_type_fr"] = type_yr["source_type"].map({
        "ptobs": "Point d'observation (ptobs)",
        "ptphoto": "Point photo (ptphoto)"
    }).fillna(type_yr["source_type"])
    
    fig_type_yr = px.bar(
        type_yr,
        x="annee",
        y="observations",
        color="source_type_fr",
        barmode="stack",
        color_discrete_map={
            "Point d'observation (ptobs)": "#00D4FF",
            "Point photo (ptphoto)": "#00E5C3"
        },
        labels={"annee": "Année", "observations": "Observations", "source_type_fr": "Type de données"}
    )
    apply_theme(fig_type_yr, height=380)
    fig_type_yr.update_layout(
        legend=dict(
            bgcolor="#061528",
            bordercolor="rgba(0,212,255,0.2)",
            x=0, y=1.1,
            orientation="h"
        )
    )
    fig_type_yr.update_xaxes(title_text="Année")
    fig_type_yr.update_yaxes(title_text="Observations")
    st.plotly_chart(fig_type_yr, use_container_width=True)

    st.markdown('<div class="section-title">🏛️ Top 15 Fournisseurs de Données</div>',
                unsafe_allow_html=True)
    dim_prov = (dim_dataset[["id_dataset_int"]].drop_duplicates())
    prov_df = (agg.groupby("source_provider", as_index=False)["count"].sum()
                  .rename(columns={"source_provider": "provider"})
                  .sort_values("count", ascending=False).head(15))
    fig_prov = px.bar(prov_df, x="count", y="provider", orientation="h",
                      color="count",
                      color_continuous_scale=["#003D80","#0099CC","#00D4FF"],
                      labels={"count":"Observations","provider":""})
    fig_prov.update_traces(hovertemplate="<b>%{y}</b><br>%{x:,} obs.<extra></extra>")
    apply_theme(fig_prov, height=460)
    fig_prov.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_prov, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — ANALYSE SPATIALE PAR DATASET
# ══════════════════════════════════════════════════════════════════════════════
with tab5:

    if not _FOLIUM_OK:
        st.error("❌ `streamlit-folium` n'est pas installé. Lancez : `pip install streamlit-folium`")
    elif not _GPD_OK:
        st.error("❌ `geopandas` n'est pas installé. Lancez : `pip install geopandas`")
    else:
        # ── Chargement de l'index ─────────────────────────────────────────────
        idx_df = load_index()
        # Conserver uniquement les datasets ayant un fichier points
        idx_valid = idx_df[idx_df["has_points"]].copy()

        if idx_valid.empty:
            st.warning("Aucun fichier de points trouvé dans le répertoire data_sources_point.")
        else:
            # ── Filtres de la sidebar spécifique à cet onglet ─────────────────
            col_sel, col_info = st.columns([3, 1])

            with col_sel:
                # Sélecteur de région pour filtrer les datasets
                regions_idx = sorted(idx_valid["Region"].dropna().unique().tolist())
                region_filter = st.selectbox(
                    "🌍 Filtrer par Région",
                    ["Toutes"] + regions_idx,
                    key="sp_region_filter"
                )

            if region_filter != "Toutes":
                idx_view = idx_valid[idx_valid["Region"] == region_filter].copy()
            else:
                idx_view = idx_valid.copy()

            # Construction des labels pour le selectbox
            idx_view["_label"] = idx_view.apply(
                lambda r: f"[{r['ID']}] {str(r['Title'])[:70]}{'…' if len(str(r['Title'])) > 70 else ''} — {str(r.get('Provider', ''))[:30]}",
                axis=1
            )
            label_to_id = dict(zip(idx_view["_label"], idx_view["ID"]))

            with col_sel:
                chosen_label = st.selectbox(
                    "📦 Sélectionner un Dataset",
                    list(label_to_id.keys()),
                    key="sp_dataset_sel"
                )

            chosen_id = label_to_id[chosen_label]

            # ── Chargement des données du dataset choisi ──────────────────────
            pts_df   = load_dataset_points(chosen_id)
            gdb_path = find_survey_track(chosen_id)

            # Indicateur de confiance
            has_track  = gdb_path is not None
            confidence = "Haute" if has_track else "Modérée"
            conf_color = "#00E5C3" if has_track else "#FFB347"
            conf_icon  = "🟢" if has_track else "🟡"
            conf_detail = ("Survey track (.gdb) disponible" if has_track
                           else "Enveloppe convexe des points utilisée")

            with col_info:
                st.markdown(
                    f"""
                    <div style='background:linear-gradient(135deg,#061528,#0a2240);
                    border:1px solid {conf_color};border-radius:12px;
                    padding:0.8rem 1rem;margin-top:1.8rem;text-align:center;'>
                        <div style='font-size:1.4rem;'>{conf_icon}</div>
                        <div style='color:{conf_color};font-weight:700;font-size:0.95rem;'>Confiance {confidence}</div>
                        <div style='color:#8ABDD4;font-size:0.72rem;margin-top:0.2rem;'>{conf_detail}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("<hr style='border:1px solid rgba(0,212,255,0.15);margin:0.8rem 0;'>",
                        unsafe_allow_html=True)

            if pts_df.empty:
                st.warning("⚠️ Aucune donnée de points disponible pour ce dataset.")
            else:
                pts_clean = pts_df.dropna(subset=["latitude", "longitude"]).copy()

                # ── Calcul de la zone d'étude ─────────────────────────────────
                with st.spinner("⏳ Calcul de la zone d'étude..."):
                    zone_gdf, zone_confidence, area_km2 = compute_study_zone(
                        pts_clean, gdb_path, buffer_m=500
                    )

                # ── KPIs ─────────────────────────────────────────────────────
                nb_points    = len(pts_clean)
                total_indiv  = int(pd.to_numeric(pts_clean.get("group_size", pd.Series([0])),
                                                  errors="coerce").sum())
                density      = compute_density_indicator(pts_clean, area_km2)

                date_col = "date_time" if "date_time" in pts_clean.columns else None
                if date_col and pts_clean[date_col].notna().any():
                    dates_str   = pts_clean[date_col].dropna().astype(str)
                    periode_min = dates_str.min()
                    periode_max = dates_str.max()
                    periode_txt = f"{periode_min[:10]} → {periode_max[:10]}"
                else:
                    periode_txt = "N/A"

                sp_k1, sp_k2, sp_k3, sp_k4 = st.columns(4)
                sp_kpi_data = [
                    (sp_k1, "📍", f"{nb_points:,}",    "Points d'observation"),
                    (sp_k2, "🐋", f"{total_indiv:,}", "Individus observés"),
                    (sp_k3, "📐", f"{area_km2:,.1f} km²", "Superficie zone d'étude"),
                    (sp_k4, "📊", f"{density:.4f}",   "Individus / km²"),
                ]
                for col, icon, val, label in sp_kpi_data:
                    with col:
                        st.markdown(f"""
                        <div class="kpi-card">
                            <div class="kpi-icon">{icon}</div>
                            <div class="kpi-value" style='font-size:1.7rem;'>{val}</div>
                            <div class="kpi-label">{label}</div>
                        </div>""", unsafe_allow_html=True)

                st.markdown(
                    f"<div style='color:#8ABDD4;font-size:0.82rem;margin:0.5rem 0 0.8rem 0;'>"
                    f"📅 Période : <strong style='color:#E8F4FD;'>{periode_txt}</strong>&nbsp;&nbsp;"
                    f"📦 Dataset : <strong style='color:#00D4FF;'>{chosen_id}</strong></div>",
                    unsafe_allow_html=True
                )

                st.markdown("<hr style='border:1px solid rgba(0,212,255,0.1);margin:0.5rem 0;'>",
                            unsafe_allow_html=True)

                # ── Carte Folium ──────────────────────────────────────────────
                st.markdown('<div class="section-title">🗺️ Carte des Observations</div>',
                            unsafe_allow_html=True)

                # Centre de la carte
                lat_center = pts_clean["latitude"].mean()
                lon_center = pts_clean["longitude"].mean()

                m = folium.Map(
                    location=[lat_center, lon_center],
                    zoom_start=5,
                    tiles="CartoDB dark_matter",
                )

                # Couche 1 : Trajectoire réelle (si disponible)
                if has_track and zone_confidence == "Haute":
                    track_gdf = None
                    try:
                        from data_loader import load_track_lines as _ltl
                        track_gdf = _ltl(gdb_path)
                    except Exception:
                        pass

                    if track_gdf is not None and not track_gdf.empty:
                        # On ne garde QUE la géométrie pour éviter les
                        # erreurs de sérialisation JSON (Timestamp, etc.)
                        import geopandas as gpd_local
                        track_geom_only = gpd_local.GeoDataFrame(
                            geometry=track_gdf.geometry, crs=track_gdf.crs
                        )
                        folium.GeoJson(
                            track_geom_only.__geo_interface__,
                            name="Trajectoire",
                            style_function=lambda _: {
                                "color": "#3399FF",
                                "weight": 2.5,
                                "opacity": 0.6,
                            },
                            tooltip="Trajectoire de recherche",
                        ).add_to(m)

                # Couche 2 : Zone d'étude (buffer ou hull) — géométrie seule
                if zone_gdf is not None and not zone_gdf.empty:
                    zone_label = ("Zone tampon 500m (survey track)"
                                  if has_track else "Enveloppe convexe (points)")
                    zone_color = "#00D4FF" if has_track else "#FFB347"
                    import geopandas as gpd_local
                    zone_geom_only = gpd_local.GeoDataFrame(
                        geometry=zone_gdf.geometry, crs=zone_gdf.crs
                    )
                    folium.GeoJson(
                        zone_geom_only.__geo_interface__,
                        name=zone_label,
                        style_function=lambda _, zc=zone_color: {
                            "fillColor": zc,
                            "fillOpacity": 0.12,
                            "color": zc,
                            "weight": 1.5,
                            "dashArray": "5, 5",
                        },
                        tooltip=zone_label,
                    ).add_to(m)

                # Couche 3 : Points d'observation (limités à 5000 pour la perf)
                pts_map = pts_clean.copy()
                if len(pts_map) > 5000:
                    pts_map = pts_map.sample(5000, random_state=42)

                for _, row in pts_map.iterrows():
                    species  = str(row.get("scientific_name") or row.get("common_name") or "N/A")
                    date_val = str(row.get("date_time") or "N/A")
                    gs_val   = row.get("group_size", 1)
                    try:
                        gs_int = int(gs_val)
                    except (ValueError, TypeError):
                        gs_int = 1

                    popup_html = f"""
                    <div style='font-family:Inter,sans-serif;min-width:160px;'>
                        <b style='color:#00D4FF;'>{species}</b><br>
                        📅 {date_val}<br>
                        👥 {gs_int} individu(s)
                    </div>
                    """
                    folium.CircleMarker(
                        location=[row["latitude"], row["longitude"]],
                        radius=max(3, min(10, gs_int)),
                        color="#FF4444",
                        fill=True,
                        fill_color="#FF6666",
                        fill_opacity=0.75,
                        popup=folium.Popup(popup_html, max_width=220),
                        tooltip=f"{species} ({gs_int} ind.)",
                    ).add_to(m)

                folium.LayerControl(collapsed=False).add_to(m)

                # Affichage de la carte
                _map_out = st_folium(m, use_container_width=True, height=520, returned_objects=[], key="folium_ds")

                # ── Graphique temporel ────────────────────────────────────────
                if date_col and pts_clean[date_col].notna().any():
                    st.markdown('<div class="section-title">📈 Évolution Temporelle des Observations</div>',
                                unsafe_allow_html=True)

                    pts_time = pts_clean.copy()
                    pts_time["date_parsed"] = pd.to_datetime(
                        pts_time[date_col], errors="coerce"
                    )
                    pts_time = pts_time.dropna(subset=["date_parsed"])

                    if not pts_time.empty:
                        pts_time["annee"] = pts_time["date_parsed"].dt.year
                        pts_time["gs_num"] = pd.to_numeric(
                            pts_time.get("group_size", 1), errors="coerce"
                        ).fillna(1)

                        yr_grp = (
                            pts_time.groupby("annee", as_index=False)
                                    .agg(nb_obs=("gs_num", "count"),
                                         nb_indiv=("gs_num", "sum"))
                        )

                        fig_sp_time = go.Figure()
                        fig_sp_time.add_trace(go.Bar(
                            x=yr_grp["annee"], y=yr_grp["nb_indiv"],
                            name="Individus",
                            marker_color="#00D4FF",
                            opacity=0.8,
                            hovertemplate="<b>%{x}</b><br>%{y:,} individus<extra></extra>",
                        ))
                        fig_sp_time.add_trace(go.Scatter(
                            x=yr_grp["annee"], y=yr_grp["nb_obs"],
                            name="Observations",
                            mode="lines+markers",
                            line=dict(color="#00E5C3", width=2),
                            marker=dict(size=6),
                            yaxis="y2",
                            hovertemplate="<b>%{x}</b><br>%{y:,} obs.<extra></extra>",
                        ))
                        fig_sp_time.update_layout(
                            **{k: v for k, v in CHART_LAYOUT.items()},
                            height=320,
                            yaxis=dict(title="Individus", gridcolor="#0A2240"),
                            yaxis2=dict(
                                title="Observations",
                                overlaying="y",
                                side="right",
                                gridcolor="#0A2240",
                                color="#00E5C3",
                            ),
                            legend=dict(
                                bgcolor="#061528", bordercolor="#00D4FF",
                                font=dict(color="#E8F4FD", size=11),
                                orientation="h", x=0, y=1.08
                            ),
                            hovermode="x unified",
                        )
                        st.plotly_chart(fig_sp_time, use_container_width=True)

                # ── Tableau des espèces ───────────────────────────────────────
                if "scientific_name" in pts_clean.columns:
                    st.markdown('<div class="section-title">🔬 Espèces Observées</div>',
                                unsafe_allow_html=True)
                    sp_summary = (
                        pts_clean.groupby("scientific_name", as_index=False)
                                 .agg(nb_obs=("latitude", "count"),
                                      nb_indiv=("group_size",
                                                lambda x: pd.to_numeric(x, errors="coerce").sum()))
                                 .sort_values("nb_indiv", ascending=False)
                    )
                    sp_summary["nb_indiv"] = sp_summary["nb_indiv"].astype(int)
                    sp_summary.columns = ["Espèce (scientifique)", "Nb observations", "Nb individus"]
                    st.dataframe(
                        sp_summary,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Nb individus": st.column_config.ProgressColumn(
                                "Nb individus",
                                min_value=0,
                                max_value=int(sp_summary["Nb individus"].max()),
                                format="%d",
                            )
                        }
                    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — GESTION DES REGIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-title">⚙️ Validation et Configuration des Régions</div>', unsafe_allow_html=True)
    st.caption("Cette interface vous permet de confirmer la région océanique des nouveaux datasets détectés avant leur traitement complet par Airflow.")

    # Chargement en direct sans cache
    try:
        df_idx = pd.read_csv("index.csv", dtype=str)
        df_idx.columns = df_idx.columns.str.strip()
    except Exception as e:
        st.error(f"Erreur de chargement d'index.csv : {e}")
        df_idx = pd.DataFrame()

    if not df_idx.empty:
        # Trouver les datasets sans région ou marqués PENDING
        pending_mask = df_idx["Region"].isna() | (df_idx["Region"].str.strip() == "") | (df_idx["Region"].str.strip().str.upper() == "PENDING")
        pending_df = df_idx[pending_mask]

        if pending_df.empty:
            st.success("🎉 Tous les datasets sont configurés ! Aucun dataset n'est en attente de confirmation de région.")
        else:
            st.info(f"📋 Il y a **{len(pending_df)}** dataset(s) en attente de configuration.")
            
            # Label de sélection
            pending_df["_sel_label"] = pending_df.apply(
                lambda r: f"[{r['ID']}] {str(r['Title'])[:60]}... — {r.get('Provider', '')[:20]}", axis=1
            )
            label_map = dict(zip(pending_df["_sel_label"], pending_df["ID"]))
            
            chosen_label = st.selectbox("📦 Choisir un dataset à configurer", list(label_map.keys()))
            chosen_id = label_map[chosen_label]
            
            # Suggestion de région
            from data_loader import suggest_region_for_dataset
            with st.spinner("⏳ Recherche de la région suggérée..."):
                sugg_region, sugg_source = suggest_region_for_dataset(chosen_id)
                
            # Affichage de la source de suggestion
            if "API" in sugg_source:
                st.markdown(f"💡 **Région suggérée :** `{sugg_region}` (Détectée via : **🟢 {sugg_source}**)")
            else:
                st.markdown(f"💡 **Région suggérée :** `{sugg_region}` (Détectée via : **🟡 {sugg_source}**)")
                
            # Options de sélection
            all_regions = sorted(df_idx["Region"].dropna().unique().tolist())
            all_regions = [r for r in all_regions if r.strip() != "" and r.upper() != "PENDING"]
            
            if sugg_region not in all_regions:
                all_regions.insert(0, sugg_region)
            else:
                all_regions.remove(sugg_region)
                all_regions.insert(0, sugg_region)
                
            all_regions.append("Autre région (saisir ci-dessous)")
            
            chosen_region_sel = st.selectbox("🌍 Sélectionner la région", all_regions)
            
            custom_region_txt = st.text_input("✍️ Ou saisir un nom de région personnalisé (si non présent dans la liste)")
            
            final_confirmed_region = custom_region_txt.strip() if (chosen_region_sel == "Autre région (saisir ci-dessous)" or custom_region_txt.strip() != "") else chosen_region_sel
            
            st.markdown(f"Région finale qui sera enregistrée : **`{final_confirmed_region}`**")
            
            # Bouton de validation
            if st.button("Confirmer la région et lancer l'intégration Airflow", type="primary"):
                if final_confirmed_region.strip() == "":
                    st.error("Veuillez spécifier une région valide.")
                else:
                    with st.spinner("⏳ Enregistrement de la région..."):
                        # Mettre à jour l'index
                        df_idx.loc[df_idx["ID"] == chosen_id, "Region"] = final_confirmed_region
                        df_idx.to_csv("index.csv", index=False)
                        
                    with st.spinner("🚀 Déclenchement de la tâche d'intégration dans Airflow..."):
                        # Déclenchement
                        import json
                        import subprocess
                        import time
                        conf_json = json.dumps({"dataset_id": str(chosen_id)})
                        triggered = False
                        msg = ""
                        
                        # 1. Essai direct (CLI locale)
                        try:
                            cmd = ["airflow", "dags", "trigger", "seamap_sync_pipeline", "-c", conf_json]
                            res = subprocess.run(cmd, capture_output=True, text=True)
                            if res.returncode == 0:
                                triggered = True
                                msg = res.stdout
                        except Exception as e:
                            msg = str(e)
                            
                        # 2. Essai avec "docker compose"
                        if not triggered:
                            try:
                                cmd = ["docker", "compose", "exec", "-T", "airflow-webserver", "airflow", "dags", "trigger", "seamap_sync_pipeline", "-c", conf_json]
                                res = subprocess.run(cmd, capture_output=True, text=True)
                                if res.returncode == 0:
                                    triggered = True
                                    msg = res.stdout
                            except Exception as e:
                                msg = str(e)
                                
                        # 3. Essai avec "docker-compose"
                        if not triggered:
                            try:
                                cmd = ["docker-compose", "exec", "-T", "airflow-webserver", "airflow", "dags", "trigger", "seamap_sync_pipeline", "-c", conf_json]
                                res = subprocess.run(cmd, capture_output=True, text=True)
                                if res.returncode == 0:
                                    triggered = True
                                    msg = res.stdout
                            except Exception as e:
                                msg = str(e)
                                
                        if triggered:
                            st.success(f"✅ Région '{final_confirmed_region}' enregistrée et validée pour le dataset {chosen_id} !")
                            st.info("🚀 Le pipeline Airflow a été lancé immédiatement en arrière-plan pour télécharger et intégrer les données.")
                        else:
                            st.warning(f"Région enregistrée localement dans index.csv, mais impossible de déclencher Airflow automatiquement : {msg}")
                            st.info("Vous pouvez lancer manuellement le DAG 'seamap_sync_pipeline' depuis la console Airflow.")
                            
                        # Vider le cache et rafraîchir
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style='text-align:center;color:#4A7A9E;font-size:0.8rem;padding:1rem;
border-top:1px solid rgba(0,212,255,0.1);'>
    🐋 SEAMAP · Observatoire des Cétacés &nbsp;|&nbsp;
    <strong>{total_lignes:,} observations</strong> &nbsp;|&nbsp;
    Streamlit + Plotly + Folium
</div>
""", unsafe_allow_html=True)
