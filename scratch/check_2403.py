import requests
from bs4 import BeautifulSoup

def check_2403():
    url = "https://seamap.env.duke.edu/dataset/2403/html"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers, timeout=20)
    ms = BeautifulSoup(response.text, 'html.parser')
    
    mm_label = ms.find("td", string=lambda t: t and "Marine mammals" in t)
    mm_count = mm_label.find_next_sibling("td").get_text(strip=True) if mm_label else "Non trouvé"
    
    print(f"Dataset 2403 - Marine mammals count: {mm_count}")

if __name__ == "__main__":
    check_2403()
