import requests
from bs4 import BeautifulSoup

def list_all_labels():
    url = "https://seamap.env.duke.edu/dataset/2403/html"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("--- TOUS LES TD DE LA PAGE ---")
    tds = soup.find_all('td')
    for i, td in enumerate(tds):
        text = td.get_text(strip=True)
        if text in ['Latitude', 'Longitude', 'Records', 'Total']:
            print(f"TROUVÉ : '{text}' à l'index {i}")
            sibling = td.find_next_sibling('td')
            if sibling:
                print(f"  Valeur associée : '{sibling.get_text(strip=True)}'")

if __name__ == "__main__":
    list_all_labels()
