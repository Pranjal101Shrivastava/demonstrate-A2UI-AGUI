"""A2UI · STATIC mode.

The STRUCTURE is a fixed, hand-written A2UI template (template.json) whose
props are bindings like {"path": "/report/cups"}. The model writes only the
DATA. The agent sends createSurface + updateComponents (always the same) and
then updateDataModel with whatever the model produced.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common import a2ui
from common.data import sales
from common.fixtures import days_from
from common.llm import complete, strip_fences

TITLE = "Fixed A2UI template; the model only fills the data model"
MODE = "static"
HERE = pathlib.Path(__file__).parent
TEMPLATE = json.loads((HERE / "template.json").read_text())
SID = "report"

SYSTEM = (
    "Fill this JSON object for the Campus Cafe report and reply with JSON only: "
    '{"headline": str, "cups": int, "revenue": str, "best": str, "labels": [str], "series": [int], "note": str}. '
    "Data: {data}"
)
REQUIRED = {"headline": str, "cups": int, "revenue": str, "best": str, "labels": list, "series": list, "note": str}


def scripted(prompt: str) -> str:
    s = sales(days_from(prompt))
    return json.dumps({
        "headline": f"{s['total_cups']} cups in {s['days']} days",
        "cups": s["total_cups"], "revenue": f"${s['total_revenue']:.2f}", "best": s["best_day"],
        "labels": s["labels"], "series": s["cups"],
        "note": f"{s['best_day']} was busiest. Beans stock: {s['stock']['beans_kg']} kg.",
    })


def check_data(d):
    return [f"{k}: expected {t.__name__}" for k, t in REQUIRED.items() if not isinstance(d.get(k), t)]


def messages_for(prompt):
    system = SYSTEM.replace("{data}", json.dumps(sales(days_from(prompt))))
    data = json.loads(strip_fences(complete(system, prompt, scripted)))
    errs = check_data(data)
    if errs:
        raise ValueError("model data rejected: " + "; ".join(errs))
    return [
        a2ui.create_surface(SID, a2ui.CAFE_CATALOG),
        a2ui.update_components(SID, TEMPLATE),          # structure: identical on every request
        a2ui.update_data(SID, "/report", data),         # data: the only thing the model decides
    ]


def stream(body):
    for m in messages_for(body.get("prompt", "")):
        yield {"a2ui": m}


ROUTES = {"stream": stream}


def cli():
    for prompt in ["daily report for 7 days", "daily report for 3 days"]:
        print(f"\nuser: {prompt}")
        msgs = messages_for(prompt)
        for m in msgs:
            k = a2ui.kind_of(m)
            print(f"  {k:<17} {json.dumps(m[k])[:120]}")
        print("  validation errors:", a2ui.validate(msgs))
        s = a2ui.Surface()
        for m in msgs:
            s.apply(m)
        print("  terminal render:\n    " + "\n    ".join(s.text_render()))


if __name__ == "__main__":
    cli()
