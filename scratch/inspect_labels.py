import requests
from bs4 import BeautifulSoup

def inspect_summary_labels():
    url = "https://seamap.env.duke.edu/dataset/2403/html"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    ms = BeautifulSoup(response.text, 'html.parser')
    
    print("--- LISTE DES LABELS TROUVÉS DANS LE RÉSUMÉ ---")
    table = ms.find('table', class_='summary') # On cherche la table summary
    if not table:
        # Si pas de classe summary, on prend toutes les td de gauche
        rows = ms.find_all('tr')
        for r in rows:
            tds = r.find_all('td')
            if len(tds) >= 2:
                print(f"Label: '{tds[0].get_text(strip=True)}' | Valeur: '{tds[1].get_text(strip=True)}'")
    else:
        for r in table.find_all('tr'):
            tds = r.find_all('td')
            if len(tds) >= 2:
                print(f"Label: '{tds[0].get_text(strip=True)}' | Valeur: '{tds[1].get_text(strip=True)}'")

if __name__ == "__main__":
    inspect_summary_labels()
