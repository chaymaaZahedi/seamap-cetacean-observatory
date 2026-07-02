from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import zipfile
import shutil

# --- CONFIGURATION ---
INDEX_PATH = "/opt/airflow/index.csv"
DATA_SOURCE_DIR = "/opt/airflow/data_source"
SCRIPTS_DIR = "/opt/airflow/scripts"
TEMP_DIR = "/tmp/seamap_downloads"

default_args = {
    'owner': 'seamap',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def extract_meta_field(soup, label):
    """ Extrait une valeur par son nom exact (sans Regex) """
    # Recherche du TD contenant exactement le texte du label
    node = soup.find("td", string=label)
    if node:
        sibling = node.find_next_sibling("td")
        if sibling:
            return sibling.get_text(strip=True)
    return ""

def check_for_updates(**kwargs):
    """ Scrape SEAMAP avec noms d'éléments exacts et support de déclenchement ciblé """
    dag_run = kwargs.get('dag_run')
    conf = dag_run.conf if dag_run else {}
    target_dataset_id = conf.get('dataset_id')

    if target_dataset_id:
        target_dataset_id = str(target_dataset_id).strip()
        log_msg = f"Déclenchement ciblé pour le dataset {target_dataset_id}"
        print(log_msg)
        if os.path.exists(INDEX_PATH):
            df_full = pd.read_csv(INDEX_PATH, dtype=str)
            df_full.columns = df_full.columns.str.strip()
            row = df_full[df_full['ID'].str.strip() == target_dataset_id]
            if not row.empty:
                item = row.iloc[0].to_dict()
                item = {k.strip(): str(v).strip() for k, v in item.items()}
                item['has_effort'] = (item.get('Effort', '').lower() == 'yes')
                item['ID'] = target_dataset_id
                kwargs['ti'].xcom_push(key='updates', value=[item])
                return [item]
        return []

    today = datetime.now()
    j_minus_4 = today - timedelta(days=4)
    
    if os.path.exists(INDEX_PATH):
        try:
            df_full = pd.read_csv(INDEX_PATH, dtype=str)
            df_full.columns = df_full.columns.str.strip()
            local_versions = dict(zip(df_full['ID'].str.strip(), df_full['Version'].str.strip()))
        except: local_versions = {}
    else: local_versions = {}

    # 1. Récupération des datasets en attente d'intégration (qui ont une région valide)
    gold_ds_path = "/opt/airflow/gold_data/dim_dataset.csv"
    integrated_ids = set()
    if os.path.exists(gold_ds_path):
        try:
            df_dim = pd.read_csv(gold_ds_path, dtype=str)
            integrated_ids = set(df_dim['index_id'].str.strip())
        except: pass

    updates_to_process = []

    if os.path.exists(INDEX_PATH):
        try:
            df_full = pd.read_csv(INDEX_PATH, dtype=str)
            df_full.columns = df_full.columns.str.strip()
            for _, row in df_full.iterrows():
                did = str(row['ID']).strip()
                region = str(row.get('Region', '')).strip()
                if did not in integrated_ids and region != '' and region.upper() != 'PENDING':
                    item = row.to_dict()
                    item = {k.strip(): str(v).strip() for k, v in item.items()}
                    item['has_effort'] = (item.get('Effort', '').lower() == 'yes')
                    item['ID'] = did
                    updates_to_process.append(item)
        except Exception as e:
            print(f"Erreur détection non intégrés: {e}")

    # 2. Scraping en ligne standard
    list_url = "https://seamap.env.duke.edu/dataset/list"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(list_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='listing')
        if table:
            rows = table.find_all('tr')
            for row in rows[:50]:
                if row.find('th'): continue
                cols = row.find_all('td')
                if len(cols) < 8: continue
                
                link = cols[2].find('a')
                if not link: continue
                dataset_id = link['href'].split('/')[-1].strip()
                
                last_updated_str = cols[7].get_text(strip=True)
                try:
                    last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d")
                except: continue

                if last_updated < j_minus_4: continue 

                meta_url = f"https://seamap.env.duke.edu/dataset/{dataset_id}/html"
                meta_resp = requests.get(meta_url, headers=headers, timeout=20)
                ms = BeautifulSoup(meta_resp.text, 'html.parser')
                
                # Mammifères
                mm_count = extract_meta_field(ms, "Marine mammals").replace(',', '') or "0"
                if int(mm_count) == 0: continue

                online_version = extract_meta_field(ms, "Version") or "1.0.0"

                if dataset_id not in local_versions or online_version != local_versions.get(dataset_id):
                    doi = extract_meta_field(ms, "DOI")
                    date_begin = extract_meta_field(ms, "Date, Begin")
                    date_end = extract_meta_field(ms, "Date, End")
                    effort_text = extract_meta_field(ms, "Effort").lower()
                    
                    # Noms exacts demandés
                    records = extract_meta_field(ms, "Records") or extract_meta_field(ms, "Total")
                    latitude = extract_meta_field(ms, "Latitude")
                    longitude = extract_meta_field(ms, "Longitude")

                    meta = {
                        'ID': dataset_id,
                        'ID Hyperlink': f"https://seamap.env.duke.edu/dataset/{dataset_id}/html",
                        'DOI': doi,
                        'DOI Hyperlink': f"https://doi.org/{doi}" if doi else "",
                        'Title': link.get_text(strip=True),
                        'Title Hyperlink': f"https://seamap.env.duke.edu/dataset/{dataset_id}",
                        'Provider': cols[3].get_text(strip=True),
                        'Data type': "ptphoto" if "ptphoto" in meta_resp.text.lower() else "ptobs",
                        'Platform': extract_meta_field(ms, "Platform"),
                        'Marine mammals': mm_count,
                        'Marine mammals - copy': mm_count,
                        'Dataset': f"obis_seamap_dataset_{dataset_id}_points.csv",
                        'Version': online_version,
                        'Date, Begin': date_begin,
                        'Date, End': date_end,
                        'Date range': f"{date_begin[:4]}-{date_end[:4]}" if len(date_begin) >= 4 and len(date_end) >= 4 else "",
                        'Records': records.replace(',', '') if records else "",
                        'Latitude': latitude,
                        'Longitude': longitude,
                        'Unnamed: 19': '',
                        'Effort': 'yes' if 'yes' in effort_text else 'No',
                        'Region': '', 
                        'has_effort': 'yes' in effort_text
                    }
                    updates_to_process.append(meta)
                    
                time.sleep(0.5)
    except Exception as e: print(f"Erreur scraping: {e}")

    kwargs['ti'].xcom_push(key='updates', value=updates_to_process)
    return updates_to_process

def download_and_extract(**kwargs):
    updates = kwargs['ti'].xcom_pull(key='updates', task_ids='check_for_updates')
    if not updates: return
    
    # Dossiers locaux
    loc_points = os.path.join(DATA_SOURCE_DIR, "data_sources_point")
    loc_tracks = os.path.join(DATA_SOURCE_DIR, "data_sources_survey_tracks")
    # Dossiers distants (montés via Docker)
    rem_root = "/opt/airflow/remote_data_source"
    rem_points = os.path.join(rem_root, "data_sources_point")
    rem_tracks = os.path.join(rem_root, "data_sources_survey_tracks")
    
    for d in [loc_points, loc_tracks, rem_points, rem_tracks, TEMP_DIR]:
        if not os.path.exists(d): os.makedirs(d)

    for item in updates:
        csv_url = f"https://seamap.env.duke.edu/downloads/datasets/dataset_{item['ID']}/obis_seamap_dataset_{item['ID']}_csv_v{item['Version']}.zip"
        # Download unique pour les deux
        zip_path = download_zip_only(csv_url, item['ID'], "points")
        if zip_path:
            extract_zip(zip_path, item['ID'], "points", [loc_points, rem_points])
            
        if item['has_effort']:
            gdb_url = f"http://seamap.env.duke.edu/downloads/datasets/dataset_{item['ID']}/obis_seamap_dataset_{item['ID']}_gdb_v{item['Version']}.zip"
            gdb_zip = download_zip_only(gdb_url, item['ID'], "gdb")
            if gdb_zip:
                extract_zip(gdb_zip, item['ID'], "gdb", [loc_tracks, rem_tracks])

def download_zip_only(url, ds_id, file_type):
    zip_path = os.path.join(TEMP_DIR, f"{ds_id}_{file_type}.zip")
    try:
        r = requests.get(url, stream=True, timeout=60)
        if r.status_code == 200:
            with open(zip_path, 'wb') as f: shutil.copyfileobj(r.raw, f)
            return zip_path
    except: pass
    return None

def extract_zip(zip_path, ds_id, file_type, dest_folders):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            if file_type == "points":
                for f in zip_ref.namelist():
                    if f.endswith('.csv') and 'points' in f.lower():
                        for dest in dest_folders:
                            with zip_ref.open(f) as src, open(os.path.join(dest, f"obis_seamap_dataset_{ds_id}_points.csv"), "wb") as tgt:
                                shutil.copyfileobj(src, tgt)
            else:
                for f in zip_ref.namelist():
                    if ".gdb/" in f:
                        for dest in dest_folders:
                            zip_ref.extract(f, dest)
    except Exception as e: print(f"Erreur extraction {ds_id}: {e}")

def update_index(**kwargs):
    updates = kwargs['ti'].xcom_pull(key='updates', task_ids='check_for_updates')
    if not updates: return
    df = pd.read_csv(INDEX_PATH, dtype=str)
    cols_order = df.columns.tolist()
    for ds_meta in updates:
        csv_row = {k: v for k, v in ds_meta.items() if k in cols_order}
        if str(csv_row['ID']) in df['ID'].values:
            for key, value in csv_row.items():
                df.loc[df['ID'] == str(csv_row['ID']), key] = value
        else:
            df = pd.concat([df, pd.DataFrame([csv_row])], ignore_index=True)
    df.to_csv(INDEX_PATH, index=False)

def decide_etl_branch(**kwargs):
    updates = kwargs['ti'].xcom_pull(key='updates', task_ids='check_for_updates')
    if not updates: return []
    return "run_spatial_etl" if updates[0]['Data type'] == "ptobs" else "run_temporal_etl"

# --- DAG ---
with DAG(
    'seamap_sync_pipeline',
    default_args=default_args,
    description='Pipeline SEAMAP (Noms exacts)',
    schedule_interval=None,
    catchup=False,
    tags=['seamap', 'exact_labels'],
) as dag:

    t1 = PythonOperator(task_id='check_for_updates', python_callable=check_for_updates)
    t2 = PythonOperator(task_id='download_and_extract', python_callable=download_and_extract)
    t3 = PythonOperator(task_id='update_index', python_callable=update_index)
    t4 = BranchPythonOperator(task_id='decide_etl', python_callable=decide_etl_branch)
    
    t5a = BashOperator(
        task_id='run_spatial_etl',
        bash_command='python3 /opt/airflow/scripts/ETL_spatial.py --dataset_id {{ ti.xcom_pull(task_ids="check_for_updates", key="updates")[0]["ID"] }}',
    )
    
    t5b = BashOperator(
        task_id='run_temporal_etl',
        bash_command='python3 /opt/airflow/scripts/ETL_temporal.py --dataset_id {{ ti.xcom_pull(task_ids="check_for_updates", key="updates")[0]["ID"] }}',
    )

    t1 >> t2 >> t3 >> t4
    t4 >> [t5a, t5b]
