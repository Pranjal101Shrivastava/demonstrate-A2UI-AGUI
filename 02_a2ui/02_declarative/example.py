"""A2UI · DECLARATIVE mode, with a validation-and-correction loop.

The model writes the A2UI messages itself (JSONL, one message per line)
using only the advertised catalog. The agent validates the whole sequence;
if anything is wrong, the ERRORS ARE SENT BACK TO THE MODEL as the next
prompt, and it tries again (max 3 attempts). Only a valid sequence is
streamed to the client.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import a2ui
from common.fixtures import a2ui_dashboard, days_from
from common.llm import complete

TITLE = "Model writes A2UI messages; validation errors are fed back for self-correction"
MODE = "declarative"
MAX_ATTEMPTS = 3

SYSTEM = (
    f"You emit A2UI {a2ui.VERSION} messages as JSONL (one JSON object per line, nothing else).\n"
    f"Use surfaceId 'cafe' and catalogId '{a2ui.CAFE_CATALOG}'. Components in this catalog:\n"
    + a2ui.catalog_prompt(a2ui.CAFE_CATALOG)
    + "\nSequence: createSurface, updateComponents (flat list, root id 'root', children by id), "
    "updateDataModel (path '/'). Bind props to data with {\"path\": \"/pointer\"}."
)


def scripted(prompt: str) -> str:
    msgs = a2ui_dashboard(days_from(prompt))
    if "VALIDATION ERRORS" not in prompt:
        # First attempt: a realistic mistake. The model reaches for a PieChart (not in
        # the catalog) and references a child it never defined.
        comps = msgs[1]["updateComponents"]["components"]
        comps[7] = {"id": "chart", "component": "PieChart", "slices": {"path": "/sales/cups"}}
        comps[0]["children"].append("footer")
    return "\n".join(json.dumps(m) for m in msgs)


def generate(prompt, log=lambda *_: None):
    ask = prompt
    for attempt in range(1, MAX_ATTEMPTS + 1):
        text = complete(SYSTEM, ask, scripted)
        msgs, errs = a2ui.parse_jsonl(text)
        errs += a2ui.validate(msgs) if not errs else []
        log(f"attempt {attempt}: {len(msgs)} messages, {len(errs)} errors")
        for e in errs:
            log(f"   - {e}")
        if not errs:
            return msgs
        # Errors are a RESULT, not a crash: hand them back to the model.
        ask = f"{prompt}\n\nVALIDATION ERRORS in your previous reply:\n" + "\n".join(errs) + "\nReply with the corrected JSONL."
    raise ValueError(f"no valid UI after {MAX_ATTEMPTS} attempts")


def stream(body):
    notes = []
    msgs = generate(body.get("prompt", ""), notes.append)
    for n in notes:
        yield {"note": n}
    for m in msgs:
        yield {"a2ui": m}


ROUTES = {"stream": stream}


def cli():
    prompt = "build a stock and sales overview for 5 days"
    print(f"user: {prompt}")
    msgs = generate(prompt, lambda s: print("  " + s))
    s = a2ui.Surface()
    for m in msgs:
        s.apply(m)
    print("terminal render of the accepted surface:\n  " + "\n  ".join(s.text_render()))


if __name__ == "__main__":
    cli()
