# import requests
# from bs4 import BeautifulSoup

# url = "https://seamap.env.duke.edu/dataset/2371/html"

# response = requests.get(url)
# response.raise_for_status()

# soup = BeautifulSoup(response.text, "html.parser")

# # 1️⃣ metadata-main
# metadata_div = soup.find("div", class_="metadata-main")

# if not metadata_div:
#     print("metadata-main introuvable")
#     exit()

# # 2️⃣ Table principale
# main_table = metadata_div.find("table")

# # 3️⃣ Les deux colonnes principales
# columns = main_table.find("tr").find_all("td", recursive=False)

# left_column = columns[0]   # partie metadata (Dataset credit, Abstract, etc.)
# right_column = columns[1]  # summary_box

# # ==========================
# # 🔹 EXTRACTION PARTIE GAUCHE
# # ==========================

# inner_table = left_column.find("table")

# rows = inner_table.find_all("tr", recursive=False)

# print("Sections trouvées :")
# for row in rows:
#     h3 = row.find("h3")
#     if h3:
#         print("-", h3.get_text(strip=True))

# # Exemple : récupérer Abstract
# for row in rows:
#     h3 = row.find("h3")
#     if h3 and h3.get_text(strip=True) == "Abstract":
#         description = row.find("div", class_="description")
#         print("\nAbstract :", description.get_text(strip=True))

# # ==========================
# # 🔹 EXTRACTION SUMMARY BOX
# # ==========================

# summary_table = right_column.find("table")

# summary_rows = summary_table.find_all("tr")

# for row in summary_rows:
#     cols = row.find_all("td")
#     if len(cols) == 2:
#         key = cols[0].get_text(strip=True)
#         value = cols[1].get_text(strip=True)

#         if key == "Date, Begin":
#             print("Date Begin :", value)
#         if key == "Total":
#             print("Total :", value)

#         if key == "Date, End":
#             print("Date, End :", value)

# ======================================================================================================================================        
# import requests
# import pandas as pd
# from bs4 import BeautifulSoup
# import time

# def extract_dataset_info(dataset_id):
#     url = f"https://seamap.env.duke.edu/dataset/{dataset_id}/html"

#     headers = {
#         "User-Agent": "Mozilla/5.0"
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=15)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         print(f"Erreur pour ID {dataset_id} : {e}")
#         return None, None, None

#     soup = BeautifulSoup(response.text, "html.parser")

#     # ✅ On cherche metadata-main (et NON tab_information)
#     metadata_div = soup.find("div", class_="metadata-main")

#     if not metadata_div:
#         print(f"metadata-main introuvable pour ID {dataset_id}")
#         return None, None, None

#     main_table = metadata_div.find("table")
#     columns = main_table.find("tr").find_all("td", recursive=False)

#     if len(columns) < 2:
#         print(f"Colonnes non trouvées pour ID {dataset_id}")
#         return None, None, None

#     right_column = columns[1]  # summary_box
#     summary_table = right_column.find("table")
#     summary_rows = summary_table.find_all("tr")

#     date_begin = None
#     date_end = None
#     total_records = None

#     for row in summary_rows:
#         cols = row.find_all("td")
#         if len(cols) == 2:
#             key = cols[0].get_text(strip=True)
#             value = cols[1].get_text(strip=True)

#             if key == "Date, Begin":
#                 date_begin = value
#             elif key == "Date, End":
#                 date_end = value
#             elif key == "Total":
#                 total_records = value

#     return date_begin, date_end, total_records


# # ================= MAIN =================

# file_path = "All_seamap_ID_Dataset_whal.xlsx"
# df = pd.read_excel(file_path)

# for index, row in df.iterrows():
#     dataset_id = row["ID"]

#     if pd.isna(dataset_id):
#         continue

#     print(f"Traitement ID: {dataset_id}")

#     date_begin, date_end, total = extract_dataset_info(dataset_id)

#     df.at[index, "Date, Begin"] = date_begin
#     df.at[index, "Date, End"] = date_end
#     df.at[index, "Records"] = total

#     time.sleep(1)

# df.to_excel("datasets_updated.xlsx", index=False)

# print("Terminé ✅")

# ======================================================================================================================================

# import requests
# import pandas as pd
# from bs4 import BeautifulSoup
# import time

