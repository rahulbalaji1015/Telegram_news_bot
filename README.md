# 🚀 Rahul AI News Bot

An advanced AI-powered Telegram News Automation Bot built using Python, RSS feeds, Telegram Bot API, SQLite, and intelligent news ranking.

This bot automatically fetches trending news from multiple trusted sources, removes duplicates, detects trends, performs sentiment analysis, ranks important news, and sends beautifully formatted updates to Telegram channels/groups/users.

---

# ✨ Features

## 📰 Multi-Source News Aggregation
Fetches news from:
- Google News RSS
- TechCrunch
- HackerNews
- Reuters

---

## 🤖 AI & Smart Features

### ✅ Duplicate News Removal
Uses `RapidFuzz` fuzzy matching to remove repeated articles.

### ✅ Intelligent News Ranking
Ranks articles based on:
- keywords
- trusted sources
- breaking news detection

### ✅ Sentiment Analysis
Detects:
- Positive
- Negative
- Neutral news

### ✅ Trend Detection
Identifies trending keywords/topics from news headlines.

### ✅ Auto Hashtag Generation
Generates hashtags automatically from article titles.

### ✅ Breaking News Detection
Highlights urgent/breaking news instantly.

---

## 📂 Multiple Categories

Supports:
- 🤖 AI & Machine Learning
- 💻 Technology
- 🛡 Cybersecurity
- 💰 Finance
- 🌍 World News

---

## 📸 Telegram Enhancements

### ✅ Inline Buttons
Users can select categories interactively.

### ✅ Image Support
Automatically sends article thumbnails when available.

### ✅ Beautiful Formatting
Professional Telegram news presentation.

---

## 💾 Database Support

Uses SQLite database to:
- store sent articles
- avoid duplicate posting
- maintain history

---

## 📄 Logging System

Creates:
- `news_log.txt`
- `news_bot.log`

for debugging and analytics.

---

# 🏗 Tech Stack

| Technology | Usage |
|---|---|
| Python | Core backend |
| Telegram Bot API | Message delivery |
| RSS Feeds | News collection |
| SQLite | Database |
| RapidFuzz | Duplicate detection |
| TextBlob | Sentiment analysis |
| Feedparser | RSS parsing |
| Schedule | Automation |

---

# 📁 Project Structure

```bash
Telegram_news_bot/
│
├── news_bot.py
├── newsbot.env
├── requirements.txt
├── news.db
├── news_log.txt
├── news_bot.log
│
├── .github/
│   └── workflows/
│       └── news.yml
│
└── README.md
```

---

# ⚙️ Installation Guide

# Step 1 — Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/Telegram_news_bot.git

cd Telegram_news_bot
```

---

# Step 2 — Create Virtual Environment

## Windows

```bash
python -m venv venv

venv\Scripts\activate
```

## Linux / Mac

```bash
python3 -m venv venv

source venv/bin/activate
```

---

# Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Step 4 — Create Environment File

Create:

```bash
newsbot.env
```

Add:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_CHAT_ID
```

---

# 🤖 Create Telegram Bot

Open Telegram:

## Search:
```text
@BotFather
```

Commands:

```text
/newbot
```

Copy:
- BOT TOKEN

---

# 📢 Get Chat ID

## Add bot to channel/group as admin

Then open:

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

Find:

```json
"chat": {
    "id": -100xxxxxxxxxx
}
```

Copy that as:
```env
CHAT_ID
```

---

# ▶️ Run The Bot

```bash
python news_bot.py
```

---

# 🧠 Features Included in Step 5

The Step 5 version includes:

✅ Multiple RSS Sources  
✅ Duplicate Removal  
✅ Sentiment Analysis  
✅ Trend Detection  
✅ Inline Telegram Buttons  
✅ Category-Based News  
✅ News Ranking Algorithm  
✅ SQLite Database  
✅ Logging System  
✅ Breaking News Detection  
✅ Automatic Hashtags  
✅ Telegram Image Support  
✅ Daily Digest Generation  

---

# 📦 Requirements

```txt
requests
feedparser
schedule
rapidfuzz
textblob
```

---

# 📥 Install TextBlob Data

Run once:

```bash
python -m textblob.download_corpora
```

---

# 🚀 GitHub Actions Automation

Create:

```bash
.github/workflows/news.yml
```

Example workflow:

```yaml
name: Rahul AI News Bot

on:
  schedule:
    - cron: '30 2 * * *'

  workflow_dispatch:

jobs:
  run-bot:

    runs-on: ubuntu-latest

    steps:

      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          pip install -r requirements.txt

      - name: Create ENV File
        run: |
          echo "BOT_TOKEN=${{ secrets.BOT_TOKEN }}" >> newsbot.env
          echo "CHAT_ID=${{ secrets.CHAT_ID }}" >> newsbot.env

      - name: Run Bot
        run: |
          python news_bot.py
```

---

# 🔐 GitHub Secrets

Go to:

```text
Repository
→ Settings
→ Secrets and Variables
→ Actions
```

Add:
- `BOT_TOKEN`
- `CHAT_ID`

---

# 🕒 Scheduled News Timing

| Time | Category |
|---|---|
| 08:00 | AI |
| 13:00 | Technology |
| 17:00 | Cybersecurity |
| 20:00 | Finance |
| 22:00 | World News |

---

# 📈 Future Improvements

Possible upgrades:
- AI-generated summaries
- Voice news updates
- Web dashboard
- User subscriptions
- Multi-language translation
- OpenAI/Gemini integration
- Analytics dashboard

---

# 🧑‍💻 Author

## Rahul Balaji

AI News Automation System using:
- Python
- Telegram Bot API
- RSS Aggregation
- NLP
- Automation

---
