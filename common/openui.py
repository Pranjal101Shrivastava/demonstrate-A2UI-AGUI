"""OpenUI Lang (modeled on thesys OpenUI's `openui-lang`): a compact, line-oriented
UI language. A program is a list of assignments; `root` is the entry point and
identifiers may be used BEFORE they are defined (forward references), which
lets a model write the outline first and fill in details while streaming:

    root = Stack([title, kpis], "column")
    title = Text("Campus Cafe", "h1")
    kpis = Stack([Metric("Cups", 365), Metric("Revenue", "$1277.50")], "row")

Arguments are POSITIONAL; the catalog maps positions to prop names. Strings use
JSON escaping, so arbitrary HTML can travel inside HtmlArtifact("...").
Mirrored in the browser by common/web/openui.js.
"""
import json
import re

# component -> positional parameter names (the catalog). Last ones may be omitted.
SIGNATURES = {
    "Stack": ["children", "direction"],
    "Card": ["title", "children"],
    "Text": ["text", "variant"],
    "Metric": ["label", "value"],
    "Table": ["columns", "rows"],
    "BarChart": ["labels", "values", "title"],
    "Button": ["label", "action", "params"],
}
HTML_SIGNATURES = {"HtmlArtifact": ["html", "height"]}
PRESET_SIGNATURES = {"SalesCard": ["days", "cups", "revenue", "best"], "CupsChart": ["labels", "values"], "StockTable": ["rows"]}

TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?)|(?P<id>[A-Za-z_]\w*)|(?P<p>[()\[\]{},=:]))')


def tokenize(src):
    pos, out = 0, []
    while pos < len(src):
        if src[pos:].strip() == "":
            break
        m = TOKEN.match(src, pos)
        if not m:
            raise SyntaxError(f"unexpected character {src[pos]!r} at {pos}")
        pos = m.end()
        kind = m.lastgroup
        val = m.group(kind)
        out.append((kind, json.loads(val) if kind == "str" else float(val) if kind == "num" and "." in val else int(val) if kind == "num" else val))
    return out


class Ref(str):
    """An identifier used as a value: resolved later (forward references)."""


def parse_statement(src):
    toks, i = tokenize(src), 0

    def peek():
        return toks[i] if i < len(toks) else (None, None)

    def take(expect=None):
        nonlocal i
        t = peek()
        if expect and t[1] != expect:
            raise SyntaxError(f"expected {expect!r}, got {t[1]!r}")
        i += 1
        return t

    def expr():
        kind, val = take()
        if kind in ("str", "num"):
            return val
        if kind == "id":
            if val in ("true", "false", "null"):
                return {"true": True, "false": False, "null": None}[val]
            if peek()[1] == "(":
                take("(")
                args = []
                while peek()[1] != ")":
                    args.append(expr())
                    if peek()[1] == ",":
                        take(",")
                take(")")
                return {"$call": val, "args": args}
            return Ref(val)
        if val == "[":
            items = []
            while peek()[1] != "]":
                items.append(expr())
                if peek()[1] == ",":
                    take(",")
            take("]")
            return items
        if val == "{":
            obj = {}
            while peek()[1] != "}":
                k = take()[1]
                take(":")
                obj[k] = expr()
                if peek()[1] == ",":
                    take(",")
            take("}")
            return obj
        raise SyntaxError(f"unexpected token {val!r}")

    kind, name = take()
    if kind != "id":
        raise SyntaxError("statement must start with an identifier")
    take("=")
    value = expr()
    if i != len(toks):
        raise SyntaxError(f"trailing tokens after {name}")
    return name, value


def split_statements(text):
    """Split at newlines that are outside strings and brackets. Returns (complete, rest)."""
    out, depth, in_str, esc, start = [], 0, False, False, 0
    for j, ch in enumerate(text):
        if in_str:
            esc = (ch == "\\") and not esc
            if ch == '"' and not esc:
                in_str = False
            continue
        if ch == '"':
            in_str, esc = True, False
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "\n" and depth == 0:
            if text[start:j].strip():
                out.append(text[start:j])
            start = j + 1
    return out, text[start:]


class Program:
    """Holds parsed statements; can be fed text incrementally (streaming)."""

    def __init__(self, signatures=None):
        self.sigs = signatures or SIGNATURES
        self.defs, self.buf, self.errors = {}, "", []

    def feed(self, chunk):
        self.buf += chunk
        stmts, self.buf = split_statements(self.buf)
        return [self._add(s) for s in stmts]

    def close(self):
        rest, self.buf = self.buf, ""
        return [self._add(rest)] if rest.strip() else []

    def _add(self, src):
        if src.strip().startswith(("```", "#", "//")):
            return None
        try:
            name, value = parse_statement(src)
        except SyntaxError as e:
            self.errors.append(f"{src.strip()[:40]!r}: {e}")
            return None
        self.defs[name] = value
        return name

    def tree(self, name="root", seen=()):
        """Resolve root into a nested node {type, props, children}; undefined refs -> None (pending)."""
        if name not in self.defs or name in seen:
            return None
        return self._resolve(self.defs[name], seen + (name,))

    def _resolve(self, v, seen):
        if isinstance(v, Ref):
            return self.tree(v, seen)
        if isinstance(v, list):
            return [self._resolve(x, seen) for x in v]
        if isinstance(v, dict) and "$call" in v:
            t = v["$call"]
            if t not in self.sigs:
                self.errors.append(f"unknown component {t!r}")
                return {"type": t, "props": {}, "children": []}
            props = {p: self._resolve(a, seen) for p, a in zip(self.sigs[t], v["args"])}
            kids = props.pop("children", []) or []
            return {"type": t, "props": props, "children": kids}
        return v

    def validate(self):
        errs = list(self.errors)
        if "root" not in self.defs:
            errs.append("no `root = ...` statement")

        def walk(v):
            if isinstance(v, Ref) and v not in self.defs:
                errs.append(f"undefined reference {v!r}")
            elif isinstance(v, list):
                [walk(x) for x in v]
            elif isinstance(v, dict) and "$call" in v:
                if v["$call"] not in self.sigs:
                    errs.append(f"unknown component {v['$call']!r}; allowed: {', '.join(self.sigs)}")
                elif len(v["args"]) > len(self.sigs[v["$call"]]):
                    errs.append(f"{v['$call']}: too many arguments")
                [walk(a) for a in v["args"]]
        for val in self.defs.values():
            walk(val)
        return errs


def _lit(v):
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ", ".join(_lit(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_lit(x)}" for k, x in v.items()) + "}"
    return "null"


def from_spec(spec):
    """Write a flat element map as an OpenUI Lang program (used for scripted replies + benchmarks)."""
    sigs = dict(SIGNATURES, **HTML_SIGNATURES)
    lines = []
    for eid, el in spec["elements"].items():
        t = el["type"] if el["type"] != "GeneratedView" else "HtmlArtifact"
        props = dict(el.get("props", {}))
        if el.get("children"):
            props["children"] = el["children"]
        args = []
        for p in sigs[t]:
            if p == "children" and p in props:
                args.append("[" + ", ".join(props[p]) + "]")
            elif p in props:
                args.append(_lit(props[p]))
            else:
                args.append("null")
        while args and args[-1] == "null":
            args.pop()
        lines.append(f"{eid} = {t}({', '.join(args)})")
    return "\n".join(lines) + "\n"
