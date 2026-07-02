import pandas as pd
from pathlib import Path

# Load index
df_idx = pd.read_csv('index.csv')
df_idx.columns = df_idx.columns.str.strip()

# Path resolver
local_dir = Path('data_source/data_sources_point')
remote_dir = Path('c:/MyPc/master/s4/stage-ird/dataset/baleine-seamap/data_source/data_sources_point')

anomalies = []

# Whales list
whales = {
    'megaptera novaeangliae', 'balaenoptera physalus', 'balaenoptera musculus',
    'balaenoptera acutorostrata', 'balaenoptera bonaerensis', 'balaenoptera borealis',
    'balaenoptera edeni', 'physeter macrocephalus', 'eubalaena glacialis',
    'eubalaena australis', 'eubalaena japonica', 'balaena mysticetus',
    'eschrichtius robustus'
}

for idx, row in df_idx.iterrows():
    ds_id = str(row['ID']).strip()
    fn = str(row['Dataset']).strip()
    title = str(row['Title']).strip()
    path = local_dir / fn
    if not path.exists():
        path = remote_dir / fn
    if not path.exists():
        continue
        
    try:
        df = pd.read_csv(path, low_memory=False)
        df.columns = df.columns.str.strip().str.lower()
        
        # Check column name for group size
        gs_col = 'group_size' if 'group_size' in df.columns else None
        ic_col = 'individual_count' if 'individual_count' in df.columns else None
        
        # We will check whichever is present
        for col in [gs_col, ic_col]:
            if col is None:
                continue
            
            # Convert to numeric
            s = pd.to_numeric(df[col], errors='coerce')
            
            # 1. Negative values
            neg = df[s < 0]
            for _, r in neg.iterrows():
                anomalies.append({
                    'Dataset ID': ds_id,
                    'Dataset Name': title,
                    'File': fn,
                    'Date Time': r.get('date_time', 'N/A'),
                    'Scientific Name': r.get('scientific_name', 'N/A'),
                    'Common Name': r.get('common_name', 'N/A'),
                    'Field': col,
                    'Value': r[col],
                    'Reason': 'Valeur negative (Generalement un placeholder ou code erreur dans la base source).'
                })
                
            # 2. Large values
            large_rows = df[s >= 50]
            for _, r in large_rows.iterrows():
                sp = str(r.get('scientific_name', 'N/A')).strip().lower()
                val = float(r[col])
                
                # Check for large whales (> 50 is a clear anomaly)
                if any(w in sp for w in whales) and val >= 50:
                    anomalies.append({
                        'Dataset ID': ds_id,
                        'Dataset Name': title,
                        'File': fn,
                        'Date Time': r.get('date_time', 'N/A'),
                        'Scientific Name': r.get('scientific_name', 'N/A'),
                        'Common Name': r.get('common_name', 'N/A'),
                        'Field': col,
                        'Value': val,
                        'Reason': f'Effectif irrealiste pour cette espece de grand cetace (group_size >= 50).'
                    })
                # Check for polar bears (> 5 is suspicious)
                elif 'ursus' in sp and val > 10:
                    anomalies.append({
                        'Dataset ID': ds_id,
                        'Dataset Name': title,
                        'File': fn,
                        'Date Time': r.get('date_time', 'N/A'),
                        'Scientific Name': r.get('scientific_name', 'N/A'),
                        'Common Name': r.get('common_name', 'N/A'),
                        'Field': col,
                        'Value': val,
                        'Reason': f'Effectif irrealiste pour un ours polaire (solitaire).'
                    })
                # Flag any species with group size >= 3000
                elif val >= 3000:
                    reason = f'Effectif extremement eleve ({val}).'
                    if 'delphinus' in sp or 'stenella' in sp:
                        reason = f'Super-groupe de dauphins exceptionnellement grand ({val} individus).'
                    elif 'charadrii' in sp or 'branta' in sp or 'puffinus' in sp:
                        if int(val) == 9999:
                            reason = 'Code 9999 (Generalement un placeholder de donnees manquantes ou inestimables).'
                        else:
                            reason = f'Effectif extremement eleve pour des oiseaux ({val} individus).'
                    anomalies.append({
                        'Dataset ID': ds_id,
                        'Dataset Name': title,
                        'File': fn,
                        'Date Time': r.get('date_time', 'N/A'),
                        'Scientific Name': r.get('scientific_name', 'N/A'),
                        'Common Name': r.get('common_name', 'N/A'),
                        'Field': col,
                        'Value': val,
                        'Reason': reason
                    })
    except Exception as e:
        pass

# Sort anomalies by Dataset ID then Date Time
anomalies = sorted(anomalies, key=lambda x: (x['Dataset ID'], str(x['Date Time'])))

output_file = Path('anomalies_group_size.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('================================================================================\n')
    f.write('                     RAPPORT DES ANOMALIES DE TAILLE DE GROUPE                  \n')
    f.write('================================================================================\n')
    f.write(f'Nombre total d\'anomalies detectees : {len(anomalies)}\n\n')
    
    for idx, a in enumerate(anomalies, 1):
        f.write(f'Anomaly #{idx}\n')
        f.write(f'--------------------------------------------------------------------------------\n')
        f.write(f'  Dataset ID      : {a["Dataset ID"]}\n')
        f.write(f'  Dataset Name    : {a["Dataset Name"]}\n')
        f.write(f'  File            : {a["File"]}\n')
        f.write(f'  Date Time       : {a["Date Time"]}\n')
        f.write(f'  Scientific Name : {a["Scientific Name"]}\n')
        f.write(f'  Common Name     : {a["Common Name"]}\n')
        f.write(f'  Field/Column    : {a["Field"]}\n')
        f.write(f'  Value           : {a["Value"]}\n')
        f.write(f'  Reason/Type     : {a["Reason"]}\n')
        f.write('\n')

print(f'Rapport genere avec succes dans: {output_file.absolute()}')
