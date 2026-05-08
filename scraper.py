import requests
from bs4 import BeautifulSoup
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URLS = [
    "https://www.kijiji.ca/b-maisons-a-louer/drummondville/c37l80019a1700217",
    "https://www.kijiji.ca/b-appartements-condos/drummondville/c37l80019a1700270"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SEEN_FILE = "seen.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def scrape(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    annonces = []
    
    # Kijiji utilise des attributs data-listing-id ou id sur les li
    items = soup.find_all("li", attrs={"data-listing-id": True})
    
    # Fallback: cherche tous les articles avec un lien vers /v-
    if not items:
        items = soup.find_all("div", class_=lambda x: x and "regular-ad" in x)
    
    if not items:
        # Dernier recours: tous les liens /v- uniques
        liens = soup.find_all("a", href=lambda x: x and "/v-" in x and x.startswith("/"))
        seen_hrefs = set()
        for lien in liens:
            href = lien.get("href", "")
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            titre = lien.get_text(strip=True)
            if len(titre) > 10:
                annonces.append({
                    "id": href,
                    "titre": titre,
                    "prix": "",
                    "lien": "https://www.kijiji.ca" + href
                })
        return annonces
    
    for item in items:
        id_ = item.get("data-listing-id", "")
        titre = item.find(class_=lambda x: x and "title" in x.lower()) if item else None
        prix = item.find(class_=lambda x: x and "price" in x.lower()) if item else None
        lien_tag = item.find("a", href=lambda x: x and "/v-" in x)
        lien = "https://www.kijiji.ca" + lien_tag["href"] if lien_tag else ""
        annonces.append({
            "id": id_,
            "titre": titre.get_text(strip=True) if titre else "Sans titre",
            "prix": prix.get_text(strip=True) if prix else "",
            "lien": lien
        })
    
    return annonces

def envoyer_email(nouvelles):
    EMAIL = os.environ["EMAIL"]
    PASSWORD = os.environ["EMAIL_PASSWORD"]
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Kijiji – {len(nouvelles)} nouvelle(s) annonce(s)"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    
    corps = ""
    for a in nouvelles:
        corps += f"<h3>{a['titre']}</h3><p>{a['prix']}</p><p><a href='{a['lien']}'>Voir l'annonce</a></p><hr>"
    
    msg.attach(MIMEText(corps, "html"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, EMAIL, msg.as_string())

def main():
    seen = load_seen()
    nouvelles = []
    
    for url in URLS:
        annonces = scrape(url)
        print(f"Trouvé {len(annonces)} annonces sur {url}")
        for a in annonces:
            if a["id"] not in seen:
                nouvelles.append(a)
                seen.add(a["id"])
    
    if nouvelles:
        envoyer_email(nouvelles)
        save_seen(seen)
        print(f"{len(nouvelles)} nouvelles annonces envoyées.")
    else:
        print("Aucune nouvelle annonce.")

if __name__ == "__main__":
    main()
