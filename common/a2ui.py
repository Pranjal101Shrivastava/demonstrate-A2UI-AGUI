"""A2UI (Agent-to-UI) message helpers, following the v0.9 message shapes.

A2UI is a FORMAT that separates STRUCTURE from DATA:
  createSurface     {surfaceId, catalogId}          open a surface, name its catalog
  updateComponents  {surfaceId, components:[...]}   flat list; each {id, component, ...props}
                                                   children by id: "child": id / "children": [ids]
  updateDataModel   {surfaceId, path, value}        JSON data the components bind to
  deleteSurface     {surfaceId}
A prop may be a literal or a binding {"path": "/json/pointer"} into the data model.
User interaction goes back as {"action": {name, surfaceId, sourceComponentId, context}}.

The client only renders component types from the catalog it advertised, so
the model can describe UI but cannot ship code. See https://a2ui.org/.
"""
import json

VERSION = "v0.9"
BASIC_CATALOG = "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json"
CAFE_CATALOG = "urn:genux:catalog:campus-cafe:v1"      # basic + Metric/BarChart/Table
CAFE_HTML_CATALOG = "urn:genux:catalog:campus-cafe-html:v1"  # ...plus the HtmlFrame escape hatch

# component -> (allowed props, required props)
COMPONENTS = {
    "Column": ({"children", "gap"}, set()),
    "Row": ({"children", "gap"}, set()),
    "Card": ({"child", "children", "title"}, set()),
    "Text": ({"text", "variant"}, {"text"}),
    "Divider": (set(), set()),
    "Button": ({"label", "action"}, {"label", "action"}),
    "Metric": ({"label", "value"}, {"label", "value"}),
    "BarChart": ({"labels", "values", "title"}, {"labels", "values"}),
    "Table": ({"columns", "rows"}, {"columns", "rows"}),
}
HTML_COMPONENTS = {"HtmlFrame": ({"html", "height"}, {"html"})}


def catalog_for(catalog_id):
    return dict(COMPONENTS, **HTML_COMPONENTS) if catalog_id == CAFE_HTML_CATALOG else dict(COMPONENTS)


def catalog_prompt(catalog_id):
    out = []
    for name, (allowed, req) in catalog_for(catalog_id).items():
        out.append(f"- {name}: props {sorted(allowed) or '-'}; required {sorted(req) or '-'}")
    return "\n".join(out)


def msg(kind, **body):
    return {"version": VERSION, kind: body}


def create_surface(sid, catalog_id):
    return msg("createSurface", surfaceId=sid, catalogId=catalog_id)


def update_components(sid, components):
    return msg("updateComponents", surfaceId=sid, components=components)


def update_data(sid, path, value):
    return msg("updateDataModel", surfaceId=sid, path=path, value=value)


def delete_surface(sid):
    return msg("deleteSurface", surfaceId=sid)


def kind_of(m):
    return next(k for k in ("createSurface", "updateComponents", "updateDataModel", "deleteSurface", "action") if k in m)


def validate(messages):
    """Validate a whole message sequence. Returns a list of human-readable errors
    (written for the MODEL to read and fix, see 02_a2ui/02_declarative)."""
    errs, catalogs, comps = [], {}, {}
    for i, m in enumerate(messages):
        if not isinstance(m, dict) or m.get("version") != VERSION:
            errs.append(f"message {i}: must be an object with version {VERSION!r}")
            continue
        try:
            k = kind_of(m)
        except StopIteration:
            errs.append(f"message {i}: unknown message type, keys={list(m)}")
            continue
        body = m[k]
        sid = body.get("surfaceId")
        if k == "createSurface":
            catalogs[sid] = body.get("catalogId")
            comps[sid] = {}
            continue
        if sid not in catalogs:
            errs.append(f"message {i}: surface {sid!r} used before createSurface")
            continue
        if k == "updateComponents":
            cat = catalog_for(catalogs[sid])
            for c in body.get("components", []):
                cid, ctype = c.get("id"), c.get("component")
                if ctype not in cat:
                    errs.append(f"component {cid!r}: type {ctype!r} is not in catalog {catalogs[sid]} (allowed: {', '.join(cat)})")
                    continue
                allowed, req = cat[ctype]
                for r in req - set(c):
                    errs.append(f"component {cid!r} ({ctype}): missing required prop {r!r}")
                for p in set(c) - allowed - {"id", "component"}:
                    errs.append(f"component {cid!r} ({ctype}): unknown prop {p!r}")
                comps[sid][cid] = c
        if k == "updateDataModel" and not str(body.get("path", "")).startswith("/"):
            errs.append(f"message {i}: updateDataModel.path must be a JSON pointer starting with '/'")
    for sid, cs in comps.items():
        if cs and "root" not in cs:
            errs.append(f"surface {sid!r}: no component with id 'root'")
        for cid, c in cs.items():
            for ref in ([c["child"]] if "child" in c else []) + list(c.get("children", [])):
                if ref not in cs:
                    errs.append(f"component {cid!r}: child {ref!r} does not exist")
    return errs


def parse_jsonl(text):
    """Models emit one JSON message per line. Returns (messages, errors)."""
    out, errs = [], []
    for n, line in enumerate(text.strip().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            errs.append(f"line {n}: invalid JSON ({e.msg})")
    return out, errs


class Surface:
    """Server-side mirror of a client surface: used by tests and the terminal renderer."""

    def __init__(self):
        self.catalog, self.components, self.data = None, {}, {}

    def apply(self, m):
        k = kind_of(m)
        b = m[k]
        if k == "createSurface":
            self.catalog = b["catalogId"]
        elif k == "updateComponents":
            for c in b["components"]:
                self.components[c["id"]] = c
        elif k == "updateDataModel":
            self._set(b["path"], b["value"])
        elif k == "deleteSurface":
            self.components, self.data = {}, {}
        return self

    def _set(self, path, value):
        parts = [p for p in path.split("/") if p]
        if not parts:
            self.data = value
            return
        cur = self.data
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = value

    def get(self, path):
        cur = self.data
        for p in [p for p in path.split("/") if p]:
            cur = cur[int(p)] if isinstance(cur, list) else cur.get(p) if isinstance(cur, dict) else None
        return cur

    def resolve(self, v):
        return self.get(v["path"]) if isinstance(v, dict) and set(v) == {"path"} else v

    def text_render(self, cid="root", depth=0):
        """A tiny terminal renderer: proves the same messages can target a non-browser client."""
        c = self.components.get(cid)
        if not c:
            return []
        props = {k: self.resolve(v) for k, v in c.items() if k not in ("id", "component", "child", "children", "action")}
        line = "  " * depth + f"{c['component']}" + (f" {json.dumps(props)[:100]}" if props else "")
        kids = ([c["child"]] if "child" in c else []) + list(c.get("children", []))
        return [line] + [l for k in kids for l in self.text_render(k, depth + 1)]
