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
PER_FEED = 5
API = "https://api.groq.com/openai/v1"

# Tried in this order; the first one your key can actually use wins.
PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def get_headlines():
    items = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        if not feed.entries:
            print(f"warning: no entries from {url}")
        for entry in feed.entries[:PER_FEED]:
            items.append(f"- {entry.title} ({entry.link})")
    return items


def pick_model(api_key):
    """Ask Groq which models this key can use, then pick the best match."""
    r = requests.get(
        f"{API}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"Could not list models ({r.status_code}): {r.text}")
        sys.exit(1)
    available = [m["id"] for m in r.json().get("data", [])]
    print("Models available to this key:", ", ".join(sorted(available)))
    for model in PREFERRED_MODELS:
        if model in available:
            return model
    # Fall back to any text chat model that is not speech/audio/guard
    for model in available:
        if not any(x in model for x in ("whisper", "tts", "guard", "playai", "orpheus")):
            return model
    print("No usable chat model found for this key")
    sys.exit(1)


def summarize(headlines, api_key, model):
    prompt = (
        "Here are the latest tech headlines with links. Write a short news digest: "
        "4-6 bullet points, each one sentence, with the link in markdown.\n\n"
        + "\n".join(headlines)
    )
    r = requests.post(
        f"{API}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    if r.status_code != 200:
        print(f"Groq error {r.status_code} (model {model}): {r.text}")
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

    model = pick_model(api_key)
    print("Using model:", model)

    summary = summarize(headlines, api_key, model)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open("news.md", "w", encoding="utf-8") as f:
        f.write(f"# Latest Tech News\n\n*Updated: {now}*\n\n{summary}\n")
    print("news.md updated")


if __name__ == "__main__":
    main()
