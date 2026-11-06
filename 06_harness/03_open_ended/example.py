"""Harness · OPEN-ENDED mode: render_html(html).

The model writes HTML as a tool argument. The tool enforces the content
policy; the web surface mounts it in a sandboxed iframe; the terminal surface
can only say that a custom view exists. If the policy rejects the HTML, the
model gets the reason and can retry.
"""
import pathlib, sys
_here = pathlib.Path(__file__).resolve()
sys.path[:0] = [str(_here.parents[2]), str(_here.parents[1])]  # repo root + 06_harness (for tools.py)

from common.agui import print_events
from common.fixtures import custom_html, days_from
from common.harness import Harness, ToolError, last_results, steps_since_user, text, tool_use
from common.sandbox import check_html
from tools import READ_SALES, terminal_surface

TITLE = "render_html tool: policy-checked HTML, sandboxed on the web surface"
MODE = "open-ended"
SYSTEM = "Campus Cafe agent. Read data, then call render_html with a self-contained HTML fragment (no URLs, fetch or storage)."


def render_html(html):
    problems = check_html(html)
    if problems:
        raise ToolError("HTML rejected: " + "; ".join(problems))
    return {"rendered_bytes": len(html), "_render": {"kind": "html", "html": html}}


TOOLS = {
    "read_sales": READ_SALES,
    "render_html": ({"description": "Render a custom HTML view (sandboxed).", "input_schema": {"type": "object", "properties": {
        "html": {"type": "string"}}, "required": ["html"]}}, render_html),
}


def policy(messages):
    step, days = steps_since_user(messages), days_from(messages[0]["content"])
    if step == 0:
        return {"content": [tool_use("read_sales", {"days": days})]}
    if step == 1:  # first try loads a charting library from a CDN - the policy blocks it
        return {"content": [tool_use("render_html", {"html": '<script src="https://cdn.example/chart.js"></script><canvas id=c></canvas>'})]}
    if step == 2 and last_results(messages)[0].get("is_error"):
        return {"content": [text("No external scripts allowed - drawing it with inline SVG instead."), tool_use("render_html", {"html": custom_html(days)})]}
    return {"content": [text("Custom revenue view rendered.")]}


def run(body, surfaces=()):
    yield from Harness(SYSTEM, TOOLS, policy, surfaces).run(body.get("prompt", ""))


ROUTES = {"run": run}


def cli():
    print_events(run({"prompt": "make a custom revenue visual for 7 days"}, surfaces=[terminal_surface]))


if __name__ == "__main__":
    cli()
