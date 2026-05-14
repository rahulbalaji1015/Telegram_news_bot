import os
import re
import json
import html
import asyncio
import logging
import sqlite3
from datetime import datetime
from collections import Counter

import requests
import feedparser
from rapidfuzz import fuzz
from textblob import TextBlob

# =========================================================
# ENV LOADING
# =========================================================

def load_dotenv(dotenv_path="newsbot.env"):
    if not os.path.exists(dotenv_path):
        return False

    with open(dotenv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")

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
# RSS FEEDS
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
        "https://news.google.com/rss/search?q=cybersecurity&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "Finance": [
        "https://news.google.com/rss/search?q=finance&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "World": [
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en",
        "https://feeds.reuters.com/Reuters/worldNews"
    ]
}

# =========================================================
# CATEGORY DISPLAY
# =========================================================

CATEGORY_DISPLAY = {
    "AI": "🤖 AI & Machine Learning",
    "Technology": "💻 Technology",
    "Cybersecurity": "🛡 Cybersecurity",
    "Finance": "💰 Finance",
    "World": "🌍 World News",
    "General": "📰 General News"
}

# =========================================================
# HELPERS
# =========================================================

def telegram_request(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    try:
        r = requests.post(url, data=payload, timeout=30)
        return r.json()
    except Exception as e:
        logging.error(e)
        return None


def clean_html(text):
    if not text:
        return ""
    text = re.sub("<.*?>", "", text)
    return html.unescape(text)


def extract_image(entry):
    try:
        if "media_content" in entry:
            media = entry.media_content
            if media:
                return media[0]["url"]
    except:
        pass
    return None

# =========================================================
# NEWS FETCH
# =========================================================

def fetch_news(category="Technology"):
    all_news = []
    feeds = RSS_FEEDS.get(category, RSS_FEEDS["Technology"])

    for url in feeds:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")

                if not title or not link:
                    continue

                all_news.append({
                    "title": title,
                    "url": link,
                    "description": clean_html(entry.get("summary", "")),
                    "image": extract_image(entry),
                    "source": feed.feed.get("title", "Unknown")
                })

        except Exception as e:
            logging.error(e)

    return all_news


def remove_duplicates(news):
    unique = []

    for item in news:
        if not any(
            fuzz.ratio(item["title"].lower(), x["title"].lower()) > 85
            for x in unique
        ):
            unique.append(item)

    return unique


def rank_news(news):
    for item in news:
        item["score"] = 1
    return sorted(news, key=lambda x: x["score"], reverse=True)

# =========================================================
# NEWS SENDER
# =========================================================

async def send_news(category, chat_id):

    news = fetch_news(category)
    news = remove_duplicates(news)
    news = rank_news(news)

    if not news:
        telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": "No news available."
        })
        return

    header = f"""🚀 TOP 7 NEWS

{CATEGORY_DISPLAY.get(category, category)}
📅 {datetime.now().strftime('%d %B %Y')}
"""

    telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": header,
        "reply_markup": json.dumps(get_buttons())
    })

    for i, item in enumerate(news[:TOTAL_NEWS], 1):

        msg = f"""📰 {i}. {item['title']}

🔗 {item['url']}
"""

        telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": msg
        })

        await asyncio.sleep(1)

# =========================================================
# BUTTON MENU (IMPORTANT FIX)
# =========================================================

def get_buttons():
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
            [
                {"text": "🌍 World", "callback_data": "World"}
            ]
        ]
    }

# =========================================================
# SINGLE CALLBACK LOOP (NO INFINITE STALLS IN ACTIONS)
# =========================================================

async def handle_callbacks():

    last_update = None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    if last_update:
        url += f"?offset={last_update + 1}"

    try:
        res = requests.get(url, timeout=20).json()

        if res.get("ok"):
            for update in res["result"]:

                last_update = update["update_id"]

                if "message" in update:
                    msg = update["message"]
                    text = msg.get("text", "")
                    chat_id = msg["chat"]["id"]

                    if text == "/start":
                        telegram_request("sendMessage", {
                            "chat_id": chat_id,
                            "text": "🚀 Choose a category:",
                            "reply_markup": json.dumps(get_buttons())
                        })

                if "callback_query" in update:
                    cb = update["callback_query"]
                    category = cb["data"]
                    chat_id = cb["message"]["chat"]["id"]

                    telegram_request("answerCallbackQuery", {
                        "callback_query_id": cb["id"]
                    })

                    await send_news(category, chat_id)

    except Exception as e:
        logging.error(e)

# =========================================================
# MAIN (IMPORTANT FIX FOR GITHUB ACTIONS)
# =========================================================

async def main():
    print("Bot started")

    await handle_callbacks()

    # OPTIONAL: default run (can be removed)
    await send_news("Technology", CHAT_ID)


asyncio.run(main())