# def extract_lat_lon(dataset_id):
#     url = f"https://seamap.env.duke.edu/dataset/{dataset_id}/html"

#     headers = {
#         "User-Agent": "Mozilla/5.0"
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=15)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         print(f"Erreur pour ID {dataset_id} : {e}")
#         return None, None

#     soup = BeautifulSoup(response.text, "html.parser")

#     metadata_div = soup.find("div", class_="metadata-main")
#     if not metadata_div:
#         print(f"metadata-main introuvable pour ID {dataset_id}")
#         return None, None

#     main_table = metadata_div.find("table")
#     columns = main_table.find("tr").find_all("td", recursive=False)

#     if len(columns) < 2:
#         return None, None

#     right_column = columns[1]
#     summary_table = right_column.find("table")
#     summary_rows = summary_table.find_all("tr")

#     latitude = None
#     longitude = None

#     for row in summary_rows:
#         cols = row.find_all("td")
#         if len(cols) == 2:
#             key = cols[0].get_text(strip=True)
#             value = cols[1].get_text(strip=True)

#             if key == "Latitude":
#                 latitude = value
#             elif key == "Longitude":
#                 longitude = value

#     return latitude, longitude


# # ================= MAIN =================

# file_path = "All_seamap_ID_Dataset_whal.xlsx"
# df = pd.read_excel(file_path)

# # Créer les colonnes si elles n'existent pas
# if "Latitude" not in df.columns:
#     df["Latitude"] = None

# if "Longitude" not in df.columns:
#     df["Longitude"] = None

# for index, row in df.iterrows():
#     dataset_id = row["ID"]

#     if pd.isna(dataset_id):
#         continue

#     print(f"Traitement ID: {dataset_id}")

#     lat, lon = extract_lat_lon(dataset_id)

#     df.at[index, "Latitude"] = lat
#     df.at[index, "Longitude"] = lon

#     time.sleep(1)

# df.to_excel("datasets_updated.xlsx", index=False)

# print("Terminé ✅")

# ===============================================================================================

# import requests
# import pandas as pd
# from bs4 import BeautifulSoup
# import time

# def extract_species_counts(dataset_id):
#     url = f"https://seamap.env.duke.edu/dataset/{dataset_id}/html"

#     headers = {
#         "User-Agent": "Mozilla/5.0"
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=15)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         print(f"Erreur pour ID {dataset_id} : {e}")
#         return None

#     soup = BeautifulSoup(response.text, "html.parser")

#     metadata_div = soup.find("div", class_="metadata-main")
#     if not metadata_div:
#         print(f"metadata-main introuvable pour ID {dataset_id}")
#         return None

#     main_table = metadata_div.find("table")
#     columns = main_table.find("tr").find_all("td", recursive=False)

#     if len(columns) < 2:
#         return None

#     right_column = columns[1]
#     summary_table = right_column.find("table")
#     summary_rows = summary_table.find_all("tr")

#     # Initialiser dictionnaire des catégories
#     categories = {
#         "Seabirds": None,
#         "Marine mammals": None,
#         "Sea turtles": None,
#         "Rays and sharks": None,
#         "Other species": None,
#         "Non spatial": None,
#         "Non species": None
#     }

#     for row in summary_rows:
#         cols = row.find_all("td")
#         if len(cols) == 2:
#             key = cols[0].get_text(strip=True)
#             value = cols[1].get_text(strip=True)

#             if key in categories:
#                 categories[key] = value

#     return categories


# # ================= MAIN =================

# file_path = "All_seamap_ID_Dataset_whal.xlsx"
# df = pd.read_excel(file_path)

# # 🔹 Créer colonnes si inexistantes
# species_columns = [
#     "Seabirds",
#     "Marine mammals",
#     "Sea turtles",
#     "Rays and sharks",
#     "Other species",
#     "Non spatial",
#     "Non species"
# ]

# for col in species_columns:
#     if col not in df.columns:
#         df[col] = None


# for index, row in df.iterrows():
#     dataset_id = row["ID"]

#     if pd.isna(dataset_id):
#         continue

#     print(f"Traitement ID: {dataset_id}")

#     species_data = extract_species_counts(dataset_id)

#     if species_data:
#         for col in species_columns:
#             df.at[index, col] = species_data[col]

