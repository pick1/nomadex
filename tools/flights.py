# ============================================================
#  tools/flights.py — SerpApi Google Flights search
#  Set SERPAPI_KEY env var to enable
# ============================================================
import json
import os
from datetime import datetime
from langchain.tools import tool
from config import OUTPUT_DIR, SERPAPI_KEY, ORIGIN, DESTINATION


@tool
def search_flights(
    origin: str = "LAX",
    destination: str = "SYD",
    outbound_date: str = "",
    return_date: str = "",
    adults: int = 4,
) -> str:
    """
    Search Google Flights via SerpApi for cash prices on a route.
    Requires SERPAPI_KEY environment variable.
    Returns price summary and saves to output/flight_watch.json.
    """
    if not SERPAPI_KEY:
        return (
            "SERPAPI_KEY not set. Get a free key at https://serpapi.com "
            "then: export SERPAPI_KEY=your_key"
        )
    try:
        from serpapi import GoogleSearch
    except ImportError:
        return "Run: pip install google-search-results"

    params = {
        "engine":          "google_flights",
        "departure_id":    origin or ORIGIN,
        "arrival_id":      destination or DESTINATION,
        "outbound_date":   outbound_date or "",
        "return_date":     return_date or "",
        "adults":          adults,
        "currency":        "USD",
        "hl":              "en",
        "api_key":         SERPAPI_KEY,
    }

    search  = GoogleSearch(params)
    results = search.get_dict()

    best = results.get("best_flights", []) or results.get("other_flights", [])
    if not best:
        return "No flights found for those parameters."

    summary = []
    records = []
    for flight in best[:5]:
        price    = flight.get("price", "?")
        duration = flight.get("total_duration", "?")
        airline  = flight.get("flights", [{}])[0].get("airline", "?")
        summary.append(f"  {airline}: ${price} | {duration} min")
        records.append({"airline": airline, "price": price, "duration_min": duration})

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "flight_watch.json")
    existing = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            existing = json.load(f)
    history = existing.get("history", [])
    history.append({
        "checked_at": datetime.now().isoformat(),
        "route":      f"{origin}→{destination}",
        "adults":     adults,
        "results":    records,
    })
    with open(out_path, "w") as f:
        json.dump({"history": history}, f, indent=2)

    lines = [f"Flights {origin}→{destination} (×{adults} adults):"]
    lines += summary
    lines.append(f"\nSaved to output/flight_watch.json")
    return "\n".join(lines)


@tool
def watch_route(
    origin: str = "LAX",
    destination: str = "SYD",
    target_price_usd: int = 900,
    note: str = "",
) -> str:
    """
    Add a route to the price watch list in output/flight_watch.json.
    Nomadex will alert you when prices drop below target.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "flight_watch.json")
    existing = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            existing = json.load(f)
    watches = existing.get("watches", [])
    watches.append({
        "route":            f"{origin}→{destination}",
        "target_price_usd": target_price_usd,
        "added_at":         datetime.now().isoformat(),
        "note":             note,
    })
    existing["watches"] = watches
    with open(out_path, "w") as f:
        json.dump(existing, f, indent=2)
    return f"Watching {origin}→{destination} — alert below ${target_price_usd}/person. Saved."
