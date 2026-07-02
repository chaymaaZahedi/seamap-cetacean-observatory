import pandas as pd
from pathlib import Path

# Load index to get list of files
df_idx = pd.read_csv('index.csv')
df_idx.columns = df_idx.columns.str.strip()

# Path to point data
points_dir = Path('c:/MyPc/master/s4/stage-ird/dataset/baleine-seamap/data_source/data_sources_point')
if not points_dir.exists():
    points_dir = Path('data_source/data_sources_point')

print('Searching for overlaps among datasets in:', points_dir)
datasets = {}
for idx, row in df_idx.iterrows():
    ds_id = str(row['ID']).strip()
    filename = str(row['Dataset']).strip()
    filepath = points_dir / filename
    if filepath.exists():
        try:
            # Read only required columns to save memory
            df = pd.read_csv(filepath, usecols=['date_time', 'latitude', 'longitude', 'scientific_name'], low_memory=False)
            df = df.dropna(subset=['date_time', 'latitude', 'longitude'])
            # Create a set of (date_time, round(lat, 4), round(lon, 4), scientific_name)
            points = set()
            for r in df.itertuples():
                try:
                    lat_r = round(float(r.latitude), 4)
                    lon_r = round(float(r.longitude), 4)
                    points.add((str(r.date_time).strip(), lat_r, lon_r, str(r.scientific_name).strip().lower()))
                except Exception:
                    continue
            if points:
                datasets[ds_id] = {
                    'title': row['Title'],
                    'points': points,
                    'file': filename
                }
        except Exception as e:
            pass

print(f'Loaded {len(datasets)} datasets with observations.')

# Compare pairs for overlap
overlaps = []
ds_ids = list(datasets.keys())
for i in range(len(ds_ids)):
    for j in range(i + 1, len(ds_ids)):
        id1, id2 = ds_ids[i], ds_ids[j]
        set1 = datasets[id1]['points']
        set2 = datasets[id2]['points']
        intersection = set1.intersection(set2)
        if len(intersection) > 0:
            pct1 = len(intersection) / len(set1) * 100
            pct2 = len(intersection) / len(set2) * 100
            overlaps.append((id1, id2, len(intersection), pct1, pct2))

if overlaps:
    overlaps = sorted(overlaps, key=lambda x: x[2], reverse=True)
    print('\nFound overlaps:')
    for id1, id2, count, pct1, pct2 in overlaps[:30]:
        t1 = datasets[id1]['title'][:40]
        t2 = datasets[id2]['title'][:40]
        print(f'- Dataset {id1} ({t1}) & Dataset {id2} ({t2}):')
        print(f'  Overlap count: {count} points ({pct1:.1f}% of D1, {pct2:.1f}% of D2)')
else:
    print('\nNo coordinate/datetime overlaps found between any pair of datasets!')
