import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SENT_FILE = "sent_articles.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def load_sent() -> set:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE) as f:
            return set(json.load(f))
    return set()


def save_sent(sent: set):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f)


def scrape_wwe_articles() -> list[dict]:
    url = "https://bleacherreport.com/wwe"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []

    # Primary card articles
    for card in soup.select("a[href*='/articles/']"):
        href = card.get("href", "")
        if not href:
            continue

        full_url = href if href.startswith("http") else "https://bleacherreport.com" + href

        # Title: look inside the link or use aria-label
        title = (
            card.get("aria-label")
            or card.select_one("h1, h2, h3, h4, [class*='title'], [class*='headline']")
            and card.select_one("h1, h2, h3, h4, [class*='title'], [class*='headline']").get_text(strip=True)
            or card.get_text(strip=True)
        )

        # Image
        img_tag = card.select_one("img")
        image_url = None
        if img_tag:
            image_url = (
                img_tag.get("src")
                or img_tag.get("data-src")
                or img_tag.get("data-lazy-src")
            )
            # skip tiny placeholder/base64 images
            if image_url and (image_url.startswith("data:") or len(image_url) < 20):
                image_url = None

        if title and len(title) > 10 and full_url not in [a["url"] for a in articles]:
            articles.append({"title": title, "url": full_url, "image": image_url})

    # Deduplicate by URL while preserving order
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    return unique[:20]  # max 20 articles per run


def send_telegram(article: dict):
    title = article["title"]
    url = article["url"]
    image = article["image"]

    caption = f"🤼 <b>{title}</b>\n\n🔗 <a href='{url}'>Read on Bleacher Report</a>"

    if image:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image,
            "caption": caption,
            "parse_mode": "HTML",
        }
        resp = requests.post(api_url, json=payload, timeout=15)
        # If photo fails (bad URL etc.), fall back to text message
        if not resp.ok:
            send_text_only(caption)
    else:
        send_text_only(caption)


def send_text_only(caption: str):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": caption,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    requests.post(api_url, json=payload, timeout=15)


def main():
    print(f"[{datetime.utcnow().isoformat()}] Starting WWE bot...")
    sent = load_sent()
    articles = scrape_wwe_articles()
    print(f"Found {len(articles)} articles")

    new_count = 0
    for article in articles:
        if article["url"] not in sent:
            send_telegram(article)
            sent.add(article["url"])
            new_count += 1
            print(f"  ✅ Sent: {article['title'][:60]}")

    save_sent(sent)
    print(f"Done. Sent {new_count} new articles.")


if __name__ == "__main__":
    main()
