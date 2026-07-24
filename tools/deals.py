# ============================================================
#  tools/deals.py — RSS deal aggregator
#  Pulls r/churning, ThePointsGuy, ViewFromTheWing
#  No API key required
# ============================================================
import json
import os
import feedparser
from datetime import datetime
from langchain.tools import tool
from config import OUTPUT_DIR

FEEDS = {
    "churning":    "https://www.reddit.com/r/churning/new/.rss",
    "awardtravel": "https://www.reddit.com/r/awardtravel/new/.rss",
    "tpg":         "https://thepointsguy.com/feed/",
    "vftw":        "https://viewfromthewing.com/feed/",
}

KEYWORDS = [
    "transfer bonus", "chase", "ultimate rewards", "sapphire",
    "australia", "sydney", "united", "aeroplan", "air canada",
    "double points", "bonus points", "award sale", "flash sale",
    "lax", "syd", "qantas", "air new zealand",
]


@tool
def fetch_deals(max_per_feed: int = 5) -> str:
    """
    Fetch the latest points/miles deals from Reddit and travel blogs.
    Filters for Chase UR, Australia routes, transfer bonuses, and award sales.
    Writes results to output/deals.json and returns a summary.
    """
    hits = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= max_per_feed:
                    break
                title = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                text = title + " " + summary
                if any(kw in text for kw in KEYWORDS):
                    hits.append({
                        "source":    source,
                        "title":     entry.get("title", ""),
                        "url":       entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "snippet":   entry.get("summary", "")[:200],
                    })
                    count += 1
        except Exception as e:
            hits.append({"source": source, "error": str(e)})

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "deals.json")
    with open(out_path, "w") as f:
        json.dump({"fetched_at": datetime.now().isoformat(), "deals": hits}, f, indent=2)

    if not hits:
        return "No matching deals found across feeds."
    lines = [f"Found {len(hits)} relevant deals — saved to output/deals.json\n"]
    for h in hits[:10]:
        lines.append(f"[{h.get('source','?').upper()}] {h.get('title','')}\n  {h.get('url','')}")
    return "\n".join(lines)
