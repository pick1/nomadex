# nomadex

Travel intelligence + points optimization agent for floorBoard.
Mirrors the qwen-agent architecture — same LangGraph ReAct loop,
same persistent memory pattern, new domain-specific tools.

## Quick start

```bash
cd ~/projects/nomadex
pip install -r requirements.txt
python agent.py
```

## Environment variables

```bash
export SERPAPI_KEY=your_key      # free tier at serpapi.com — enables flight search
export USE_XAVIER=true           # route to Jetson for batch tasks
```

## Tools

| Tool | What it does |
|---|---|
| `fetch_deals` | RSS from r/churning, TPG, VFTW — filters for Chase UR + Australia |
| `search_flights` | Google Flights via SerpApi — LAX→SYD prices |
| `watch_route` | Add price alert to output/flight_watch.json |
| `calc_points_vs_cash` | Compare points vs cash for 4 tickets |
| `update_points_balance` | Record current balance, project EOY total |
| `project_points` | Estimate earn by EOY from monthly spend |

## Output → Voyager bridge

Nomadex writes structured JSON to `output/` — Voyager reads from there.

```
output/
  deals.json          ← live deal feed results
  flight_watch.json   ← LAX→SYD price history + watches
  points_state.json   ← balance, goal gap, projection
  direct_finds.json   ← OTA vs direct savings (future)
```

## Memory files

- `memory.md` — cards, spend profile, trip goal
- `tasks.md` — active watches and follow-ups
- `nomadex.md` — agent reasoning notes
