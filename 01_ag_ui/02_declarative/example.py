"""AG-UI · DECLARATIVE mode.

The model composes a layout from the shared CATALOG (common/catalog.py) as a
flat element map. The agent publishes it as SHARED STATE: one STATE_SNAPSHOT,
then one STATE_DELTA (RFC 6902 JSON Patch) per element, so the page renders
progressively. Every element is validated before it is sent.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import agui
from common.catalog import catalog_prompt, validate_element, validate_flat
from common.fixtures import dashboard_spec, days_from
from common.llm import complete, stream_chunks, strip_fences

TITLE = "Agent streams a catalog layout as shared state (STATE_SNAPSHOT + STATE_DELTA)"
MODE = "declarative"

SYSTEM = (
    "Build a dashboard for the Campus Cafe from ONLY these components:\n" + catalog_prompt()
    + '\nReturn JSON only: {"root": "<id>", "elements": {"<id>": {"type", "props", "children": [ids]}}}.'
    " List parents before children."
)


def scripted(prompt: str) -> str:
    return json.dumps(dashboard_spec(days_from(prompt)))


def run(run_input: dict):
    thread, run_id = run_input.get("threadId", "t1"), run_input.get("runId", agui.new_id("run"))
    yield agui.run_started(thread, run_id)
    spec = json.loads(strip_fences(complete(SYSTEM, agui.last_user_text(run_input), scripted)))
    errors = validate_flat(spec)
    if errors:
        yield agui.run_error("invalid UI spec: " + "; ".join(errors[:5]))
        return
    yield from agui.text_message("Building your dashboard…", stream_chunks)
    # 1) snapshot: an empty surface that names the root
    yield agui.state_snapshot({"ui": {"root": spec["root"], "elements": {}}})
    # 2) deltas: one JSON Patch per element -> progressive rendering
    for eid, el in spec["elements"].items():
        assert not validate_element(el)
        yield agui.state_delta([{"op": "add", "path": f"/ui/elements/{eid}", "value": el}])
    yield agui.run_finished(thread, run_id)


ROUTES = {"run": run}


def cli():
    from common.jsonpatch import apply_patch
    prompt = "build me a dashboard for the last 5 days"
    print(f"user: {prompt}")
    events = list(run({"messages": [{"role": "user", "content": prompt}]}))
    agui.print_events(events)
    state = {}
    for e in events:
        if e["type"] == "STATE_SNAPSHOT":
            state = e["snapshot"]
        elif e["type"] == "STATE_DELTA":
            state = apply_patch(state, e["delta"])
    print(f"\nfinal client state: {len(state['ui']['elements'])} elements, validation errors: {validate_flat(state['ui'])}")


if __name__ == "__main__":
    cli()
