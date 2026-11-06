"""json-render style specs (modeled on vercel-labs/json-render).

Ideas we reproduce:
  * ONE catalog = prompt + validator + renderer registry (components AND actions).
  * The spec is a FLAT element map: {"root": id, "elements": {id: {type, props, children}}}
  * Models stream the spec as JSONL RFC 6902 patches:
        {"op":"add","path":"/root","value":"main"}
        {"op":"add","path":"/elements/main","value":{...}}
    so each finished line can be rendered immediately.
  * The same spec can drive more than one renderer (browser and terminal here).
"""
import json

from common.catalog import CATALOG, HYBRID_EXTRA, validate_element, validate_flat
from common.jsonpatch import apply_patch

# Actions are part of the catalog too: name -> param types. Buttons may only use these.
ACTIONS = {
    "set_days": {"days": int},
    "restock": {"item": str, "qty": int},
}

# STATIC mode catalog: coarse, prebuilt components the model can only pick and parameterise.
PRESETS = {
    "SalesSummaryCard": {"props": {"days": "integer 1-7"}},
    "DailyCupsChart": {"props": {"days": "integer 1-7"}},
    "StockTable": {"props": {}},
}


def catalog_prompt(hybrid=False, presets=False):
    if presets:
        comps = "\n".join(f"- {k}({', '.join(f'{p}: {t}' for p, t in v['props'].items())})" for k, v in PRESETS.items())
    else:
        cat = dict(CATALOG, **(HYBRID_EXTRA if hybrid else {}))
        comps = "\n".join(f"- {k}({', '.join(v['props'])}){' [children]' if v['children'] else ''}" for k, v in cat.items())
    acts = "\n".join(f"- {k}({', '.join(f'{p}: {t.__name__}' for p, t in v.items())})" for k, v in ACTIONS.items())
    return f"COMPONENTS:\n{comps}\nACTIONS (Button.action / Button.params):\n{acts}"


def validate_action(name, params):
    if name not in ACTIONS:
        return [f"unknown action {name!r}"]
    errs = []
    for p, t in ACTIONS[name].items():
        if not isinstance(params.get(p), t):
            errs.append(f"action {name}: param {p!r} must be {t.__name__}")
    return errs


def validate_spec(spec, hybrid=False):
    errs = validate_flat(spec, extra=hybrid)
    for eid, el in spec.get("elements", {}).items():
        if el.get("type") == "Button":
            errs += [f"{eid}: {e}" for e in validate_action(el["props"].get("action"), el["props"].get("params", {}))]
    return errs


def spec_to_patches(spec):
    """Serialize a spec as the JSONL patch stream a model would emit (parents first)."""
    yield {"op": "add", "path": "/root", "value": spec["root"]}
    for eid, el in spec["elements"].items():
        yield {"op": "add", "path": f"/elements/{eid}", "value": el}


class PatchStreamParser:
    """Feed raw model text chunk by chunk; complete lines become validated patches."""

    def __init__(self, hybrid=False):
        self.buf, self.spec, self.hybrid, self.errors = "", {"root": None, "elements": {}}, hybrid, []

    def feed(self, chunk):
        self.buf += chunk
        out = []
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            out += self._line(line)
        return out

    def close(self):
        out = self._line(self.buf)
        self.buf = ""
        return out

    def _line(self, line):
        line = line.strip()
        if not line or line.startswith("```"):
            return []
        try:
            op = json.loads(line)
        except json.JSONDecodeError as e:
            self.errors.append(f"bad JSON line: {e.msg}")
            return []
        if op.get("path", "").startswith("/elements/") and op.get("op") == "add":
            errs = validate_element(op["value"], self.hybrid)
            if errs:  # drop the bad element, keep streaming the rest
                self.errors += [f"{op['path']}: {e}" for e in errs]
                return []
        self.spec = apply_patch(self.spec, [op])
        return [op]


def terminal_render(spec, width=60):
    """Second renderer: the same spec as plain text (e.g. for a CLI or a coding-agent harness)."""
    els = spec["elements"]
    lines = []

    def walk(eid, depth):
        el = els.get(eid)
        if not el:
            return
        p, pad = el.get("props", {}), "  " * depth
        t = el["type"]
        if t == "Text":
            lines.append(pad + (p["text"].upper() if p.get("variant") == "h1" else p["text"]))
        elif t == "Metric":
            lines.append(f"{pad}{p['label']}: {p['value']}")
        elif t == "BarChart":
            mx = max(p["values"]) or 1
            for lab, v in zip(p["labels"], p["values"]):
                lines.append(f"{pad}{lab:>4} {'#' * round(v / mx * 30)} {v}")
        elif t == "Table":
            lines.append(pad + " | ".join(p["columns"]))
            lines.extend(pad + " | ".join(str(c) for c in r) for r in p["rows"])
        elif t == "Button":
            lines.append(f"{pad}[ {p['label']} ] -> {p['action']}({json.dumps(p.get('params', {}))})")
        elif t == "GeneratedView":
            lines.append(f"{pad}[custom HTML view, {len(p['html'])} bytes - a terminal cannot run it; open the web surface]")
        elif t == "Card":
            lines.append(f"{pad}+-- {p.get('title', '')} " + "-" * max(0, width - len(p.get('title', '')) - 5 - len(pad)))
        for c in el.get("children", []) or []:
            walk(c, depth + (1 if t in ("Card", "Stack") and depth < 6 else 0))

    walk(spec["root"], 0)
    return "\n".join(lines)
