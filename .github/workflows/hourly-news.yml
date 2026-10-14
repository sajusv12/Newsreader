import os
import sys
from datetime import datetime, timezone

import feedparser
import requests

FEEDS = [
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
]
MODEL = "llama-3.3-70b-versatile"
PER_FEED = 5


def get_headlines():
    items = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        if not feed.entries:
            print(f"warning: no entries from {url}")
        for entry in feed.entries[:PER_FEED]:
            items.append(f"- {entry.title} ({entry.link})")
    return items


def summarize(headlines, api_key):
    prompt = (
        "Here are the latest tech headlines with links. Write a short news digest: "
        "4-6 bullet points, each one sentence, with the link in markdown.\n\n"
        + "\n".join(headlines)
    )
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    if r.status_code != 200:
        print(f"Groq error {r.status_code}: {r.text}")
        sys.exit(1)
    return r.json()["choices"][0]["message"]["content"]


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY is not set (add it under Settings > Secrets > Actions)")
        sys.exit(1)

    headlines = get_headlines()
    if not headlines:
        print("No headlines fetched, nothing to do")
        sys.exit(1)

    summary = summarize(headlines, api_key)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open("news.md", "w", encoding="utf-8") as f:
        f.write(f"# Latest Tech News\n\n*Updated: {now}*\n\n{summary}\n")
    print("news.md updated")


if __name__ == "__main__":
    main()
