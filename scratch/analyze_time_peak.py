import pandas as pd
import numpy as np

# Load index and viz_facts_clean
index_df = pd.read_csv("index.csv")
df = pd.read_csv("gold_data/viz_facts_clean.csv")

# Identify ptphoto / v5_temporel
# Let's inspect how agg_std is merged and filtered in main.py
# main.py does:
# agg_std = agg.merge(dim_dataset[["index_id", "traitement_type"]].drop_duplicates(), left_on="id_dataset_int", right_on="index_id", how="left")
# agg_temp = agg_std[agg_std["traitement_type"] == "v5_temporel"]

# Let's check columns in df
print("df columns:", df.columns.tolist())

# Let's find dataset dimensions
dim_dataset = pd.read_csv("gold_data/dim_dataset.csv")
print("dim_dataset columns:", dim_dataset.columns.tolist())
print("dim_dataset unique traitement_type:", dim_dataset["traitement_type"].unique())

# Perform the merge and calculation
# We need to use the gold facts/clean data to do this calculation.
# Let's check how main.py loads agg_all
# In main.py:
# dim_region, dim_espece, dim_date, dim_dataset = load_dimensions()
# agg_all, geo_all, kpis_total, id_maps = build_joined_agg()
# Let's see what data_loader.py has, or let's write the code to compute it directly from df (viz_facts_clean.csv).
# In viz_facts_clean.csv:
# index_id represents dataset ID, traitement_type is there, and columns are probably annee, group_size (or abondance), and nb_jours or date_time.
# Let's see what columns are in df:
# In previous outputs we saw:
# 'annee', 'index_id', 'source_type', 'traitement_type', 'nb_jours', 'abondance' etc.
# Let's do the calculation on df:

agg_temp = df[df["traitement_type"] == "v5_temporel"]
print("agg_temp shape:", agg_temp.shape)

# Let's calculate:
# pop_yr_time = (agg_temp.groupby("annee", as_index=False)
#                .agg(individus=("sum_group_size", "sum"), effort=("nb_jours", "sum")))
# Wait, let's see if the column names are sum_group_size or abondance or group_size
group_size_col = 'sum_group_size' if 'sum_group_size' in agg_temp.columns else ('group_size' if 'group_size' in agg_temp.columns else 'abondance')
effort_col = 'nb_jours' if 'nb_jours' in agg_temp.columns else 'effort'

# Let's calculate for each dataset and year
print(f"Using group size column: {group_size_col}, effort column: {effort_col}")

pop_yr_time = (agg_temp.groupby("annee", as_index=False)
               .agg(individus=(group_size_col, "sum"), effort=(effort_col, "sum")))

effort_moyen_time = pop_yr_time["effort"].mean()
pop_yr_time["pop_std"] = np.where(pop_yr_time["effort"] > 0, 
                                  (pop_yr_time["individus"] / pop_yr_time["effort"]) * effort_moyen_time, 0)

print("\nYearly stats for ptphoto (all years, sorted by year):")
print(pop_yr_time.to_string())

# Let's filter for years around 1970-1990
print("\nStats around 1970-1990:")
print(pop_yr_time[(pop_yr_time["annee"] >= 1970) & (pop_yr_time["annee"] <= 1990)].to_string())

# Which datasets contributed to the peak?
print("\nContribution of datasets for years 1977-1980:")
contrib = agg_temp[(agg_temp["annee"] >= 1977) & (agg_temp["annee"] <= 1980)].groupby(["annee", "index_id"]).agg(
    individus=(group_size_col, "sum"),
    effort=(effort_col, "sum")
).reset_index()

# Merge with index_df to get Titles
contrib = contrib.merge(index_df[["ID", "Title", "Provider"]], left_on="index_id", right_on="ID", how="left")
print(contrib.to_string())

# Let's also check the raw points for 1764 and 1765 to see if there is something weird.
# We can load the raw data for 1764 / 1765 or see what the counts are.
# In 1977: index_id 1764 and 1765.
# In 1978: index_id 1764.
# In 1979: index_id 1764 and 1765.
# Let's print this info out to a text file.
