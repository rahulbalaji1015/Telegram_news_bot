import os
import re
import json
import time
import html
import asyncio
import logging
import sqlite3
from datetime import datetime
from collections import Counter

import requests
import feedparser
import schedule

from rapidfuzz import fuzz
from textblob import TextBlob

# =========================================================
# LOAD ENV
# =========================================================

def load_dotenv(dotenv_path="newsbot.env"):

    if not os.path.exists(dotenv_path):
        return False

    with open(dotenv_path, encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if (
                not line
                or line.startswith("#")
                or "=" not in line
            ):
                continue

            key, value = line.split("=", 1)

            os.environ[key.strip()] = (
                value.strip()
                .strip('"')
                .strip("'")
            )

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
# SQLITE DATABASE
# =========================================================

conn = sqlite3.connect(
    "news.db",
    check_same_thread=False
)

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
# SOURCE SCORES
# =========================================================

SOURCE_SCORES = {

    "Reuters": 5,

    "BBC": 5,

    "CNN": 4,

    "TechCrunch": 4,

    "Google News": 3,

    "Hacker News": 3

}

# =========================================================
# BREAKING KEYWORDS
# =========================================================

BREAKING_KEYWORDS = [

    "breaking",
    "urgent",
    "attack",
    "earthquake",
    "explosion",
    "war",
    "alert"

]

# =========================================================
# CATEGORY KEYWORDS
# =========================================================

CATEGORY_KEYWORDS = {

    "AI": [

        "ai",
        "openai",
        "chatgpt",
        "gemini",
        "llm",
        "robot"

    ],

    "Technology": [

        "technology",
        "google",
        "microsoft",
        "startup",
        "software",
        "apple"

    ],

    "Cybersecurity": [

        "cyber",
        "hack",
        "malware",
        "attack"

    ],

    "Finance": [

        "stock",
        "market",
        "bitcoin",
        "crypto"

    ]

}

# =========================================================
# SAVE LOG FILE
# =========================================================

def save_log(message):

    with open(
        "news_log.txt",
        "a",
        encoding="utf-8"
    ) as f:

        f.write("\n\n")
        f.write("=" * 80)
        f.write("\n")
        f.write(
            datetime.now().strftime(
                "%d-%m-%Y %I:%M:%S %p"
            )
        )
        f.write("\n\n")
        f.write(message)
        f.write("\n")

# =========================================================
# CLEAN HTML
# =========================================================

def clean_html(text):

    if not text:
        return ""

    text = re.sub("<.*?>", "", text)

    return html.unescape(text)

# =========================================================
# EXTRACT IMAGE
# =========================================================

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
# FETCH NEWS
# =========================================================

def fetch_news(category="Technology"):

    all_news = []

    feeds = RSS_FEEDS.get(
        category,
        RSS_FEEDS["Technology"]
    )

    for rss_url in feeds:

        try:

            print(f"Fetching: {rss_url}")

            logging.info(f"Fetching: {rss_url}")

            feed = feedparser.parse(rss_url)

            for entry in feed.entries:

                title = entry.get("title", "")
                link = entry.get("link", "")

                if not title or not link:
                    continue

                description = clean_html(
                    entry.get("summary", "")
                )

                all_news.append({

                    "title": title,

                    "url": link,

                    "description": description,

                    "published": entry.get(
                        "published",
                        ""
                    ),

                    "image": extract_image(entry),

                    "source": feed.feed.get(
                        "title",
                        "Unknown"
                    )

                })

        except Exception as e:

            logging.error(e)

    return all_news

# =========================================================
# REMOVE DUPLICATES
# =========================================================

def remove_duplicates(news_items):

    unique_news = []

    for item in news_items:

        duplicate = False

        for existing in unique_news:

            similarity = fuzz.ratio(

                item["title"].lower(),

                existing["title"].lower()

            )

            if similarity > 85:

                duplicate = True
                break

        if not duplicate:
            unique_news.append(item)

    return unique_news

# =========================================================
# DETECT CATEGORY
# =========================================================

def detect_category(title):

    title = title.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            if keyword in title:
                return category

    return "General"

# =========================================================
# SENTIMENT ANALYSIS
# =========================================================

def detect_sentiment(text):

    polarity = TextBlob(text).sentiment.polarity

    if polarity > 0.2:
        return "😊 Positive Outlook"

    elif polarity < -0.2:
        return "⚠ Negative Impact"

    return "😐 Neutral Update"

# =========================================================
# BREAKING NEWS
# =========================================================

def is_breaking_news(title):

    title = title.lower()

    return any(

        keyword in title

        for keyword in BREAKING_KEYWORDS

    )

# =========================================================
# HASHTAGS
# =========================================================

def generate_hashtags(title):

    hashtags = []

    words = title.split()

    for word in words[:5]:

        clean = "".join(
            c for c in word if c.isalnum()
        )

        if len(clean) > 3:

            hashtags.append(f"#{clean}")

    return " ".join(hashtags)

# =========================================================
# TREND DETECTION
# =========================================================

def detect_trends(news_items):

    keywords = []

    for item in news_items:

        for word in item["title"].split():

            word = word.lower()

            if len(word) > 4:
                keywords.append(word)

    counter = Counter(keywords)

    return counter.most_common(5)

# =========================================================
# SUMMARY
# =========================================================

def generate_summary(item):

    desc = item.get("description", "")

    if not desc:
        return (
            "Latest update from trusted "
            "news sources."
        )

    return desc[:180] + "..."

# =========================================================
# SCORE LABELS
# =========================================================

def score_label(score):

    if score >= 12:
        return "🔥 Highly Trending"

    elif score >= 8:
        return "🚀 Popular Topic"

    elif score >= 5:
        return "📈 Rising News"

    return "📰 Regular Update"

# =========================================================
# RANK NEWS
# =========================================================

def rank_news(news_items):

    ranked = []

    for item in news_items:

        score = 0

        title = item["title"].lower()

        for category, keywords in CATEGORY_KEYWORDS.items():

            for keyword in keywords:

                if keyword in title:
                    score += 3

        if is_breaking_news(title):
            score += 6

        source = item["source"]

        for src, src_score in SOURCE_SCORES.items():

            if src.lower() in source.lower():
                score += src_score

        item["score"] = score

        ranked.append(item)

    ranked.sort(

        key=lambda x: x["score"],

        reverse=True

    )

    return ranked

# =========================================================
# SAVE NEWS DATABASE
# =========================================================

def save_news(item, category):

    try:

        cursor.execute("""

        INSERT OR IGNORE INTO news
        (title, url, category, created_at)

        VALUES (?, ?, ?, ?)

        """, (

            item["title"],

            item["url"],

            category,

            str(datetime.now())

        ))

        conn.commit()

    except Exception as e:

        logging.error(e)

# =========================================================
# CLEAN DATABASE
# =========================================================

def cleanup_old_news():

    try:

        cursor.execute("""

        DELETE FROM news

        WHERE created_at < datetime(
            'now',
            '-7 day'
        )

        """)

        conn.commit()

    except Exception as e:

        logging.error(e)

# =========================================================
# TELEGRAM BUTTONS
# =========================================================

def get_buttons():

    keyboard = {

        "inline_keyboard": [

            [

                {
                    "text": "🤖 AI",
                    "callback_data": "AI"
                },

                {
                    "text": "💻 Technology",
                    "callback_data": "Technology"
                }

            ],

            [

                {
                    "text": "🛡 Cybersecurity",
                    "callback_data": "Cybersecurity"
                },

                {
                    "text": "💰 Finance",
                    "callback_data": "Finance"
                }

            ],

            [

                {
                    "text": "🌍 World",
                    "callback_data": "World"
                }

            ]

        ]
    }

    return keyboard

# =========================================================
# TELEGRAM REQUEST
# =========================================================

def telegram_request(method, payload):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    try:

        response = requests.post(

            url,

            data=payload,

            timeout=30

        )

        return response.json()

    except Exception as e:

        logging.error(e)

        return None

# =========================================================
# SEND NEWS
# =========================================================

async def send_news(

    category="Technology",

    custom_chat_id=None

):

    print(f"\nFetching {category} news...")

    news_items = fetch_news(category)

    print(f"Fetched: {len(news_items)}")

    news_items = remove_duplicates(news_items)

    print(
        f"After Duplicate Removal: "
        f"{len(news_items)}"
    )

    news_items = rank_news(news_items)

    if not news_items:

        telegram_request(

            "sendMessage",

            {

                "chat_id":
                custom_chat_id or CHAT_ID,

                "text":
                "No news available."

            }

        )

        return

    category_title = CATEGORY_DISPLAY.get(
        category,
        "📰 News"
    )

    today = datetime.now().strftime(
        "%d %B %Y"
    )

    current_time = datetime.now().strftime(
        "%I:%M %p"
    )

    trends = detect_trends(news_items)

    trend_text = "🔥 Trending Topics\n\n"

    for trend, count in trends:

        trend_text += (
            f"• {trend.title()} ({count})\n"
        )

    header_message = (

        f"🚀 TOP 7 NEWS UPDATE\n\n"

        f"{category_title}\n"

        f"📅 {today}\n"

        f"⏰ {current_time}\n\n"

        f"{trend_text}"

    )

    save_log(header_message)

    telegram_request(

        "sendMessage",

        {

            "chat_id":
            custom_chat_id or CHAT_ID,

            "text": header_message,

            "reply_markup": json.dumps(
                get_buttons()
            )

        }

    )

    for idx, item in enumerate(
        news_items[:TOTAL_NEWS],
        start=1
    ):

        summary = generate_summary(item)

        sentiment = detect_sentiment(
            item["title"]
        )

        score_text = score_label(
            item["score"]
        )

        hashtags = generate_hashtags(
            item["title"]
        )

        breaking = ""

        if is_breaking_news(item["title"]):

            breaking = (
                "🚨 BREAKING NEWS 🚨\n\n"
            )

        article_text = (

            f"{breaking}"

            f"📰 {idx}. {item['title']}\n\n"

            f"🤖 Summary:\n"
            f"{summary}\n\n"

            f"{sentiment}\n"

            f"{score_text}\n\n"

            f"🔗 {item['url']}\n\n"

            f"{hashtags}"

        )

        save_log(article_text)

        save_news(item, category)

        try:

            if item.get("image"):

                telegram_request(

                    "sendPhoto",

                    {

                        "chat_id":
                        custom_chat_id or CHAT_ID,

                        "photo": item["image"],

                        "caption": article_text[:1024]

                    }

                )

            else:

                telegram_request(

                    "sendMessage",

                    {

                        "chat_id":
                        custom_chat_id or CHAT_ID,

                        "text": article_text

                    }

                )

        except Exception as e:

            logging.error(e)

        await asyncio.sleep(1)

    digest = "🧠 DAILY NEWS DIGEST\n\n"

    for item in news_items[:5]:

        digest += f"• {item['title']}\n"

    save_log(digest)

    telegram_request(

        "sendMessage",

        {

            "chat_id":
            custom_chat_id or CHAT_ID,

            "text": digest

        }

    )

    telegram_request(

        "sendMessage",

        {

            "chat_id":
            custom_chat_id or CHAT_ID,

            "text":

            (
                "📂 Select another category "
                "to view more live news."
            ),

            "reply_markup":
            json.dumps(get_buttons())

        }

    )

    print("News Sent Successfully!")

# =========================================================
# CALLBACK HANDLER
# =========================================================

async def handle_callback_query():

    last_update_id = None

    while True:

        try:

            url = (
                f"https://api.telegram.org/"
                f"bot{BOT_TOKEN}/getUpdates"
            )

            if last_update_id:

                url += (
                    f"?offset={last_update_id + 1}"
                )

            response = requests.get(
                url,
                timeout=30
            ).json()

            if response.get("ok"):

                for update in response["result"]:

                    last_update_id = update["update_id"]

                    # ====================================
                    # BUTTON CLICK
                    # ====================================

                    if "callback_query" in update:

                        callback = update[
                            "callback_query"
                        ]

                        category = callback[
                            "data"
                        ]

                        callback_id = callback[
                            "id"
                        ]

                        chat_id = callback[
                            "message"
                        ]["chat"]["id"]

                        telegram_request(

                            "answerCallbackQuery",

                            {

                                "callback_query_id":
                                callback_id

                            }

                        )

                        await send_news(

                            category,

                            custom_chat_id=chat_id

                        )

                    # ====================================
                    # START COMMAND
                    # ====================================

                    elif "message" in update:

                        message = update["message"]

                        text = message.get(
                            "text",
                            ""
                        )

                        chat_id = message[
                            "chat"
                        ]["id"]

                        if text == "/start":

                            telegram_request(

                                "sendMessage",

                                {

                                    "chat_id": chat_id,

                                    "text":

                                    (
                                        "🚀 Rahul AI News Bot\n\n"

                                        "Select a category "
                                        "below to get "
                                        "latest Top 7 news."
                                    ),

                                    "reply_markup":
                                    json.dumps(
                                        get_buttons()
                                    )

                                }

                            )

        except Exception as e:

            print("Callback Error:", e)

            logging.error(e)

        await asyncio.sleep(3)

# =========================================================
# JOB FUNCTIONS
# =========================================================

def ai_job():

    asyncio.run(send_news("AI"))

def tech_job():

    asyncio.run(send_news("Technology"))

def cyber_job():

    asyncio.run(send_news("Cybersecurity"))

def finance_job():

    asyncio.run(send_news("Finance"))

def world_job():

    asyncio.run(send_news("World"))

# =========================================================
# SCHEDULE
# =========================================================

schedule.every().day.at(
    "08:00"
).do(ai_job)

schedule.every().day.at(
    "13:00"
).do(tech_job)

schedule.every().day.at(
    "17:00"
).do(cyber_job)

schedule.every().day.at(
    "20:00"
).do(finance_job)

schedule.every().day.at(
    "22:00"
).do(world_job)

# =========================================================
# MAIN
# =========================================================

print("🚀 Rahul AI News Bot Running...")

logging.info(
    "Rahul AI News Bot Started"
)

cleanup_old_news()

async def main_loop():

    asyncio.create_task(
        handle_callback_query()
    )

    # Immediate startup news
    asyncio.create_task(
        send_news("Technology")
    )

    while True:

        schedule.run_pending()

        await asyncio.sleep(30)

asyncio.run(main_loop())