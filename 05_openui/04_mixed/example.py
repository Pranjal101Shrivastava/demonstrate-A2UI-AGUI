"""OpenUI Lang · MIXED mode: primitives + one HtmlArtifact + Buttons.

The reply to a user action is just MORE PROGRAM TEXT: re-assigning an id
(`title = Text(...)`) replaces that node, so updates stream with the same
parser as the first render. Actions are allow-listed on the server.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.data import sales
from common.fixtures import custom_html, dashboard_spec, days_from
from common.llm import complete, stream_chunks
from common.openui import HTML_SIGNATURES, SIGNATURES, Program, from_spec
from common.sandbox import check_html

TITLE = "Primitives + HtmlArtifact; actions answered with re-assignments"
MODE = "mixed"
SIGS = dict(SIGNATURES, **HTML_SIGNATURES)
STOCK = dict(sales()["stock"])
SYSTEM = ("Write an OpenUI Lang program (root first, forward references allowed). Use HtmlArtifact once for a custom "
          "visual; everything else from:\n" + "\n".join(f"- {k}({', '.join(v)})" for k, v in SIGS.items())
          + '\nButtons: Button(label, "set_days"|"restock", {params}).')
ACTION_SYSTEM = "The user clicked {action} {params}. Reply ONLY with re-assignments of the ids that change."


def generate(prompt):
    text = complete(SYSTEM, prompt, lambda p: from_spec(dashboard_spec(days_from(p), hybrid=True)))
    prog = Program(SIGS)
    prog.feed(text)
    prog.close()
    errs = prog.validate()
    errs += [e for v in prog.defs.values() if isinstance(v, dict) and v.get("$call") == "HtmlArtifact" for e in check_html(v["args"][0])]
    if errs:
        raise ValueError("; ".join(errs))
    return text


def scripted_update(action, params):
    if action == "restock":
        STOCK[params.get("item", "beans_kg")] = STOCK.get(params.get("item", "beans_kg"), 0) + int(params.get("qty", 1))
        return f'stock = Table(["Item", "Qty"], {json.dumps([[k, v] for k, v in STOCK.items()])})\n'
    s = sales(int(params.get("days", 7)))
    return (f'title = Text("Campus Cafe - last {s["days"]} days", "h1")\n'
            f'm_cups = Metric("Cups sold", {s["total_cups"]})\n'
            f'm_rev = Metric("Revenue", "${s["total_revenue"]:.2f}")\n'
            f'bars = BarChart({json.dumps(s["labels"])}, {json.dumps(s["cups"])})\n'
            f'custom = HtmlArtifact({json.dumps(custom_html(s["days"]))}, 230)\n')


def update(action, params):
    if action not in ("set_days", "restock"):
        raise ValueError(f"action {action!r} is not allowed")
    text = complete(ACTION_SYSTEM.format(action=action, params=json.dumps(params)), action, lambda _: scripted_update(action, params))
    check = Program(SIGS)
    check.feed(text)
    check.close()
    if check.errors:
        raise ValueError("; ".join(check.errors))
    return text


def stream(body):
    for c in stream_chunks(generate(body.get("prompt", "")), 60):
        yield {"text": c}
    yield {"end": True}


def on_action(body):
    try:
        text = update(body.get("action"), body.get("params", {}))
    except ValueError as e:
        yield {"error": str(e)}
        return
    for c in stream_chunks(text, 60):
        yield {"text": c}
    yield {"end": True}


ROUTES = {"stream": stream, "action": on_action}


def cli():
    prog = Program(SIGS)
    prog.feed(generate("dashboard for 7 days"))
    prog.close()
    print(f"initial program: {len(prog.defs)} statements, errors {prog.validate()}")
    print("title:", prog.tree("title")["props"]["text"])
    upd = update("set_days", {"days": 3})
    print("\nclick [Last 3 days] -> model replies with re-assignments only:\n" + "\n".join("  " + l[:100] for l in upd.splitlines()))
    prog.feed(upd)
    print("title now:", prog.tree("title")["props"]["text"], "| total statements still", len(prog.defs))
    try:
        update("format_disk", {})
    except ValueError as e:
        print("forged action:", e)


if __name__ == "__main__":
    cli()