#     # 💾 Sauvegarde après chaque ID
#     df.to_excel("datasets_updated.xlsx", index=False)

#     time.sleep(1)

# print("Terminé ✅")

#====================================================================================================
# import requests
# import pandas as pd
# from bs4 import BeautifulSoup
# import time

# def extract_dataset_info(dataset_id):
#     url = f"https://seamap.env.duke.edu/dataset/{dataset_id}/html"

#     headers = {
#         "User-Agent": "Mozilla/5.0"
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=15)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         print(f"Erreur pour ID {dataset_id} : {e}")
#         return None

#     soup = BeautifulSoup(response.text, "html.parser")

#     metadata_div = soup.find("div", class_="metadata-main")
#     if not metadata_div:
#         print(f"metadata-main introuvable pour ID {dataset_id}")
#         return None

#     main_table = metadata_div.find("table")
#     columns = main_table.find("tr").find_all("td", recursive=False)

#     if len(columns) < 2:
#         return None

#     right_column = columns[1]
#     summary_table = right_column.find("table")
#     summary_rows = summary_table.find_all("tr")

#     # 🔹 Initialiser dictionnaire
#     data = {
#         "Date, Begin": None,
#         "Date, End": None,
#         "Records": None,
#         "Latitude": None,
#         "Longitude": None
#     }

#     for row in summary_rows:
#         cols = row.find_all("td")
#         if len(cols) == 2:
#             key = cols[0].get_text(strip=True)
#             value = cols[1].get_text(strip=True)

#             if key == "Date, Begin":
#                 data["Date, Begin"] = value
#             elif key == "Date, End":
#                 data["Date, End"] = value
#             elif key == "Total":
#                 data["Records"] = value
#             elif key == "Latitude":
#                 data["Latitude"] = value
#             elif key == "Longitude":
#                 data["Longitude"] = value

#     return data


# # ================= MAIN =================

# file_path = "All_seamap_ID_Dataset_whal.xlsx"
# df = pd.read_excel(file_path)

# # 🔹 Créer colonnes si inexistantes
# needed_columns = [
#     "Date, Begin",
#     "Date, End",
#     "Records",
#     "Latitude",
#     "Longitude"
# ]

# for col in needed_columns:
#     if col not in df.columns:
#         df[col] = None


# for index, row in df.iterrows():
#     dataset_id = row["ID"]

#     if pd.isna(dataset_id):
#         continue

#     print(f"Traitement ID: {dataset_id}")

#     dataset_data = extract_dataset_info(dataset_id)

#     if dataset_data:
#         for col in needed_columns:
#             df.at[index, col] = dataset_data[col]

#     # 💾 Sauvegarde après chaque ID
#     df.to_excel("datasets_updated.xlsx", index=False)

#     time.sleep(1)

# print("Terminé ✅")

# =========================================================
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

def extract_dataset_version(dataset_id):
    url = f"https://seamap.env.duke.edu/dataset/{dataset_id}/html"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Erreur pour ID {dataset_id} : {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # On cherche directement la cellule (td) qui contient exactement le mot "Version"
    version_label = soup.find("td", string=lambda t: t and "Version" in t)
    
    if version_label:
        # La valeur de la version est dans la cellule (td) suivante
        version_value_td = version_label.find_next_sibling("td")
        if version_value_td:
            version = version_value_td.get_text(strip=True)
            # Nettoyage si besoin (certaines versions ont des espaces ou du texte inutile)
            return version

    return "Non trouvée"

# ================= MAIN =================

file_path = "All_seamap_ID_Dataset_whale.xlsx"
df = pd.read_excel(file_path)

if "Version" not in df.columns:
    df["Version"] = None

for index, row in df.iterrows():
    dataset_id = row["ID"]
    if pd.isna(dataset_id): continue

    # On ne traite que si la version est vide
    if pd.isna(df.at[index, "Version"]) or df.at[index, "Version"] == "":
        print(f"Extraction Version pour ID: {dataset_id}")
        version = extract_dataset_version(dataset_id)
        
        if version:
            df.at[index, "Version"] = version
            print(f"-> Version trouvée : {version}")
        
        # Sauvegarde toutes les 5 itérations pour plus de rapidité (ou à chaque fois si vous préférez)
        df.to_excel("datasets_with_version.xlsx", index=False)
        time.sleep(1)

print("Terminé ✅")