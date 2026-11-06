"""json-render · STATIC mode.

The catalog holds only three coarse, prebuilt components (PRESETS). The model
still answers in the json-render spec format, but its spec can contain just
one preset element with a parameter. The page owns the presets' layout; the
server sends their data on a side channel.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.data import sales
from common.fixtures import days_from
from common.jsonrender import PRESETS, catalog_prompt, spec_to_patches
from common.llm import complete, strip_fences

TITLE = "A preset-only catalog: the model picks one prebuilt component"
MODE = "static"
SYSTEM = ("Pick ONE component for the request. " + catalog_prompt(presets=True)
          + '\nReturn a json-render spec, JSON only: {"root": "main", "elements": {"main": {"type", "props"}}}')


def scripted(prompt):
    p = prompt.lower()
    t = "StockTable" if "stock" in p else "DailyCupsChart" if "chart" in p else "SalesSummaryCard"
    props = {} if t == "StockTable" else {"days": days_from(p)}
    return json.dumps({"root": "main", "elements": {"main": {"type": t, "props": props}}})


def generate(prompt):
    spec = json.loads(strip_fences(complete(SYSTEM, prompt, scripted)))
    els = spec.get("elements", {})
    if len(els) != 1 or next(iter(els.values()))["type"] not in PRESETS:
        raise ValueError(f"static mode accepts exactly one preset element, got {[e['type'] for e in els.values()]}")
    return spec


def stream(body):
    spec = generate(body.get("prompt", ""))
    yield {"data": sales(spec["elements"]["main"]["props"].get("days", 7))}
    for op in spec_to_patches(spec):
        yield {"patch": op}


ROUTES = {"stream": stream}


def cli():
    for prompt in ["sales summary for 5 days", "chart of cups for 7 days", "show stock"]:
        spec = generate(prompt)
        print(f"user: {prompt:<28} -> spec {json.dumps(spec)}")
    print("\nrejected (model tried to compose a layout):")
    try:
        bad = {"root": "a", "elements": {"a": {"type": "Stack", "props": {}, "children": ["b"]}, "b": {"type": "Text", "props": {"text": "hi"}}}}
        globals()["scripted"] = lambda p: json.dumps(bad)
        generate("anything")
    except ValueError as e:
        print("  ", e)


if __name__ == "__main__":
    cli()
