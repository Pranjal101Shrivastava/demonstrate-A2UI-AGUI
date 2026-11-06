"""A2UI · MIXED (hybrid) mode.

Catalog components + one HtmlFrame + buttons. When the user clicks, the
client sends an A2UI `action` message. The agent answers with
updateDataModel ONLY: the component tree is never resent, because in A2UI
structure and data travel separately.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import a2ui
from common.data import sales
from common.fixtures import a2ui_dashboard, a2ui_data, days_from
from common.llm import complete
from common.sandbox import check_html

TITLE = "Catalog + HtmlFrame; button actions answered with data-model updates only"
MODE = "mixed"
ALLOWED = {"set_days", "restock"}
STOCK = dict(sales()["stock"])  # server-side state the actions mutate

SYSTEM = (
    f"Emit A2UI {a2ui.VERSION} JSONL for surface 'cafe' with catalog {a2ui.CAFE_HTML_CATALOG}:\n"
    + a2ui.catalog_prompt(a2ui.CAFE_HTML_CATALOG)
    + "\nUse catalog components wherever possible and exactly one HtmlFrame for a custom visual. "
    "Add Buttons with action {name: set_days|restock, context: {...}}."
)


def scripted(prompt):
    return "\n".join(json.dumps(m) for m in a2ui_dashboard(days_from(prompt), html=True, actions=True))


def messages_for(prompt):
    msgs, errs = a2ui.parse_jsonl(complete(SYSTEM, prompt, scripted))
    errs += a2ui.validate(msgs)
    s = a2ui.Surface()
    for m in msgs:
        s.apply(m)
    for c in s.components.values():
        if c["component"] == "HtmlFrame":
            errs += check_html(str(s.resolve(c["html"])))
    if errs:
        raise ValueError("; ".join(errs))
    return msgs


def on_action(body):
    """Client -> agent: {"version", "action": {name, surfaceId, context}} -> data updates."""
    act = body.get("action", {})
    name, ctx = act.get("name"), act.get("context", {})
    if name not in ALLOWED:
        yield {"error": f"action {name!r} is not allowed"}
        return
    if name == "restock":
        STOCK[ctx.get("item", "beans_kg")] = STOCK.get(ctx.get("item", "beans_kg"), 0) + int(ctx.get("qty", 1))
        yield {"a2ui": a2ui.update_data("cafe", "/stock_rows", [[k, v] for k, v in STOCK.items()])}
    elif name == "set_days":
        d = a2ui_data(int(ctx.get("days", 7)), html=True, stock=STOCK)
        for path in ("title", "sales", "custom_html"):
            yield {"a2ui": a2ui.update_data("cafe", "/" + path, d[path])}


def stream(body):
    for m in messages_for(body.get("prompt", "")):
        yield {"a2ui": m}


ROUTES = {"stream": stream, "action": on_action}


def cli():
    prompt = "cafe dashboard for 7 days"
    msgs = messages_for(prompt)
    s = a2ui.Surface()
    for m in msgs:
        s.apply(m)
    print(f"user: {prompt}\n  {len(msgs)} messages, {len(s.components)} components, validation errors: {a2ui.validate(msgs)}")
    for label, action in [("click 'Reorder beans'", {"name": "restock", "surfaceId": "cafe", "context": {"item": "beans_kg", "qty": 5}}),
                          ("click 'Zoom to 3 days' inside HtmlFrame", {"name": "set_days", "surfaceId": "cafe", "context": {"days": 3}}),
                          ("forged action", {"name": "drop_tables", "surfaceId": "cafe", "context": {}})]:
        print(f"\n{label}: {json.dumps(action)}")
        for out in on_action({"version": a2ui.VERSION, "action": action}):
            if "a2ui" in out:
                b = out["a2ui"]["updateDataModel"]
                print(f"  updateDataModel  path={b['path']:<13} value={json.dumps(b['value'])[:80]}")
                s.apply(out["a2ui"])
            else:
                print("  ", out)
    print("\nafter actions:", s.get("/title"), "| stock:", s.get("/stock_rows"), "| components resent: 0")


if __name__ == "__main__":
    cli()
