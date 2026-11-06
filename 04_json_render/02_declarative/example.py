"""json-render · DECLARATIVE mode, streamed as JSONL patches.

The model writes the spec as one JSON Patch per line. The server parses the
model's text INCREMENTALLY (PatchStreamParser): every completed line is
validated against the catalog and forwarded at once, so the browser paints
the first elements long before the reply is complete. Invalid elements are
dropped and reported; the rest of the stream continues.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json
import time

from common.fixtures import dashboard_spec, days_from
from common.jsonrender import PatchStreamParser, catalog_prompt, spec_to_patches, validate_spec
from common.llm import complete, stream_chunks

TITLE = "Spec streamed as RFC 6902 JSONL patches, validated line by line"
MODE = "declarative"
SYSTEM = ("Build a Campus Cafe UI. " + catalog_prompt()
          + "\nOutput JSONL, one RFC 6902 patch per line: first {\"op\":\"add\",\"path\":\"/root\",\"value\":id}, "
          "then {\"op\":\"add\",\"path\":\"/elements/<id>\",\"value\":{type,props,children}} parents first. Nothing else.")


def scripted(prompt):
    spec = dashboard_spec(days_from(prompt))
    lines = [json.dumps(op) for op in spec_to_patches(spec)]
    # one realistic hallucination mid-stream: a component the catalog does not have
    lines.insert(5, json.dumps({"op": "add", "path": "/elements/gauge", "value": {"type": "Gauge", "props": {"value": 0.7}}}))
    return "\n".join(lines) + "\n"


def stream(body, chunk=40):
    text = complete(SYSTEM, body.get("prompt", ""), scripted)
    parser, t0, first = PatchStreamParser(), time.perf_counter(), None
    for piece in stream_chunks(text, chunk):          # imitate tokens arriving
        for op in parser.feed(piece):
            first = first or time.perf_counter() - t0
            yield {"patch": op}
        while parser.errors:
            yield {"note": "dropped: " + parser.errors.pop(0)}
    for op in parser.close():
        yield {"patch": op}
    yield {"note": f"final spec valid: {validate_spec(parser.spec) == []}, {len(parser.spec['elements'])} elements"}


ROUTES = {"stream": stream}


def cli():
    prompt = "dashboard for 5 days"
    print(f"user: {prompt}")
    n = 0
    for ev in stream({"prompt": prompt}):
        n += 1
        if "patch" in ev:
            v = ev["patch"]["value"]
            print(f"  [{n:02}] patch {ev['patch']['path']:<22} {v.get('type', '') if isinstance(v, dict) else v}")
        else:
            print(f"  [{n:02}] {ev['note']}")


if __name__ == "__main__":
    cli()
