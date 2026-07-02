import pandas as pd

# Load viz_facts_clean.csv
df = pd.read_csv("gold_data/viz_facts_clean.csv", low_memory=False)

# Filter for dataset 1764 (Humpback whale in North Atlantic Ocean) and years 1977-1980
df_1764 = df[(df["index_id"] == 1764) & (df["annee"].isin([1977, 1978, 1979, 1980]))]

print("=== Date distribution for Dataset 1764 in 1977-1980 ===")
for year in [1977, 1978, 1979, 1980]:
    df_yr = df_1764[df_1764["annee"] == year]
    print(f"\nYear {year} (Total records: {len(df_yr)})")
    print(df_yr["date_time_str"].value_counts().head(10))
    print("Unique date_jour values:", df_yr["date_jour"].unique().tolist())
