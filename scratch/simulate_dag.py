import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def simulate_check():
    today = datetime.now()
    j_minus_4 = today - timedelta(days=4)
    print(f"DEBUG: J-4 est {j_minus_4.strftime('%Y-%m-%d')}")
    
    list_url = "https://seamap.env.duke.edu/dataset/list"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(list_url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', class_='listing')
    rows = table.find_all('tr')
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 8: continue
        
        link = cols[2].find('a')
        if not link: continue
        dataset_id = link['href'].split('/')[-1].strip()
        
        if dataset_id == "2403":
            last_updated_str = cols[7].get_text(strip=True)
            last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d")
            
            print(f"Trouvé 2403 ! Date: {last_updated_str}")
            if last_updated < j_minus_4:
                print("ECHEC: Trop vieux")
                return
            
            # Check Mammifères
            meta_url = f"https://seamap.env.duke.edu/dataset/{dataset_id}/html"
            meta_resp = requests.get(meta_url, headers=headers)
            ms = BeautifulSoup(meta_resp.text, 'html.parser')
            
            # Recherche précise du label
            mm_label = ms.find("td", string=lambda t: t and "Marine mammals" in t)
            if not mm_label:
                print("ECHEC: Label 'Marine mammals' non trouvé sur la page HTML")
                return
            
            mm_count_str = mm_label.find_next_sibling("td").get_text(strip=True).replace(',', '')
            mm_count = int(mm_count_str)
            print(f"Compteur Mammifères: {mm_count}")
            
            if mm_count == 0:
                print("ECHEC: Compteur est à 0")
                return
            
            print("SUCCÈS: Le dataset 2403 devrait être téléchargé !")

if __name__ == "__main__":
    simulate_check()
