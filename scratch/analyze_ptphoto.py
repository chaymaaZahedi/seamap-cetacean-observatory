import pandas as pd

# Load the viz facts data
df = pd.read_csv("gold_data/viz_facts_clean.csv")

print("Columns in viz_facts_clean.csv:")
print(df.columns.tolist())

# Print unique values in source_type or whatever type column represents 'ptphoto'
# Let's find columns related to type
type_cols = [c for c in df.columns if "type" in c or "traitement" in c]
print("\nType columns found:", type_cols)

for c in type_cols:
    print(f"Unique values in {c}:", df[c].unique() if c in df.columns else "N/A")

# Let's inspect the distribution of years and counts for photo-identification
# Based on previous compaction summary: "source_type == 'ptphoto'" or "traitement_type == 'v5_photo_id'"
# Let's filter and see.
if 'source_type' in df.columns:
    df_photo = df[df['source_type'] == 'ptphoto']
elif 'traitement_type' in df.columns:
    df_photo = df[df['traitement_type'] == 'v5_photo_id']
else:
    # Try finding the right subset dynamically
    df_photo = df[df.astype(str).apply(lambda x: x.str.contains('ptphoto|photo_id')).any(axis=1)]

print(f"\nNumber of records in df_photo: {len(df_photo)}")
if len(df_photo) > 0:
    print("Columns with non-null values in df_photo:")
    print(df_photo.dropna(how='all', axis=1).columns.tolist())
    
    # Group by year and count/sum abundance
    # Let's see what columns are in df_photo
    year_col = 'annee' if 'annee' in df_photo.columns else ('year' if 'year' in df_photo.columns else None)
    if not year_col:
        year_col = [c for c in df_photo.columns if 'year' in c or 'annee' in c][0]
    
    print(f"\nUsing year column: {year_col}")
    
    # Find abundance/count/population columns
    val_cols = [c for c in df_photo.columns if any(w in c.lower() for w in ['size', 'count', 'abundance', 'pop', 'ind', 'value', 'std'])]
    print("Potential value/population columns:", val_cols)
    
    # Summary of records around 1977
    around_1977 = df_photo[(df_photo[year_col] >= 1970) & (df_photo[year_col] <= 1985)]
    print("\nRecords around 1977:")
    print(around_1977.groupby(year_col).size().reset_index(name='count'))
    
    for val_col in val_cols:
        try:
            print(f"\nSum of {val_col} by year around 1977:")
            print(around_1977.groupby(year_col)[val_col].sum().reset_index())
        except Exception as e:
            print(f"Could not sum {val_col}: {e}")
            
    # Let's look at the actual records around 1977 to see what datasets they belong to
    dataset_cols = [c for c in df_photo.columns if 'dataset' in c or 'ds' in c or 'id' in c]
    print("\nDataset columns:", dataset_cols)
    
    for d_col in dataset_cols:
        if d_col in around_1977.columns:
            print(f"\nUnique values in {d_col} around 1977:")
            print(around_1977.groupby([year_col, d_col]).size().reset_index(name='count'))
            
            # Print details of the records in the peak year
            peak_years = around_1977[around_1977[year_col] == 1978] # post-1977 could be 1978 or so
            if len(peak_years) == 0:
                peak_years = around_1977[around_1977[year_col] == 1977]
            print(f"\nSample records for year {peak_years[year_col].iloc[0] if len(peak_years) > 0 else 'N/A'}:")
            print(peak_years.head(20))
