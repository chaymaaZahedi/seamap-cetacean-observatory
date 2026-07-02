import pandas as pd
import re

# Load the index
index_df = pd.read_csv("index.csv")
print("Columns in index.csv:")
print(index_df.columns.tolist())

# Load viz_facts_clean.csv
df = pd.read_csv("gold_data/viz_facts_clean.csv")

# Find ptphoto/photo_id datasets
ptphoto_df = df[df['source_type'] == 'ptphoto'] if 'source_type' in df.columns else df[df['traitement_type'] == 'v5_photo_id']

print(f"Number of ptphoto records: {len(ptphoto_df)}")

# Find matching id column in index.csv (e.g. 'ID')
id_col_index = 'ID'

# Unique dataset IDs in ptphoto
unique_dataset_ids = ptphoto_df['index_id'].unique()
print("Unique dataset IDs in ptphoto:", len(unique_dataset_ids))

# Display dataset details from index_df
matched_index = index_df[index_df[id_col_index].isin(unique_dataset_ids)]
print("\nMatched datasets in index.csv:")
print(matched_index[[id_col_index, 'Title', 'Data type']].head(20).to_string())

# Group by year and dataset_id to see counts of records
year_dataset_counts = ptphoto_df.groupby(['annee', 'index_id']).size().reset_index(name='record_count')
print("\nRecord counts by year and dataset ID (1970-1990):")
print(year_dataset_counts[(year_dataset_counts['annee'] >= 1970) & (year_dataset_counts['annee'] <= 1990)].to_string())

# Group by year and calculate sum/avg of group_size or individual_count
abundance_cols = [c for c in ptphoto_df.columns if any(w in c.lower() for w in ['size', 'count', 'abundance', 'pop', 'ind', 'value', 'std'])]
print("\nAbundance-related columns in data:", abundance_cols)

for c in abundance_cols:
    grouped = ptphoto_df.groupby('annee')[c].agg(['sum', 'count', 'mean']).reset_index()
    print(f"\nStats for {c} by year (1970-1990):")
    print(grouped[(grouped['annee'] >= 1970) & (grouped['annee'] <= 1990)].to_string())

# Let's see what main.py does for 'ptphoto'
with open("main.py", "r", encoding="utf-8") as f:
    main_content = f.read()

# Look for 'ptphoto' or 'photo_id' or 'Photo-Identification'
matches = re.findall(r'.{0,100}ptphoto.{0,100}', main_content, re.IGNORECASE)
print("\nMatches for 'ptphoto' in main.py:")
for m in matches[:10]:
    print("- ", m.strip())

matches_photo = re.findall(r'.{0,100}photo_id.{0,100}', main_content, re.IGNORECASE)
print("\nMatches for 'photo_id' in main.py:")
for m in matches_photo[:10]:
    print("- ", m.strip())

# Find the section plotting this
chart_sections = []
for line in main_content.splitlines():
    if "photo" in line.lower() or "ptphoto" in line.lower():
        chart_sections.append(line)
print("\nLines in main.py containing 'photo' or 'ptphoto' (first 20 lines):")
for line in chart_sections[:20]:
    print(line)
