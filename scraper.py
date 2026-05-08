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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
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
    for item in soup.select("[data-listing-id]"):
        id_ = item["data-listing-id"]
        titre = item.select_one("[class*='title']")
        prix = item.select_one("[class*='price']")
        lien = "https://www.kijiji.ca" + item.select_one("a")["href"] if item.select_one("a") else ""
        annonces.append({
            "id": id_,
            "titre": titre.text.strip() if titre else "Sans titre",
            "prix": prix.text.strip() if prix else "Prix non indiqué",
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
