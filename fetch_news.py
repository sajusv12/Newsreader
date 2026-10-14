import os
import sys
from datetime import datetime, timezone

import feedparser
import requests

# ---- Edit these lists to change your sources -------------------------------
# Any feed that is empty or broken is skipped (a warning shows in the log).
SECTIONS = {
    "Lithuania": {
        "emoji": "🇱🇹",
        "title": "Lietuvoje",
        "feeds": [
            "https://www.lrt.lt/?rss",                    # LRT (Lithuanian)
            "https://www.15min.lt/rss",                   # 15min (Lithuanian)
            "https://www.lrt.lt/en/news-in-english?rss",  # LRT English
        ],
    },
    "World": {
        "emoji": "🌍",
        "title": "Pasaulyje",
        "feeds": [
            "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC World
            "https://www.aljazeera.com/xml/rss/all.xml",    # Al Jazeera
            "https://rss.dw.com/rdf/rss-en-world",          # Deutsche Welle
        ],
    },
}
PER_FEED = 6
# -----------------------------------------------------------------------------

API = "https://api.groq.com/openai/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; news-bot/1.0)"}

# Tried in this order; the first one your key can actually use wins.
PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def get_headlines(feeds):
    items = []
    for url in feeds:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            feed = feedparser.parse(r.content)
        except Exception as e:
            print(f"warning: could not fetch {url}: {e}")
            continue
        entries = feed.entries[:PER_FEED]
        print(f"{len(entries):2d} items from {url}")
        for entry in entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if title and link:
                items.append(f"- {title} ({link})")
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
    for model in PREFERRED_MODELS:
        if model in available:
            return model
    for model in available:
        if not any(x in model for x in ("whisper", "tts", "guard", "playai", "orpheus")):
            return model
    print("No usable chat model found for this key")
    sys.exit(1)


def summarize(name, headlines, api_key, model):
    prompt = (
        f"Žemiau pateikiamos naujausios naujienų antraštės su nuorodomis (tema: {name}). "
        "Parašyk trumpą naujienų santrauką LIETUVIŲ KALBA: 5-7 punktai, "
        "kiekvienas punktas - vienas aiškus, taisyklingas sakinys. "
        "Antraštes, kurios yra kita kalba, išversk į lietuvių kalbą. "
        "Kiekvieno punkto gale įdėk šaltinio nuorodą markdown formatu, pvz. [šaltinis](url). "
        "Praleisk pasikartojančias naujienas, o apie tą patį įvykį sujunk į vieną punktą. "
        "Rašyk tik lietuviškai, be įžangos ir be papildomų komentarų.\n\n"
        + "\n".join(headlines)
    )
    r = requests.post(
        f"{API}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    if r.status_code != 200:
        print(f"Groq error {r.status_code} (model {model}): {r.text}")
        sys.exit(1)
    return r.json()["choices"][0]["message"]["content"].strip()


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY is not set (add it under Settings > Secrets > Actions)")
        sys.exit(1)

    model = pick_model(api_key)
    print("Using model:", model)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [f"# Kas naujo\n\n*Atnaujinta: {now}*\n"]
    got_anything = False

    for name, cfg in SECTIONS.items():
        print(f"\n== {name} ==")
        headlines = get_headlines(cfg["feeds"])
        if headlines:
            body = summarize(name, headlines, api_key, model)
            got_anything = True
        else:
            body = "_Šią valandą naujienų gauti nepavyko._"
        parts.append(f"## {cfg['emoji']} {cfg['title']}\n\n{body}\n")

    if not got_anything:
        print("No headlines from any section, leaving news.md unchanged")
        sys.exit(1)

    with open("news.md", "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("\nnews.md updated")


if __name__ == "__main__":
    main()
