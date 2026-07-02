import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def debug_seamap_list():
    list_url = "https://seamap.env.duke.edu/dataset/list"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print(f"--- DIAGNOSTIC SEAMAP LIST ({datetime.now()}) ---")
    try:
        response = requests.get(list_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='listing')
        
        if not table:
            print("ERREUR : Table '.listing' non trouvée")
            return

        rows = table.find_all('tr')
        print(f"Total lignes : {len(rows)}")
        
        # On inspecte les 5 premières lignes de données
        count = 0
        for row in rows:
            if row.find('th'): continue
            cols = row.find_all('td')
            print(f"\nLIGNE {count+1}:")
            for i, c in enumerate(cols):
                text = c.get_text(strip=True)
                print(f"  Col {i}: {text[:50]}...")
            
            count += 1
            if count >= 5: break
            
    except Exception as e:
        print(f"ERREUR HTTP: {e}")

if __name__ == "__main__":
    debug_seamap_list()
