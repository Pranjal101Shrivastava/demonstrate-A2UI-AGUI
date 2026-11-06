"""OpenUI Lang · DECLARATIVE mode + a format benchmark.

The model composes primitives. The program streams to the browser as raw
text and the browser's own parser (common/web/openui.js) renders each
statement as soon as it is complete. Because `root` comes first and refers to
ids defined later, the page shows the layout skeleton immediately and fills
it in. cli() also compares the size of the same dashboard in four formats.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json
import re

from common.fixtures import a2ui_dashboard, custom_html, dashboard_spec, days_from
from common.jsonrender import spec_to_patches
from common.llm import complete, stream_chunks
from common.openui import SIGNATURES, Program, from_spec

TITLE = "Streaming OpenUI Lang with forward references, plus a format size benchmark"
MODE = "declarative"
SYSTEM = ("Write an OpenUI Lang program (one `id = Component(args)` per line, `root` first; ids may be used before "
          "they are defined). Components (positional args):\n" + "\n".join(f"- {k}({', '.join(v)})" for k, v in SIGNATURES.items()))


def scripted(prompt):
    return from_spec(dashboard_spec(days_from(prompt)))


def generate(prompt):
    text = complete(SYSTEM, prompt, scripted)
    prog = Program()
    prog.feed(text)
    prog.close()
    errs = prog.validate()
    if errs:
        raise ValueError("; ".join(errs))
    return text


def stream(body):
    for c in stream_chunks(generate(body.get("prompt", "")), 18):
        yield {"text": c}
    yield {"end": True}


ROUTES = {"stream": stream}


def approx_tokens(s):
    """Crude, stated heuristic (no tokenizer download): words, numbers and each punctuation mark = 1 token."""
    return len(re.findall(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]", s))


def benchmark(days=7):
    spec = dashboard_spec(days)
    formats = {
        "OpenUI Lang": from_spec(spec),
        "json-render JSONL patches": "\n".join(json.dumps(op) for op in spec_to_patches(spec)),
        "json-render spec (JSON)": json.dumps(spec),
        "A2UI v0.9 JSONL": "\n".join(json.dumps(m) for m in a2ui_dashboard(days, actions=True)),
    }
    return {k: (len(v), approx_tokens(v)) for k, v in formats.items()}


def cli():
    prompt = "dashboard for 5 days"
    text = generate(prompt)
    print(f"user: {prompt}\nmodel program:\n" + "\n".join("  " + l for l in text.splitlines()))
    prog, order = Program(), []
    for c in stream_chunks(text, 18):
        for name in prog.feed(c):
            t = prog.tree()
            pending = json.dumps(t).count("null") if t else "-"
            order.append(f"{name}(unresolved refs: {pending})")
    print("\nstreaming: statements completed in order ->\n  " + "\n  ".join(order[:6]) + "\n  ...")
    print("\nFormat benchmark (same 14-element dashboard; tokens = stated heuristic, not a model tokenizer):")
    for k, (chars, toks) in benchmark().items():
        print(f"  {k:<28} {chars:>5} chars  ~{toks:>4} tokens")


if __name__ == "__main__":
    cli()
