from tools.deals    import fetch_deals
from tools.flights  import search_flights, watch_route
from tools.points   import calc_points_vs_cash, update_points_balance, project_points
from tools.articles import fetch_article, list_knowledge, embed_articles, query_knowledge

ALL_TOOLS = [
    fetch_deals,
    search_flights,
    watch_route,
    calc_points_vs_cash,
    update_points_balance,
    project_points,
    fetch_article,
    list_knowledge,
    embed_articles,
    query_knowledge,
]

from langchain.tools import tool
import os

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@tool
def append_task(task: str) -> str:
    """
    Append a single task or note to tasks.md.
    Use this when the user says 'save this', 'add to tasks', or 'remember this'.
    Args:
        task: The task or note to append
    """
    path = os.path.join(AGENT_DIR, "tasks.md")

    with open(path, "r") as f:
        content = f.read()
    insertion = f"- [ ] {task}\n"
    if "## Active" in content:
        content = content.replace("## Active\n", f"## Active\n{insertion}")
    else:
        content += f"\n{insertion}"
    with open(path, "w") as f:
        f.write(content)
    return f"Saved to tasks.md: {task}"

ALL_TOOLS.append(append_task)
