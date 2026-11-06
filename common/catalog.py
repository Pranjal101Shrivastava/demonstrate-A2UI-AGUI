"""The shared component CATALOG used by the declarative examples.

A catalog is the contract between model and application: which component
types exist, which props each accepts, and which props are required.
It is used three ways: (1) rendered into the system prompt, (2) used to
validate model output, (3) mirrored by the browser renderer (common/web/catalog.js).
"""

CATALOG = {
    "Stack":   {"props": {"direction": "row|column", "gap": "number"}, "required": [], "children": True},
    "Card":    {"props": {"title": "string"}, "required": [], "children": True},
    "Text":    {"props": {"text": "string", "variant": "h1|h2|body|muted"}, "required": ["text"], "children": False},
    "Metric":  {"props": {"label": "string", "value": "string|number"}, "required": ["label", "value"], "children": False},
    "Table":   {"props": {"columns": "string[]", "rows": "any[][]"}, "required": ["columns", "rows"], "children": False},
    "BarChart": {"props": {"labels": "string[]", "values": "number[]", "title": "string"}, "required": ["labels", "values"], "children": False},
    "Button":  {"props": {"label": "string", "action": "string", "params": "object"}, "required": ["label", "action"], "children": False},
}

# The hybrid ("mixed") examples add exactly one escape-hatch component.
HYBRID_EXTRA = {
    "GeneratedView": {"props": {"html": "string", "height": "number"}, "required": ["html"], "children": False},
}


def catalog_prompt(extra: bool = False) -> str:
    cat = dict(CATALOG, **(HYBRID_EXTRA if extra else {}))
    lines = []
    for name, spec in cat.items():
        props = ", ".join(f"{k}: {v}" + (" (required)" if k in spec["required"] else "") for k, v in spec["props"].items())
        lines.append(f"- {name}({props})" + (" [has children]" if spec["children"] else ""))
    return "\n".join(lines)


def validate_element(el: dict, extra: bool = False) -> list:
    """Validate one element {type, props, children}. Returns a list of error strings."""
    cat = dict(CATALOG, **(HYBRID_EXTRA if extra else {}))
    errs = []
    t = el.get("type")
    if t not in cat:
        return [f"unknown component type {t!r}; allowed: {', '.join(cat)}"]
    props = el.get("props", {}) or {}
    for r in cat[t]["required"]:
        if r not in props:
            errs.append(f"{t}: missing required prop {r!r}")
    for k in props:
        if k not in cat[t]["props"]:
            errs.append(f"{t}: unknown prop {k!r}")
    if el.get("children") and not cat[t]["children"]:
        errs.append(f"{t}: does not accept children")
    return errs


def validate_flat(spec: dict, extra: bool = False) -> list:
    """Validate a flat element map {root, elements:{id: element}} (json-render / AG-UI state style)."""
    errs = []
    elements = spec.get("elements", {})
    if spec.get("root") not in elements:
        errs.append(f"root {spec.get('root')!r} is not an element id")
    for eid, el in elements.items():
        errs += [f"{eid}: {e}" for e in validate_element(el, extra)]
        for c in el.get("children", []) or []:
            if c not in elements:
                errs.append(f"{eid}: child {c!r} does not exist")
    return errs
