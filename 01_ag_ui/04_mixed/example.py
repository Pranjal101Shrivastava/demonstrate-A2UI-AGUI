"""AG-UI · MIXED (hybrid) mode.

Catalog components for everything the catalog can express, plus ONE
`GeneratedView` region holding model-written HTML (sandboxed). User actions
close the loop: a click starts a new run whose RunAgentInput carries
forwardedProps.action; the agent checks it against an allow-list and answers
with STATE_DELTA patches instead of rebuilding the page.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import agui
from common.catalog import catalog_prompt, validate_flat
from common.data import sales
from common.fixtures import custom_html, dashboard_spec, days_from
from common.llm import complete, stream_chunks, strip_fences
from common.sandbox import check_html

TITLE = "Catalog + one sandboxed GeneratedView, with actions round-tripping as new runs"
MODE = "mixed"

ALLOWED_ACTIONS = {"set_days", "restock"}
SYSTEM = (
    "Build a Campus Cafe dashboard from these components (GeneratedView is the ONLY place for custom HTML, "
    "use it once, for a visual the catalog lacks):\n" + catalog_prompt(extra=True)
    + '\nReturn JSON only: {"root", "elements"}.'
)


def scripted(prompt: str) -> str:
    return json.dumps(dashboard_spec(days_from(prompt), hybrid=True))


def build(run_input):
    spec = json.loads(strip_fences(complete(SYSTEM, agui.last_user_text(run_input), scripted)))
    errors = validate_flat(spec, extra=True)
    for eid, el in spec["elements"].items():
        if el["type"] == "GeneratedView":
            errors += [f"{eid}: {p}" for p in check_html(el["props"]["html"])]
    if errors:
        yield agui.run_error("invalid UI spec: " + "; ".join(errors[:5]))
        return
    yield from agui.text_message("Here is your dashboard. The trend panel is a custom view.", stream_chunks)
    yield agui.state_snapshot({"ui": {"root": spec["root"], "elements": {}}, "stock": sales()["stock"]})
    for eid, el in spec["elements"].items():
        yield agui.state_delta([{"op": "add", "path": f"/ui/elements/{eid}", "value": el}])


def handle_action(action, params, state):
    """Respond to a user action with small patches, not a new page."""
    if action not in ALLOWED_ACTIONS:
        yield agui.run_error(f"action {action!r} is not allowed")
        return
    if action == "set_days":
        days = max(1, min(7, int(params.get("days", 7))))
        s = sales(days)
        yield from agui.text_message(f"Showing the last {days} days.", stream_chunks)
        yield agui.state_delta([
            {"op": "replace", "path": "/ui/elements/title/props/text", "value": f"Campus Cafe - last {days} days"},
            {"op": "replace", "path": "/ui/elements/m_cups/props/value", "value": s["total_cups"]},
            {"op": "replace", "path": "/ui/elements/m_rev/props/value", "value": f"${s['total_revenue']:.2f}"},
            {"op": "replace", "path": "/ui/elements/m_best/props/value", "value": s["best_day"]},
            {"op": "replace", "path": "/ui/elements/bars/props", "value": {"labels": s["labels"], "values": s["cups"]}},
            {"op": "replace", "path": "/ui/elements/custom/props/html", "value": custom_html(days)},
        ])
    elif action == "restock":
        stock = dict(state.get("stock") or sales()["stock"])
        item, qty = params.get("item", "beans_kg"), int(params.get("qty", 1))
        stock[item] = stock.get(item, 0) + qty
        yield from agui.text_message(f"Ordered {qty} more {item}.", stream_chunks)
        yield agui.state_delta([
            {"op": "replace", "path": "/stock", "value": stock},
            {"op": "replace", "path": "/ui/elements/stock/props/rows", "value": [[k, v] for k, v in stock.items()]},
        ])


def run(run_input: dict):
    thread, run_id = run_input.get("threadId", "t1"), run_input.get("runId", agui.new_id("run"))
    yield agui.run_started(thread, run_id)
    action = (run_input.get("forwardedProps") or {}).get("action")
    if action:
        body = handle_action(action["name"], action.get("params", {}), run_input.get("state", {}))
    else:
        body = build(run_input)
    yield from agui.guarded(body, thread, run_id)  # RUN_ERROR or RUN_FINISHED ends the run, never both


ROUTES = {"run": run}


def cli():
    from common.jsonpatch import apply_patch
    state = {}

    def go(run_input, label):
        nonlocal state
        print(f"\n{label}")
        events = list(run(run_input))
        agui.print_events(events)
        for e in events:
            if e["type"] == "STATE_SNAPSHOT":
                state = e["snapshot"]
            elif e["type"] == "STATE_DELTA":
                state = apply_patch(state, e["delta"])

    go({"messages": [{"role": "user", "content": "dashboard for 7 days with a custom trend"}]}, "user: dashboard for 7 days with a custom trend")
    go({"state": state, "forwardedProps": {"action": {"name": "restock", "params": {"item": "beans_kg", "qty": 5}}}}, "click: Reorder beans")
    print("stock after restock:", state["stock"])
    go({"state": state, "forwardedProps": {"action": {"name": "set_days", "params": {"days": 3}}}}, "click (inside sandboxed view): Zoom to 3 days")
    print("title now:", state["ui"]["elements"]["title"]["props"]["text"])
    go({"state": state, "forwardedProps": {"action": {"name": "delete_everything"}}}, "forged action from a compromised iframe:")


if __name__ == "__main__":
    cli()
