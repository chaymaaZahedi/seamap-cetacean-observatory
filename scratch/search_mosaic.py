import requests
from bs4 import BeautifulSoup

def search_mosaic():
    list_url = "https://seamap.env.duke.edu/dataset/list"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(list_url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # On cherche n'importe quel élément qui contient 'MOSAIC'
    mosaic_node = soup.find(string=lambda t: t and 'MOSAIC' in t)
    if not mosaic_node:
        print("MOSAIC non trouvé sur la page.")
        return
        
    # On remonte à la ligne (tr)
    row = mosaic_node.find_parent('tr')
    if row:
        cols = row.find_all('td')
        print(f"--- LIGNE MOSAIC TROUVÉE ---")
        for i, c in enumerate(cols):
            print(f"Col {i}: {c.get_text(strip=True)}")
    else:
        print("MOSAIC trouvé mais pas dans un <tr>")

if __name__ == "__main__":
    search_mosaic()
