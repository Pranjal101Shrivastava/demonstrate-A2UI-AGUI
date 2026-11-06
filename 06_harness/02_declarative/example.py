"""Harness · DECLARATIVE mode: render_ui(spec) with validation and self-correction.

render_ui validates the spec against the catalog. An invalid spec does not
crash the harness: the tool returns is_error with the exact errors, the model
reads them on its next step and sends a corrected spec.
"""
import pathlib, sys
_here = pathlib.Path(__file__).resolve()
sys.path[:0] = [str(_here.parents[2]), str(_here.parents[1])]  # repo root + 06_harness (for tools.py)

from common.agui import print_events
from common.catalog import catalog_prompt, validate_flat
from common.fixtures import dashboard_spec, days_from
from common.harness import Harness, ToolError, last_results, steps_since_user, text, tool_use
from tools import READ_SALES, terminal_surface

TITLE = "render_ui tool: catalog validation, errors returned to the model, corrected spec"
MODE = "declarative"
SYSTEM = "Campus Cafe agent. Read data, then call render_ui with a flat spec {root, elements} using ONLY:\n" + catalog_prompt()


def render_ui(spec):
    errors = validate_flat(spec)
    if errors:
        raise ToolError("invalid spec: " + "; ".join(errors))
    return {"rendered": len(spec["elements"]), "_render": {"kind": "spec", "spec": spec}}


TOOLS = {
    "read_sales": READ_SALES,
    "render_ui": ({"description": "Render a UI spec on the user's surfaces.", "input_schema": {"type": "object", "properties": {
        "spec": {"type": "object"}}, "required": ["spec"]}}, render_ui),
}


def policy(messages):
    step, prompt = steps_since_user(messages), messages[0]["content"]
    days = days_from(prompt)
    if step == 0:
        return {"content": [tool_use("read_sales", {"days": days})]}
    if step == 1:
        bad = dashboard_spec(days)
        bad["elements"]["chart"] = {"type": "Chart", "props": {"kind": "pie"}, "children": ["bars"]}  # hallucinated component
        return {"content": [text("Rendering a dashboard."), tool_use("render_ui", {"spec": bad})]}
    if step == 2 and last_results(messages)[0].get("is_error"):
        return {"content": [text("The catalog has no Chart; switching to a Card with a BarChart."), tool_use("render_ui", {"spec": dashboard_spec(days)})]}
    return {"content": [text("Your dashboard is ready.")]}


def run(body, surfaces=()):
    yield from Harness(SYSTEM, TOOLS, policy, surfaces).run(body.get("prompt", ""))


ROUTES = {"run": run}


def cli():
    print_events(run({"prompt": "build me a dashboard for 5 days"}, surfaces=[terminal_surface]))


if __name__ == "__main__":
    cli()
