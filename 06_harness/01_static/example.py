"""Harness · STATIC mode: the agent loop gets a show_component tool.

Its input is restricted to an enum of three prebuilt components. The loop:
read_sales -> show_component -> final text. The render goes to BOTH surfaces:
the terminal (tools.terminal_surface) and the web page (AG-UI CUSTOM event).
"""
import pathlib, sys
_here = pathlib.Path(__file__).resolve()
sys.path[:0] = [str(_here.parents[2]), str(_here.parents[1])]  # repo root + 06_harness (for tools.py)

from common.harness import Harness, ToolError, result_json, steps_since_user, text, tool_use
from common.fixtures import days_from
from common.agui import print_events
from tools import READ_SALES, terminal_surface

TITLE = "Agent loop with a show_component tool (enum of prebuilt components)"
MODE = "static"
COMPONENTS = {"SalesCard": ["title", "cups", "revenue", "best"], "CupsChart": ["labels", "values"], "StockTable": ["rows"]}
SYSTEM = "You are the Campus Cafe agent. Read data with read_sales, then show it with show_component, then answer in one sentence."


def show_component(name, props):
    if name not in COMPONENTS:
        raise ToolError(f"unknown component {name!r}; choose one of {list(COMPONENTS)}")
    missing = [p for p in COMPONENTS[name] if p not in props]
    if missing:
        raise ToolError(f"{name} is missing props {missing}")
    return {"shown": name, "_render": {"kind": "component", "name": name, "props": props}}


TOOLS = {
    "read_sales": READ_SALES,
    "show_component": ({"description": "Show one prebuilt UI component.", "input_schema": {"type": "object", "properties": {
        "name": {"type": "string", "enum": list(COMPONENTS)}, "props": {"type": "object"}}, "required": ["name", "props"]}}, show_component),
}


def policy(messages):
    """Scripted model: what Claude would do, step by step."""
    step, prompt = steps_since_user(messages), messages[0]["content"]
    if step == 0:
        return {"content": [text("Let me read the sales first."), tool_use("read_sales", {"days": days_from(prompt)})]}
    if step == 1:
        s = result_json(messages)
        if "chart" in prompt.lower():
            return {"content": [tool_use("show_component", {"name": "CupsChart", "props": {"labels": s["labels"], "values": s["cups"]}})]}
        return {"content": [tool_use("show_component", {"name": "SalesCard", "props": {"title": f"Last {s['days']} days", "cups": s["total_cups"], "revenue": f"${s['total_revenue']:.2f}", "best": s["best_day"]}})]}
    return {"content": [text("Done - the summary card is on screen.")]}


def run(body, surfaces=()):
    yield from Harness(SYSTEM, TOOLS, policy, surfaces).run(body.get("prompt", ""))


ROUTES = {"run": run}


def cli():
    print_events(run({"prompt": "summarise sales for the last 5 days"}, surfaces=[terminal_surface]))


if __name__ == "__main__":
    cli()
