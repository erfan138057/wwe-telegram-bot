import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TELEGRAPH_TOKEN = os.environ.get("TELEGRAPH_TOKEN", "")
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
            data = json.load(f)
            return set(data.get("urls", []))
    return set()


def save_sent(sent: set):
    with open(SENT_FILE, "w") as f:
        json.dump({"urls": list(sent), "updated": datetime.utcnow().isoformat()}, f, indent=2)


def scrape_wwe_articles() -> list[dict]:
    url = "https://bleacherreport.com/wwe"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    for card in soup.select("a[href*='/articles/']"):
        href = card.get("href", "")
        if not href:
            continue

        full_url = href if href.startswith("http") else "https://bleacherreport.com" + href

        title = (
            card.get("aria-label")
            or (card.select_one("h1, h2, h3, h4, [class*='title'], [class*='headline']") or None)
            and card.select_one("h1, h2, h3, h4, [class*='title'], [class*='headline']").get_text(strip=True)
            or card.get_text(strip=True)
        )

        img_tag = card.select_one("img")
        image_url = None
        if img_tag:
            image_url = (
                img_tag.get("src")
                or img_tag.get("data-src")
                or img_tag.get("data-lazy-src")
            )
            if image_url and (image_url.startswith("data:") or len(image_url) < 20):
                image_url = None

        if title and len(title) > 10 and full_url not in [a["url"] for a in articles]:
            articles.append({"title": title, "url": full_url, "image": image_url})

    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    return unique[:20]


def scrape_article_content(url: str) -> list:
    """scrape محتوای مقاله و تبدیل به فرمت Telegraph"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        content = []

        # تصویر اصلی
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            content.append({
                "tag": "img",
                "attrs": {"src": og_image["content"]}
            })

        # متن مقاله - سعی میکنیم پاراگراف‌ها رو پیدا کنیم
        article_body = (
            soup.select_one("article")
            or soup.select_one("[class*='article-body']")
            or soup.select_one("[class*='ArticleBody']")
            or soup.select_one("main")
        )

        if article_body:
            for tag in article_body.find_all(["p", "h2", "h3", "blockquote"]):
                text = tag.get_text(strip=True)
                if not text or len(text) < 10:
                    continue

                if tag.name in ["h2", "h3"]:
                    content.append({"tag": "h3", "children": [text]})
                elif tag.name == "blockquote":
                    content.append({"tag": "blockquote", "children": [text]})
                else:
                    content.append({"tag": "p", "children": [text]})

        # اگه محتوایی پیدا نشد
        if len(content) <= 1:
            desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
            if desc and desc.get("content"):
                content.append({"tag": "p", "children": [desc["content"]]})
            content.append({
                "tag": "p",
                "children": [{"tag": "a", "attrs": {"href": url}, "children": ["Read full article on Bleacher Report →"]}]
            })

        return content

    except Exception as e:
        print(f"  ⚠️ Could not scrape content: {e}")
        return [{"tag": "p", "children": [{"tag": "a", "attrs": {"href": url}, "children": ["Read full article on Bleacher Report →"]}]}]


def create_telegraph_page(title: str, content: list, author_url: str) -> str | None:
    """ساخت صفحه Telegraph و برگرداندن URL"""
    if not TELEGRAPH_TOKEN:
        return None

    try:
        resp = requests.post("https://api.telegra.ph/createPage", json={
            "access_token": TELEGRAPH_TOKEN,
            "title": title,
            "author_name": "Bleacher Report",
            "author_url": author_url,
            "content": content,
            "return_content": False
        }, timeout=15)

        data = resp.json()
        if data.get("ok"):
            return "https://telegra.ph/" + data["result"]["path"]
        else:
            print(f"  ⚠️ Telegraph error: {data}")
            return None
    except Exception as e:
        print(f"  ⚠️ Telegraph failed: {e}")
        return None


def setup_telegraph() -> str | None:
    """ساخت اکانت Telegraph - فقط یه بار اجرا میشه"""
    try:
        resp = requests.get("https://api.telegra.ph/createAccount", params={
            "short_name": "WWEBot",
            "author_name": "WWE Bleacher Report"
        }, timeout=10)
        data = resp.json()
        if data.get("ok"):
            token = data["result"]["access_token"]
            print(f"  📝 Telegraph token: {token}")
            print(f"  ⚠️ Add this to GitHub Secrets as TELEGRAPH_TOKEN")
            return token
    except Exception as e:
        print(f"  ⚠️ Could not create Telegraph account: {e}")
    return None


def send_telegram(article: dict, telegraph_url: str | None):
    title = article["title"]
    url = telegraph_url or article["url"]
    image = article["image"]

    caption = f"🤼 <b>{title}</b>\n\n🔗 <a href='{url}'>{'Read on Telegraph' if telegraph_url else 'Read on Bleacher Report'}</a>"

    if image:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image,
            "caption": caption,
            "parse_mode": "HTML",
        }
        resp = requests.post(api_url, json=payload, timeout=15)
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

    # اگه TELEGRAPH_TOKEN نداریم، یه بار اکانت بساز
    global TELEGRAPH_TOKEN
    if not TELEGRAPH_TOKEN:
        print("  ⚠️ No TELEGRAPH_TOKEN found, trying to create account...")
        token = setup_telegraph()
        if token:
            TELEGRAPH_TOKEN = token

    sent = load_sent()
    print(f"Already sent: {len(sent)} articles")

    articles = scrape_wwe_articles()
    print(f"Found on site: {len(articles)} articles")

    new_count = 0
    for article in articles:
        if article["url"] not in sent:
            telegraph_url = None
            if TELEGRAPH_TOKEN:
                print(f"  📄 Scraping content for Telegraph...")
                content = scrape_article_content(article["url"])
                telegraph_url = create_telegraph_page(article["title"], content, article["url"])
                if telegraph_url:
                    print(f"  📝 Telegraph: {telegraph_url}")

            send_telegram(article, telegraph_url)
            sent.add(article["url"])
            new_count += 1
            print(f"  ✅ Sent: {article['title'][:60]}")
        else:
            print(f"  ⏭️ Skip: {article['title'][:60]}")

    save_sent(sent)
    print(f"Done. Sent {new_count} new articles.")


if __name__ == "__main__":
    main()
