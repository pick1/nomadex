# ============================================================
#  config.py — nomadex configuration
# ============================================================
import os

AGENT_DIR       = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE     = os.path.join(AGENT_DIR, "memory.md")
TASKS_FILE      = os.path.join(AGENT_DIR, "tasks.md")
NOMADEX_FILE    = os.path.join(AGENT_DIR, "nomadex.md")
OUTPUT_DIR      = os.path.join(AGENT_DIR, "output")

# ── Model config (mirrors qwen-agent pattern) ────────────────
USE_XAVIER      = os.getenv("USE_XAVIER", "false").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
XAVIER_BASE_URL = os.getenv("XAVIER_BASE_URL", "http://192.168.1.110:8080/v1")
MODEL = os.getenv("NOMADEX_MODEL", "hf.co/unsloth/Ornith-1.0-9B-GGUF:Q6_K")
XAVIER_MODEL    = os.getenv("XAVIER_MODEL",  "gpt-oss-20b")
TEMPERATURE     = float(os.getenv("NOMADEX_TEMP", "0.3"))

# ── API keys (set in environment or .env) ────────────────────
SERPAPI_KEY     = os.getenv("SERPAPI_KEY", "")
MAKECORPS_KEY   = os.getenv("MAKECORPS_KEY", "")

# ── Trip context ─────────────────────────────────────────────
ORIGIN          = "LAX"
DESTINATION     = "SYD"
PARTY_SIZE      = 4
POINTS_GOAL_EOY = 200000   # economy for 4 LAX→SYD round trip
