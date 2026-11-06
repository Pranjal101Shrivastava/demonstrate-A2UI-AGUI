"""OpenUI Lang · OPEN-ENDED mode: HtmlArtifact("...").

The program is a single HtmlArtifact whose string argument is model-written
HTML (JSON-escaped, so quotes and newlines survive). The browser parses it and
renders GeneratedView -> sandboxed iframe. Note the cost: the escaped HTML is
far larger than the declarative program for a similar visual.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.fixtures import custom_html, days_from
from common.llm import complete, stream_chunks, strip_fences
from common.openui import HTML_SIGNATURES, Program
from common.sandbox import check_html

TITLE = "A single HtmlArtifact carrying model-written HTML"
MODE = "open-ended"
SYSTEM = ('Reply with exactly one line: root = HtmlArtifact("<html fragment as a JSON string>", 240). The HTML must be '
          "self-contained (inline only, no URLs/fetch/storage) and may call genux.action(name, params).")


def scripted(prompt):
    return f"root = HtmlArtifact({json.dumps(custom_html(days_from(prompt)))}, 240)\n"


def generate(prompt):
    text = strip_fences(complete(SYSTEM, prompt, scripted)) + "\n"
    prog = Program(HTML_SIGNATURES)
    prog.feed(text)
    prog.close()
    errs = prog.validate()
    t = prog.tree()
    errs += check_html(t["props"]["html"]) if t else ["no root"]
    if errs:
        raise ValueError("; ".join(errs))
    return text


def stream(body):
    for c in stream_chunks(generate(body.get("prompt", "")), 120):
        yield {"text": c}
    yield {"end": True}


ROUTES = {"stream": stream}


def cli():
    text = generate("custom revenue trend for 7 days")
    print("program:", text[:150], "...")
    print(f"size: {len(text)} chars (the whole 14-element declarative dashboard in 02_declarative is 721 chars)")
    print("malicious HtmlArtifact ->", check_html('<img src=x onerror="fetch(\'//evil\')">'))


if __name__ == "__main__":
    cli()
