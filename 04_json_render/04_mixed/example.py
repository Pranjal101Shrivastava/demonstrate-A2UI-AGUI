"""json-render · MIXED mode: catalog + GeneratedView + catalog-defined actions,
rendered on TWO targets (browser and terminal) from the same spec.

Actions are part of the catalog with typed params. When a button (or the
sandboxed view) fires one, the server validates the params against the
catalog, then answers with a few `replace` patches - not a new spec.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.data import sales
from common.fixtures import custom_html, dashboard_spec, days_from
from common.jsonrender import catalog_prompt, spec_to_patches, terminal_render, validate_action, validate_spec
from common.llm import complete, strip_fences
from common.sandbox import check_html

TITLE = "Catalog + GeneratedView + typed actions; one spec, two renderers"
MODE = "mixed"
SYSTEM = ("Build a Campus Cafe UI, using GeneratedView once for a custom visual. " + catalog_prompt(hybrid=True)
          + '\nReturn JSON only: {"root", "elements"}.')
STOCK = dict(sales()["stock"])


def generate(prompt):
    spec = json.loads(strip_fences(complete(SYSTEM, prompt, lambda p: json.dumps(dashboard_spec(days_from(p), hybrid=True)))))
    errs = validate_spec(spec, hybrid=True)
    errs += [e for el in spec["elements"].values() if el["type"] == "GeneratedView" for e in check_html(el["props"]["html"])]
    if errs:
        raise ValueError("; ".join(errs))
    return spec


def action_patches(action, params):
    errs = validate_action(action, params)
    if errs:
        raise ValueError("; ".join(errs))
    if action == "restock":
        STOCK[params["item"]] = STOCK.get(params["item"], 0) + params["qty"]
        return [{"op": "replace", "path": "/elements/stock/props/rows", "value": [[k, v] for k, v in STOCK.items()]}]
    s = sales(params["days"])
    return [
        {"op": "replace", "path": "/elements/title/props/text", "value": f"Campus Cafe - last {s['days']} days"},
        {"op": "replace", "path": "/elements/m_cups/props/value", "value": s["total_cups"]},
        {"op": "replace", "path": "/elements/m_rev/props/value", "value": f"${s['total_revenue']:.2f}"},
        {"op": "replace", "path": "/elements/bars/props", "value": {"labels": s["labels"], "values": s["cups"]}},
        {"op": "replace", "path": "/elements/custom/props/html", "value": custom_html(s["days"])},
    ]


def stream(body):
    for op in spec_to_patches(generate(body.get("prompt", ""))):
        yield {"patch": op}


def on_action(body):
    try:
        for op in action_patches(body.get("action"), body.get("params", {})):
            yield {"patch": op}
    except ValueError as e:
        yield {"error": str(e)}


ROUTES = {"stream": stream, "action": on_action}


def cli():
    from common.jsonpatch import apply_patch
    spec = generate("dashboard for 7 days")
    print("=== terminal target ===\n" + terminal_render(spec))
    print("\nclick [Last 3 days] -> patches:")
    ops = action_patches("set_days", {"days": 3})
    for op in ops:
        print(f"  {op['op']} {op['path']}")
    spec = apply_patch(spec, ops)
    print("\n" + terminal_render(spec).split("\n+--")[0])
    for bad in [("restock", {"item": "beans_kg", "qty": "lots"}), ("wipe_db", {})]:
        try:
            action_patches(*bad)
        except ValueError as e:
            print(f"rejected {bad[0]}{bad[1]}: {e}")


if __name__ == "__main__":
    cli()
