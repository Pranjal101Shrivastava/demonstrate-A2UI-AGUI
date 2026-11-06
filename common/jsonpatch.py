"""Minimal RFC 6902 JSON Patch (add / replace / remove) - enough for AG-UI STATE_DELTA
and json-render streaming. Mirrors common/web/jsonpatch.js."""
import copy


def _parts(path):
    if path == "":
        return []
    return [p.replace("~1", "/").replace("~0", "~") for p in path.lstrip("/").split("/")]


def apply_patch(doc, ops):
    doc = copy.deepcopy(doc)
    for op in ops:
        parts = _parts(op["path"])
        if not parts:
            doc = copy.deepcopy(op.get("value"))
            continue
        parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent.setdefault(p, {})
        key = parts[-1]
        kind = op["op"]
        if isinstance(parent, list):
            idx = len(parent) if key == "-" else int(key)
            if kind == "add":
                parent.insert(idx, op["value"])
            elif kind == "replace":
                parent[idx] = op["value"]
            elif kind == "remove":
                parent.pop(idx)
        else:
            if kind in ("add", "replace"):
                parent[key] = op["value"]
            elif kind == "remove":
                parent.pop(key, None)
        if kind not in ("add", "replace", "remove"):
            raise ValueError(f"unsupported op {kind}")
    return doc
