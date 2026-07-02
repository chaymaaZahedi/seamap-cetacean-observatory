import pandas as pd
import re

# Set output file
output_file = "scratch/ptphoto_analysis_output.txt"

with open(output_file, "w", encoding="utf-8") as out:
    # Load index.csv
    index_df = pd.read_csv("index.csv")
    
    # Load viz_facts_clean.csv
    df = pd.read_csv("gold_data/viz_facts_clean.csv")
    
    # Find ptphoto datasets
    ptphoto_df = df[df['source_type'] == 'ptphoto'] if 'source_type' in df.columns else df[df['traitement_type'] == 'v5_photo_id']
    
    out.write(f"Total ptphoto records: {len(ptphoto_df)}\n\n")
    
    # Inspect dataset details
    unique_ids = ptphoto_df['index_id'].unique()
    out.write(f"Unique ptphoto dataset IDs: {list(unique_ids)}\n\n")
    
    matched_index = index_df[index_df['ID'].isin(unique_ids)]
    out.write("Matched datasets details:\n")
    out.write(matched_index[['ID', 'Title', 'Provider', 'Data type', 'Date, Begin', 'Date, End']].to_string())
    out.write("\n\n")
    
    # Check the data for 1764 and 1765
    out.write("Specific details on dataset 1764:\n")
    ds1764 = index_df[index_df['ID'] == 1764]
    out.write(ds1764.to_string())
    out.write("\n\n")
    
    out.write("Specific details on dataset 1765:\n")
    ds1765 = index_df[index_df['ID'] == 1765]
    out.write(ds1765.to_string())
    out.write("\n\n")
    
    # Year distribution for ptphoto
    out.write("Records by year for ptphoto (all years):\n")
    yearly_records = ptphoto_df.groupby('annee').size().reset_index(name='count')
    out.write(yearly_records.to_string())
    out.write("\n\n")
    
    # Check what columns exist in ptphoto_df and their descriptions/sums
    out.write("Sample ptphoto records around 1978:\n")
    sample_df = ptphoto_df[ptphoto_df['annee'] == 1978].head(10)
    out.write(sample_df.to_string())
    out.write("\n\n")
    
    # Find ptphoto section in main.py
    with open("main.py", "r", encoding="utf-8") as f:
        main_content = f.read()
        
    out.write("=== MAIN.PY SEARCH FOR PTPHOTO ===\n")
    # Let's extract lines that mention ptphoto
    lines = main_content.splitlines()
    for idx, line in enumerate(lines):
        if "ptphoto" in line.lower() or "photo" in line.lower() or "v5_photo_id" in line.lower():
            out.write(f"Line {idx+1}: {line}\n")
            
    # Also find where the graph is defined. Let's find "photo" and get a window of lines around it
    out.write("\n=== BLOCKS IN MAIN.PY RELEVANT TO PHOTO GRAPH ===\n")
    matches = [i for i, line in enumerate(lines) if "photo" in line.lower() or "ptphoto" in line.lower()]
    # Group contiguous line numbers to show contexts
    if matches:
        # Show blocks of lines
        current_block = [matches[0]]
        for m in matches[1:]:
            if m - current_block[-1] <= 15:
                current_block.append(m)
            else:
                # print block
                start = max(0, current_block[0] - 5)
                end = min(len(lines), current_block[-1] + 10)
                out.write(f"\n--- Line {start+1} to {end} ---\n")
                out.write("\n".join(lines[start:end]))
                out.write("\n")
                current_block = [m]
        start = max(0, current_block[0] - 5)
        end = min(len(lines), current_block[-1] + 10)
        out.write(f"\n--- Line {start+1} to {end} ---\n")
        out.write("\n".join(lines[start:end]))
        out.write("\n")

print("Done! Output written to scratch/ptphoto_analysis_output.txt")
