"""json-render · OPEN-ENDED mode, and why it hurts portability.

The catalog shrinks to one free-form element, GeneratedView {html}. The model
writes the HTML; the spec wraps it. The browser renders it in a sandbox, but
the TERMINAL renderer (another json-render target) cannot execute HTML at
all: open-ended output only works where a sandboxed web view exists.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.fixtures import custom_html, days_from
from common.jsonrender import spec_to_patches, terminal_render, validate_spec
from common.llm import complete, strip_fences
from common.sandbox import check_html

TITLE = "One free-form GeneratedView element; the terminal target cannot render it"
MODE = "open-ended"
SYSTEM = ("Write one self-contained HTML fragment (inline only; no URLs, fetch or storage) for the Campus Cafe "
          "request. Use genux.action(name, params) for buttons. HTML only.")


def generate(prompt):
    html = strip_fences(complete(SYSTEM, prompt, lambda p: custom_html(days_from(p))))
    problems = check_html(html)
    if problems:
        raise ValueError("; ".join(problems))
    spec = {"root": "view", "elements": {"view": {"type": "GeneratedView", "props": {"html": html, "height": 240}}}}
    assert validate_spec(spec, hybrid=True) == []
    return spec


def stream(body):
    for op in spec_to_patches(generate(body.get("prompt", ""))):
        yield {"patch": op}


ROUTES = {"stream": stream}


def cli():
    spec = generate("custom revenue trend for 7 days")
    print("spec:", json.dumps(spec)[:160], "...")
    print("\nterminal renderer output:\n" + terminal_render(spec))


if __name__ == "__main__":
    cli()
