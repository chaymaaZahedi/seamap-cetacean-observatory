import requests
from bs4 import BeautifulSoup

def find_map_summary_records():
    url = "https://seamap.env.duke.edu/dataset/2403/html"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    ms = BeautifulSoup(response.text, 'html.parser')
    
    print("--- RECHERCHE 'Records' ET 'Map summary' ---")
    # On cherche le texte 'Map summary'
    map_sum = ms.find(string=lambda t: t and 'Map summary' in t)
    if map_sum:
        print(f"Section '{map_sum}' trouvée.")
        # On regarde les éléments autour
        parent = map_sum.find_parent()
        if parent:
            # On cherche 'Records' dans le voisinage
            records_node = parent.find_all(string=lambda t: t and 'Records' in t)
            for r in records_node:
                print(f"Trouvé label : '{r}'")
                # Tentative de trouver la valeur associée
                p = r.find_parent('td')
                if p:
                    sibling = p.find_next_sibling('td')
                    if sibling:
                        print(f"Valeur Records associée : '{sibling.get_text(strip=True)}'")

if __name__ == "__main__":
    find_map_summary_records()
