"""A2UI · OPEN-ENDED mode.

A2UI deliberately carries data, not code. To allow open-ended output the
CLIENT must opt in by advertising a catalog that contains an escape-hatch
component, here `HtmlFrame` in catalog urn:genux:catalog:campus-cafe-html:v1.
The model writes free-form HTML into the data model; the client renders
HtmlFrame only inside a sandboxed iframe. A client that advertises the plain
catalog would reject the same messages (see cli()).
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import a2ui
from common.fixtures import custom_html, days_from
from common.llm import complete, strip_fences
from common.sandbox import check_html

TITLE = "Open-ended HTML through an opt-in HtmlFrame catalog component"
MODE = "open-ended"
SID = "custom"

SYSTEM = (
    "Write one self-contained HTML fragment (inline style/svg/script only; no URLs, no fetch, no storage) "
    "that visualises the Campus Cafe sales requested. Use genux.action(name, params) for buttons. Reply with HTML only."
)


def scripted(prompt):
    return custom_html(days_from(prompt))


def messages_for(prompt, catalog=a2ui.CAFE_HTML_CATALOG):
    html = strip_fences(complete(SYSTEM, prompt, scripted))
    problems = check_html(html)
    if problems:
        raise ValueError("generated HTML rejected: " + "; ".join(problems))
    return [
        a2ui.create_surface(SID, catalog),
        a2ui.update_components(SID, [
            {"id": "root", "component": "Card", "title": "Generated view", "child": "frame"},
            {"id": "frame", "component": "HtmlFrame", "height": 240, "html": {"path": "/html"}},
        ]),
        a2ui.update_data(SID, "/html", html),
    ]


def stream(body):
    for m in messages_for(body.get("prompt", "")):
        yield {"a2ui": m}


ROUTES = {"stream": stream}


def cli():
    prompt = "a custom revenue visual for 7 days"
    msgs = messages_for(prompt)
    print(f"user: {prompt}")
    for m in msgs:
        k = a2ui.kind_of(m)
        print(f"  {k:<17} {json.dumps(m[k])[:130]}")
    print("validation with the HTML catalog :", a2ui.validate(msgs))
    plain = messages_for(prompt, catalog=a2ui.CAFE_CATALOG)
    print("validation with the plain catalog:", a2ui.validate(plain))


if __name__ == "__main__":
    cli()
