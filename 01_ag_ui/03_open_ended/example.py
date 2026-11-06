"""AG-UI · OPEN-ENDED mode.

No catalog: the model writes HTML. The agent checks it against a content
policy (common/sandbox.py) and streams it as the arguments of a `render_html`
tool call. The page assembles the streamed TOOL_CALL_ARGS and mounts the HTML
in a sandboxed iframe with a no-network CSP (common/web/sandbox.js).
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import agui
from common.fixtures import custom_html, days_from
from common.llm import complete, stream_chunks, strip_fences
from common.sandbox import check_html

TITLE = "Agent streams model-written HTML into a sandboxed iframe"
MODE = "open-ended"

SYSTEM = (
    "Write a single self-contained HTML fragment (inline <style>/<svg>/<script> only, no external URLs, "
    "no fetch, no storage) that visualises the Campus Cafe sales the user asks about. "
    "To request an action, call genux.action(name, params). Reply with the HTML only."
)


def scripted(prompt: str) -> str:
    return custom_html(days_from(prompt))


def run(run_input: dict):
    thread, run_id = run_input.get("threadId", "t1"), run_input.get("runId", agui.new_id("run"))
    yield agui.run_started(thread, run_id)
    html = strip_fences(complete(SYSTEM, agui.last_user_text(run_input), scripted))
    problems = check_html(html)
    if problems:  # reject before the HTML ever reaches the browser
        yield agui.run_error("generated HTML rejected: " + "; ".join(problems))
        return
    yield from agui.text_message(f"Generated a custom view ({len(html)} bytes of HTML).", stream_chunks)
    yield from agui.tool_call("render_html", {"html": html}, lambda s: stream_chunks(s, 160))
    yield agui.run_finished(thread, run_id)


ROUTES = {"run": run}


def cli():
    prompt = "draw me a custom revenue trend for 7 days"
    print(f"user: {prompt}")
    agui.print_events(run({"messages": [{"role": "user", "content": prompt}]}))
    print("\npolicy check on a malicious reply:", check_html('<script src="https://evil.example/x.js"></script><script>fetch("/steal")</script>'))


if __name__ == "__main__":
    cli()
