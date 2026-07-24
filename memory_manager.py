# ============================================================
#  memory_manager.py — mirrors qwen-agent pattern
# ============================================================
import os
from datetime import datetime
from config import MEMORY_FILE, TASKS_FILE, NOMADEX_FILE, AGENT_DIR


def _ensure_files_exist():
    os.makedirs(AGENT_DIR, exist_ok=True)
    for path, default in [
        (MEMORY_FILE,  open(os.path.join(AGENT_DIR, "memory.md")).read()
                       if os.path.exists(os.path.join(AGENT_DIR, "memory.md"))
                       else "# Memory\n\n## Cards\n- (none yet)\n"),
        (TASKS_FILE,   open(os.path.join(AGENT_DIR, "tasks.md")).read()
                       if os.path.exists(os.path.join(AGENT_DIR, "tasks.md"))
                       else "# Tasks\n\n## Active\n- (none yet)\n"),
        (NOMADEX_FILE, open(os.path.join(AGENT_DIR, "nomadex.md")).read()
                       if os.path.exists(os.path.join(AGENT_DIR, "nomadex.md"))
                       else "# Nomadex Notes\n\n## Style\n- Think in points value, not just prices\n"),
    ]:
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(default)


def load_all() -> dict[str, str]:
    _ensure_files_exist()
    result = {}
    for name, path in [
        ("memory",  MEMORY_FILE),
        ("tasks",   TASKS_FILE),
        ("nomadex", NOMADEX_FILE),
    ]:
        with open(path, "r") as f:
            result[name] = f.read()
    return result


def build_system_prompt(base_prompt: str) -> str:
    files = load_all()
    return f"""{base_prompt}

---

## Persistent Memory Files

### memory.md (cards, spend profile, points balances)
{files['memory']}

### tasks.md (active watches, alerts, follow-ups)
{files['tasks']}

### nomadex.md (agent reasoning notes)
{files['nomadex']}

---

At the END of every session, you MUST call update_memory_files to persist any changes.
Never skip this step.
"""


def write_files(memory=None, tasks=None, nomadex=None) -> str:
    _ensure_files_exist()
    updated = []
    for name, content, path in [
        ("memory",  memory,  MEMORY_FILE),
        ("tasks",   tasks,   TASKS_FILE),
        ("nomadex", nomadex, NOMADEX_FILE),
    ]:
        if content is not None:
            with open(path, "w") as f:
                stamp = f"<!-- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n"
                f.write(stamp + content.lstrip())
            updated.append(name)
    return f"Updated: {', '.join(updated)}" if updated else "Nothing to update."
