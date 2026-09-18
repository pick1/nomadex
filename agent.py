#!/usr/bin/env python3
# ============================================================
#  agent.py — Nomadex: travel intelligence + points optimizer
#  Mirrors qwen-agent architecture exactly
# ============================================================
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
import time
import json
import readline
import atexit
import os
import asyncio
import threading
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.rule import Rule

from config import MODEL, OLLAMA_BASE_URL, TEMPERATURE, USE_XAVIER, XAVIER_BASE_URL, XAVIER_MODEL, OUTPUT_DIR
from memory_manager import build_system_prompt
from tools import ALL_TOOLS

if USE_XAVIER:
    from langchain_openai import ChatOpenAI
else:
    from langchain_ollama import ChatOllama

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

_HISTORY_FILE = os.path.expanduser("~/.nomadex_history")
try:
    readline.read_history_file(_HISTORY_FILE)
except FileNotFoundError:
    pass
readline.set_history_length(500)
atexit.register(readline.write_history_file, _HISTORY_FILE)

console = Console()

BASE_PROMPT = """You are Nomadex, a travel intelligence and points optimization agent running locally on floorBoard.

Your job:
- Monitor credit card points deals, transfer bonuses, and award sales
- Track Chase Ultimate Rewards balance and project EOY totals
- Find the best way to book LAX→SYD for 4 people using points or cash
- Compare OTA prices vs direct booking to eliminate Expedia/Airbnb fees
- Alert the user to actionable opportunities

Primary goal: accumulate enough Chase UR points for 4 economy round-trip tickets
LAX→SYD (need ~140,000–200,000 pts total) by EOY or beyond.

IMPORTANT:
- Always be honest about what you know vs what you're estimating
- When fetching deals, summarize only what's actually relevant to Chase UR / Australia routes
- Output/ directory is read by Voyager dashboard — keep JSON files clean

You have persistent memory across sessions. Read your memory files carefully."""


class AgentStatus:
    def __init__(self):
        self.state = "idle"
        self.current_tool = None
        self.steps = []
        self.start_time = None
        self.turn_count = 0

    def reset_turn(self):
        self.state = "thinking"
        self.current_tool = None
        self.steps = []
        self.start_time = datetime.now()
        self.turn_count += 1

    def tool_call(self, name, inp):
        self.state = "tool"
        self.current_tool = name
        self._tool_inp = inp[:80] + "…" if len(inp) > 80 else inp

    def tool_done(self, name, result):
        self.state = "thinking"
        preview = result[:60] + "…" if len(result) > 60 else result
        self.steps.append({"tool": name, "result": preview})
        self.current_tool = None

    def done(self):
        self.state = "done"

    def elapsed(self):
        if not self.start_time:
            return "0s"
        return f"{(datetime.now() - self.start_time).seconds}s"

    def render(self):
        model_name = XAVIER_MODEL if USE_XAVIER else MODEL
        t = Table.grid(padding=(0, 2))
        t.add_column(style="bold")
        t.add_column()
        t.add_row("model",  f"[cyan]{model_name}[/]")
        t.add_row("state",  f"[yellow]{self.state}[/]")
        t.add_row("turn",   str(self.turn_count))
        t.add_row("time",   self.elapsed())
        if self.current_tool:
            t.add_row("tool", f"[magenta]{self.current_tool}[/]")
        for step in self.steps[-3:]:
            t.add_row(f"  ✓ {step['tool']}", f"[dim]{step['result']}[/]")
        return Panel(t, title="[bold gold1]nomadex[/]", border_style="gold1")


status = AgentStatus()


def make_llm():
    if USE_XAVIER:
        return ChatOpenAI(
            base_url=XAVIER_BASE_URL,
            api_key="nomadex",
            model=XAVIER_MODEL,
            temperature=TEMPERATURE,
        )
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=MODEL,
        temperature=TEMPERATURE,
    )


async def run_agent():
    llm      = make_llm()
    sys_prompt = build_system_prompt(BASE_PROMPT)
    agent    = create_react_agent(llm, ALL_TOOLS)
    history  = []

    console.print(Rule("[bold gold1]NOMADEX[/] — travel intelligence + points optimizer"))
    console.print("[dim]Type your request. 'exit' to quit and save memory.[/]\n")

    while True:
        try:
            user_input = input("[bold]you[/] › ").strip()
        except (EOFError, KeyboardInterrupt):
            user_input = "exit"

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            console.print("\n[dim]Saving memory and exiting…[/]")
            # Trigger memory save
            history.append(HumanMessage(content="Save your memory files and exit."))
            messages = [SystemMessage(content=sys_prompt)] + history
            result = await agent.ainvoke({"messages": messages})
            console.print("[green]Memory saved. Goodbye.[/]")
            break

        history.append(HumanMessage(content=user_input))
        messages = [SystemMessage(content=sys_prompt)] + history

        status.reset_turn()
        response_text = ""

        done_event = threading.Event()

        def _tick(live):
            while not done_event.is_set():
                live.update(status.render())
                time.sleep(0.25)

        with Live(status.render(), refresh_per_second=4, console=console) as live:
            ticker = threading.Thread(target=_tick, args=(live,), daemon=True)
            ticker.start()
            try:
                result = await agent.ainvoke({"messages": messages})
                for msg in result["messages"]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            status.tool_call(tc["name"], str(tc.get("args", "")))
                    if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
                         response_text = msg.content
                status.done()
            except Exception as e:
                response_text = f"[red]Error: {e}[/]"
                status.done()
            finally:
                done_event.set()


        console.print(f"\n[bold gold1]nomadex[/] › {response_text}\n")
        history.append(AIMessage(content=response_text))


#if __name__ == "__main__":
#    asyncio.run(run_agent())

if __name__ == "__main__":
    import sys
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
╔══════════════════════════════════════════════════════════════╗
║  NOMADEX — travel intelligence + points optimizer            ║
╠══════════════════════════════════════════════════════════════╣
║  DEALS & ALERTS                                              ║
║  > fetch the latest deals                                    ║
║  > are there any Chase transfer bonuses live right now       ║
║  > any award sales on LAX to Sydney                         ║
║                                                              ║
║  POINTS PLANNING                                             ║
║  > project my points by EOY                                  ║
║  > how many points for 4 economy tickets to Sydney           ║
║  > update my points balance to 45000                         ║
║                                                              ║
║  FLIGHTS                                                     ║
║  > search flights LAX to Sydney in March for 4 people        ║
║  > watch LAX to SYD alert me below $900 per person           ║
║                                                              ║
║  KNOWLEDGE BASE                                              ║
║  > fetch the article at <url>                                ║
║  > what does my knowledge base say about Aeroplan            ║
║  > embed all saved articles                                  ║
║  > list my saved articles                                    ║
║                                                              ║
║  STRATEGY                                                    ║
║  > what's the best card for groceries                        ║
║  > is Plastiq worth it for my mortgage                       ║
║  > what transfer partner gives best value for Sydney         ║
║                                                              ║
║  Type 'exit' to quit and save memory.                        ║
╚══════════════════════════════════════════════════════════════╝
""")
        sys.exit(0)
    asyncio.run(run_agent())
