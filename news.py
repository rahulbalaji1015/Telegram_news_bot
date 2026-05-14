import os
import re
import json
import html
import asyncio
import logging
import sqlite3
import requests
import feedparser

from datetime import datetime
from collections import Counter
from rapidfuzz import fuzz
from textblob import TextBlob

# =========================================================
# ENV
# =========================================================

def load_dotenv(path="newsbot.env"):
    if not os.path.exists(path):
        return False

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")
    return True


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TOTAL_NEWS = 7

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    filename="news_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect("news.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE,
    category TEXT,
    created_at TEXT
)
""")
conn.commit()

# =========================================================
# RSS
# =========================================================

RSS_FEEDS = {
    "AI": [
        "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-IN&gl=IN&ceid=IN:en",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://hnrss.org/newest?q=AI"
    ],
    "Technology": [
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en",
        "https://techcrunch.com/feed/",
        "https://hnrss.org/frontpage"
    ],
    "Cybersecurity": [
        "https://news.google.com/rss/search?q=cybersecurity&hl=en-IN&gl=IN&ceid=IN:en"
    ],
    "Finance": [
        "https://news.google.com/rss/search?q=finance&hl=en-IN&gl=IN&ceid=IN:en"
    ],
    "World": [
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en",
        "https://feeds.reuters.com/Reuters/worldNews"
    ]
}

CATEGORY_KEYWORDS = {
    "AI": ["ai", "openai", "chatgpt", "gemini", "llm", "robot"],
    "Technology": ["google", "microsoft", "apple", "software", "startup"],
    "Cybersecurity": ["hack", "malware", "attack", "cyber"],
    "Finance": ["stock", "bitcoin", "crypto", "market"]
}

BREAKING_KEYWORDS = ["breaking", "urgent", "attack", "war", "earthquake", "explosion"]

SOURCE_SCORES = {
    "reuters": 5,
    "bbc": 5,
    "cnn": 4,
    "techcrunch": 4,
    "google": 3,
    "hacker news": 3
}

# =========================================================
# TELEGRAM API
# =========================================================

def tg(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        return requests.post(url, data=payload, timeout=20).json()
    except Exception as e:
        logging.error(e)

# =========================================================
# HELPERS
# =========================================================

def clean(text):
    return html.unescape(re.sub("<.*?>", "", text or ""))


def sentiment(text):
    p = TextBlob(text).sentiment.polarity
    if p > 0.2:
        return "😊 Positive"
    if p < -0.2:
        return "⚠ Negative"
    return "😐 Neutral"


def is_breaking(title):
    t = title.lower()
    return any(k in t for k in BREAKING_KEYWORDS)


def hashtags(title):
    return " ".join(
        f"#{w}" for w in title.split()[:5]
        if len(w) > 3
    )


def detect_category(title):
    t = title.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in t for k in kws):
            return cat
    return "General"


def trend_keywords(news):
    words = []
    for n in news:
        for w in n["title"].split():
            if len(w) > 4:
                words.append(w.lower())
    return Counter(words).most_common(5)

# =========================================================
# NEWS FETCH
# =========================================================

def fetch(category):
    items = []

    for url in RSS_FEEDS.get(category, RSS_FEEDS["Technology"]):
        feed = feedparser.parse(url)

        for e in feed.entries:
            items.append({
                "title": e.get("title", ""),
                "url": e.get("link", ""),
                "desc": clean(e.get("summary", "")),
                "source": feed.feed.get("title", "Unknown")
            })

    return items


def dedupe(news):
    out = []
    for n in news:
        if not any(fuzz.ratio(n["title"], x["title"]) > 85 for x in out):
            out.append(n)
    return out


def rank(news):
    for n in news:
        score = 0

        title = n["title"].lower()

        # keyword score
        for kws in CATEGORY_KEYWORDS.values():
            if any(k in title for k in kws):
                score += 3

        # breaking
        if is_breaking(title):
            score += 6

        # source boost
        for src, val in SOURCE_SCORES.items():
            if src in n["source"].lower():
                score += val

        n["score"] = score

    return sorted(news, key=lambda x: x["score"], reverse=True)

# =========================================================
# UI BUTTONS
# =========================================================

def buttons():
    return {
        "inline_keyboard": [
            [
                {"text": "🤖 AI", "callback_data": "AI"},
                {"text": "💻 Tech", "callback_data": "Technology"}
            ],
            [
                {"text": "🛡 Cyber", "callback_data": "Cybersecurity"},
                {"text": "💰 Finance", "callback_data": "Finance"}
            ],
            [{"text": "🌍 World", "callback_data": "World"}]
        ]
    }

# =========================================================
# SEND NEWS (FULL FEATURE ENGINE)
# =========================================================

async def send_news(category, chat_id):

    news = rank(dedupe(fetch(category)))

    if not news:
        tg("sendMessage", {"chat_id": chat_id, "text": "No news available"})
        return

    trends = trend_keywords(news)

    header = f"""🚀 TOP NEWS - {category}

🔥 Trending:
{chr(10).join([f"• {w} ({c})" for w, c in trends])}

📅 {datetime.now().strftime('%d %B %Y')}
"""

    tg("sendMessage", {
        "chat_id": chat_id,
        "text": header,
        "reply_markup": json.dumps(buttons())
    })

    for i, n in enumerate(news[:TOTAL_NEWS], 1):

        msg = f"""📰 {i}. {n['title']}

🤖 {sentiment(n['title'])}
🔥 Score: {n['score']}
🏷 {hashtags(n['title'])}

🔗 {n['url']}"""

        tg("sendMessage", {
            "chat_id": chat_id,
            "text": msg
        })

        await asyncio.sleep(1)

    # digest
    digest = "🧠 DAILY DIGEST\n\n" + "\n".join(
        f"• {n['title']}" for n in news[:5]
    )

    tg("sendMessage", {
        "chat_id": chat_id,
        "text": digest
    })

# =========================================================
# CALLBACK HANDLER (GITHUB SAFE)
# =========================================================

async def handle_updates():

    last = None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    if last:
        url += f"?offset={last+1}"

    try:
        res = requests.get(url, timeout=20).json()

        if res.get("ok"):
            for u in res["result"]:
                last = u["update_id"]

                if "message" in u:
                    chat_id = u["message"]["chat"]["id"]
                    text = u["message"].get("text", "")

                    if text == "/start":
                        tg("sendMessage", {
                            "chat_id": chat_id,
                            "text": "🚀 News Bot Ready",
                            "reply_markup": json.dumps(buttons())
                        })

                if "callback_query" in u:
                    cb = u["callback_query"]
                    chat_id = cb["message"]["chat"]["id"]

                    tg("answerCallbackQuery", {
                        "callback_query_id": cb["id"]
                    })

                    await send_news(cb["data"], chat_id)

    except Exception as e:
        logging.error(e)

# =========================================================
# MAIN (GITHUB ACTION SAFE)
# =========================================================

async def main():
    print("Bot Running (Full Feature Mode)")
    await handle_updates()
    await send_news("Technology", CHAT_ID)


asyncio.run(main())
