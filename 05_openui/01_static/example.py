"""OpenUI Lang · STATIC mode.

The catalog is three prebuilt components (PRESET_SIGNATURES). The model's
whole program is a single line like
    root = SalesCard(5, 272, "$952.00", "Sat")
It can choose the component and its values, nothing else.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.data import sales
from common.fixtures import days_from
from common.llm import complete, stream_chunks
from common.openui import PRESET_SIGNATURES, Program

TITLE = "One-line programs over a preset catalog"
MODE = "static"
SYSTEM = ("Answer with ONE OpenUI Lang line `root = <Component>(args...)` using one of:\n"
          + "\n".join(f"- {k}({', '.join(v)})" for k, v in PRESET_SIGNATURES.items()) + "\nCampus Cafe data: {data}")


def scripted(prompt):
    p, s = prompt.lower(), sales(days_from(prompt))
    if "stock" in p:
        return f"root = StockTable({json.dumps([[k, v] for k, v in s['stock'].items()])})\n"
    if "chart" in p:
        return f"root = CupsChart({json.dumps(s['labels'])}, {json.dumps(s['cups'])})\n"
    return f'root = SalesCard({s["days"]}, {s["total_cups"]}, "${s["total_revenue"]:.2f}", "{s["best_day"]}")\n'


def generate(prompt):
    text = complete(SYSTEM.replace("{data}", json.dumps(sales(days_from(prompt)))), prompt, scripted)
    prog = Program(PRESET_SIGNATURES)
    prog.feed(text)
    prog.close()
    errs = prog.validate() + ([] if list(prog.defs) == ["root"] else ["static mode allows exactly one statement"])
    if errs:
        raise ValueError("; ".join(errs))
    return text


def stream(body):
    for c in stream_chunks(generate(body.get("prompt", "")), 12):
        yield {"text": c}
    yield {"end": True}


ROUTES = {"stream": stream}


def cli():
    for prompt in ["sales card for 5 days", "chart for 7 days", "stock please"]:
        text = generate(prompt)
        p = Program(PRESET_SIGNATURES)
        p.feed(text)
        print(f"user: {prompt:<22} model: {text.strip():<70} -> {p.tree()['type']}")


if __name__ == "__main__":
    cli()
