"""AG-UI · STATIC mode.

The frontend already owns three hand-written components. The model only
CHOOSES one (as a tool call) and supplies its arguments. AG-UI carries that
choice to the page as TOOL_CALL_START / TOOL_CALL_ARGS / TOOL_CALL_END events,
and the page maps toolCallName -> component.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import agui
from common.data import sales
from common.fixtures import days_from
from common.llm import complete, stream_chunks, strip_fences

TITLE = "Agent picks a prebuilt component via a tool call"
MODE = "static"

# The three "frontend tools": the only UI the model may ask for.
TOOLS = {
    "show_sales_card": "Summary card with cups, revenue and best day. args: {days: 1-7}",
    "show_sales_chart": "Bar chart of cups per day. args: {days: 1-7}",
    "show_stock_table": "Table of current stock levels. args: {}",
}

SYSTEM = (
    "You are the Campus Cafe assistant. Choose exactly ONE UI tool for the user's request.\n"
    + "\n".join(f"- {k}: {v}" for k, v in TOOLS.items())
    + '\nReply with JSON only: {"say": "<one short sentence>", "tool": "<name>", "args": {...}}'
)


def scripted(prompt: str) -> str:
    p = prompt.lower()
    if "stock" in p or "inventory" in p:
        choice = {"say": "Here is the current stock.", "tool": "show_stock_table", "args": {}}
    elif "chart" in p or "trend" in p:
        choice = {"say": "Here is the daily chart.", "tool": "show_sales_chart", "args": {"days": days_from(p)}}
    else:
        choice = {"say": "Here is your sales summary.", "tool": "show_sales_card", "args": {"days": days_from(p)}}
    return json.dumps(choice)


def run(run_input: dict):
    thread, run_id = run_input.get("threadId", "t1"), run_input.get("runId", agui.new_id("run"))
    yield agui.run_started(thread, run_id)
    prompt = agui.last_user_text(run_input)
    choice = json.loads(strip_fences(complete(SYSTEM, prompt, scripted)))
    if choice.get("tool") not in TOOLS:  # never render something the frontend did not ship
        yield agui.run_error(f"model chose unknown tool {choice.get('tool')!r}")
        return
    yield from agui.text_message(choice.get("say", ""), stream_chunks)
    args = choice.get("args", {})
    data = sales(args.get("days", 7))
    yield from agui.tool_call(choice["tool"], args, lambda s: stream_chunks(s, 6), result=data)
    yield agui.run_finished(thread, run_id)


ROUTES = {"run": run}


def cli():
    for prompt in ["show me sales for the last 5 days", "what does our stock look like?", "chart the trend for 7 days"]:
        print(f"\nuser: {prompt}")
        agui.print_events(run({"threadId": "t1", "runId": "r1", "messages": [{"role": "user", "content": prompt}]}))


if __name__ == "__main__":
    cli()
