import asyncio
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.async_api import async_playwright

URLS = [
    "https://www.kijiji.ca/b-maisons-a-louer/drummondville/c37l80019a1700217",
    "https://www.kijiji.ca/b-appartements-condos/drummondville/c37l80019a1700270"
]

SEEN_FILE = "seen.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

async def scrape(page, url):
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)
    
    annonces = []
    items = await page.query_selector_all("[data-listing-id]")
    
    for item in items:
        id_ = await item.get_attribute("data-listing-id")
        titre_el = await item.query_selector("[class*='title']")
        prix_el = await item.query_selector("[class*='price']")
        lien_el = await item.query_selector("a[href*='/v-']")
        
        titre = await titre_el.inner_text() if titre_el else "Sans titre"
        prix = await prix_el.inner_text() if prix_el else ""
        href = await lien_el.get_attribute("href") if lien_el else ""
        lien = "https://www.kijiji.ca" + href if href else ""
        
        if id_:
            annonces.append({
                "id": id_,
                "titre": titre.strip(),
                "prix": prix.strip(),
                "lien": lien
            })
    
    print(f"Trouvé {len(annonces)} annonces sur {url}")
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

async def main():
    seen = load_seen()
    nouvelles = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        
        for url in URLS:
            annonces = await scrape(page, url)
            for a in annonces:
                if a["id"] not in seen:
                    nouvelles.append(a)
                    seen.add(a["id"])
        
        await browser.close()
    
    if nouvelles:
        envoyer_email(nouvelles)
        save_seen(seen)
        print(f"{len(nouvelles)} nouvelles annonces envoyées.")
    else:
        print("Aucune nouvelle annonce.")

if __name__ == "__main__":
    asyncio.run(main())
