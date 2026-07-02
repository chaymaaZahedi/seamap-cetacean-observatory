import requests
from bs4 import BeautifulSoup

def find_2403_in_list():
    list_url = "https://seamap.env.duke.edu/dataset/list"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(list_url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', class_='listing')
    
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) > 2 and "2403" in cols[2].get_text():
            print("--- INFO 2403 DANS LA LISTE ---")
            for i, c in enumerate(cols):
                print(f"Col {i}: {c.get_text(strip=True)}")
            return

if __name__ == "__main__":
    find_2403_in_list()
