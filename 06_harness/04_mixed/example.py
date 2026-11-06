"""Harness · MIXED mode: hybrid UI + human-in-the-loop.

render_ui accepts catalog components plus one GeneratedView. The harness
keeps the conversation per thread, so a click on the web surface (catalog
button or genux.action() inside the sandbox) becomes a NEW USER TURN:
"[ui action] restock {...}". The model then calls a real side-effect tool
(restock) and re-renders. Unknown actions are refused before the model sees them.
"""
import pathlib, sys
_here = pathlib.Path(__file__).resolve()
sys.path[:0] = [str(_here.parents[2]), str(_here.parents[1])]  # repo root + 06_harness (for tools.py)
import json

from common.agui import print_events
from common.catalog import catalog_prompt, validate_flat
from common.data import sales
from common.fixtures import dashboard_spec, days_from
from common.harness import Harness, ToolError, result_json, steps_since_user, text, tool_use
from common.sandbox import check_html
from tools import READ_SALES, terminal_surface

TITLE = "Hybrid render_ui; UI actions re-enter the agent loop as user turns"
MODE = "mixed"
SYSTEM = ("Campus Cafe agent. Render with render_ui using these components (GeneratedView once, for a custom visual):\n"
          + catalog_prompt(extra=True) + "\nMessages starting with [ui action] are clicks on the UI.")
STOCK = dict(sales()["stock"])
ALLOWED = {"set_days", "restock"}


def render_ui(spec):
    errors = validate_flat(spec, extra=True)
    errors += [e for el in spec.get("elements", {}).values() if el.get("type") == "GeneratedView" for e in check_html(el["props"].get("html", ""))]
    if errors:
        raise ToolError("invalid spec: " + "; ".join(errors))
    return {"rendered": len(spec["elements"]), "_render": {"kind": "spec", "spec": spec}}


def restock(item, qty):
    if item not in STOCK or not 0 < qty <= 20:
        raise ToolError("restock needs a known item and 1-20 units")
    STOCK[item] += qty
    return {"stock": dict(STOCK)}


TOOLS = {
    "read_sales": READ_SALES,
    "restock": ({"description": "Order more of a stock item.", "input_schema": {"type": "object", "properties": {
        "item": {"type": "string"}, "qty": {"type": "integer"}}, "required": ["item", "qty"]}}, restock),
    "render_ui": ({"description": "Render a hybrid UI spec.", "input_schema": {"type": "object", "properties": {
        "spec": {"type": "object"}}, "required": ["spec"]}}, render_ui),
}


def spec_for(days):
    spec = dashboard_spec(days, hybrid=True)
    spec["elements"]["stock"]["props"]["rows"] = [[k, v] for k, v in STOCK.items()]
    return spec


def policy(messages):
    step = steps_since_user(messages)
    user = next(m["content"] for m in reversed(messages) if m["role"] == "user" and isinstance(m["content"], str))
    if user.startswith("[ui action]"):
        _, _, name, params = user.split(" ", 3)
        params = json.loads(params)
        if name == "restock":
            if step == 0:
                return {"content": [tool_use("restock", params)]}
            if step == 1:
                return {"content": [tool_use("render_ui", {"spec": spec_for(7)})]}
            return {"content": [text(f"Ordered {params['qty']} {params['item']}; stock is now {STOCK[params['item']]}.")]}
        if step == 0:
            return {"content": [tool_use("render_ui", {"spec": spec_for(params["days"])})]}
        return {"content": [text(f"Now showing {params['days']} days.")]}
    if step == 0:
        return {"content": [tool_use("read_sales", {"days": days_from(user)})]}
    if step == 1:
        return {"content": [tool_use("render_ui", {"spec": spec_for(result_json(messages)["days"])})]}
    return {"content": [text("Dashboard ready - try the buttons or the custom chart.")]}


SESSIONS = {}  # threadId -> Harness (conversation memory across UI actions)


def session(thread, surfaces=()):
    if thread not in SESSIONS:
        SESSIONS[thread] = Harness(SYSTEM, TOOLS, policy, surfaces)
    return SESSIONS[thread]


def run(body, surfaces=()):
    SESSIONS.pop(body.get("threadId", "cli"), None)
    yield from session(body.get("threadId", "cli"), surfaces).run(body.get("prompt", ""))


def on_action(body):
    name, params = body.get("action"), body.get("params", {})
    if name not in ALLOWED:
        yield {"type": "RUN_ERROR", "message": f"action {name!r} is not allowed"}
        return
    yield from session(body.get("threadId", "cli")).run(f"[ui action] {name} {json.dumps(params)}")


ROUTES = {"run": run, "action": on_action}


def cli():
    print("user: dashboard for 7 days")
    print_events(run({"threadId": "cli", "prompt": "dashboard for 7 days"}, surfaces=[terminal_surface]))
    print("\nuser clicks [Reorder beans]")
    print_events(on_action({"threadId": "cli", "action": "restock", "params": {"item": "beans_kg", "qty": 5}}))
    print("\nforged click:")
    print_events(on_action({"threadId": "cli", "action": "rm_rf", "params": {}}))
    print("\nconversation length kept by the harness:", len(SESSIONS["cli"].messages), "messages")


if __name__ == "__main__":
    cli()
