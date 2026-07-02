import pandas as pd
import numpy as np

# Load data sources
df = pd.read_csv("gold_data/viz_facts_clean.csv", low_memory=False)
dim_dataset = pd.read_csv("gold_data/dim_dataset.csv")

# Replicate main.py and data_loader.py setup
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

# Merge with dim_dataset to get treatment_type
agg_std = joined.merge(dim_dataset[["index_id", "traitement_type"]].drop_duplicates(), left_on="id_dataset_int", right_on="index_id", how="left")

# 1. Calcul Temporel (v5_temporel)
agg_temp = agg_std[agg_std["traitement_type"] == "v5_temporel"]
pop_yr_time = (agg_temp.groupby("annee", as_index=False)
               .agg(individus=("sum_group_size", "sum"), effort=("nb_jours", "sum")))
effort_moyen_time = pop_yr_time["effort"].mean() if not pop_yr_time.empty else 0
pop_yr_time["pop_std"] = np.where(pop_yr_time["effort"] > 0, 
                                  (pop_yr_time["individus"] / pop_yr_time["effort"]) * effort_moyen_time, 0)

# Print stats by year
print("=== TEMPORAL STATS (PTPHOTO) BY YEAR ===")
print(pop_yr_time.to_string())

# Contribution of datasets for years around 1977
print("\n=== DATASET CONTRIBUTIONS AROUND 1977 (1975-1983) ===")
# We want to see how each dataset contributes to the total individuals and effort per year
contrib = agg_temp[(agg_temp["annee"] >= 1975) & (agg_temp["annee"] <= 1983)].groupby(["annee", "id_dataset_int"]).agg(
    individus=("sum_group_size", "sum"),
    effort=("nb_jours", "sum")
).reset_index()

index_df = pd.read_csv("index.csv")
contrib = contrib.merge(index_df[["ID", "Title", "Provider"]], left_on="id_dataset_int", right_on="ID", how="left")
print(contrib.to_string())

# Let's inspect the raw observations for the peak year to understand if group_size values are logic
print("\n=== RAW RECORDS FOR DATASETS IN 1977 AND 1978 ===")
raw_77_78 = df[(df["annee"].isin([1977, 1978])) & (df["index_id"].isin([1764, 1765]))]
print(f"Total raw records in 1977-1978 for 1764/1765: {len(raw_77_78)}")
print(raw_77_78.groupby(["annee", "index_id", "scientific_name", "abondance"]).size().reset_index(name="record_count").to_string())

# Let's print out what unique species and counts are observed
print("\n=== SPECIES DISTRIBUTION FOR 1978 ===")
print(df[df["annee"] == 1978].groupby("scientific_name").size().reset_index(name="count").to_string())

print("\n=== SPECIES DISTRIBUTION FOR 1979 ===")
print(df[df["annee"] == 1979].groupby("scientific_name").size().reset_index(name="count").to_string())
