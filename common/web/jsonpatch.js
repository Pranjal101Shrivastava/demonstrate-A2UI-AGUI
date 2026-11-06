// Minimal RFC 6902 JSON Patch (add / replace / remove). Mirrors common/jsonpatch.py.
const parts = (p) => p === "" ? [] : p.replace(/^\//, "").split("/").map(s => s.replace(/~1/g, "/").replace(/~0/g, "~"));
export function applyPatch(doc, ops) {
  doc = structuredClone(doc);
  for (const op of ops) {
    const ps = parts(op.path);
    if (!ps.length) { doc = structuredClone(op.value); continue; }
    let parent = doc;
    for (const p of ps.slice(0, -1)) parent = Array.isArray(parent) ? parent[+p] : (parent[p] ??= {});
    const key = ps[ps.length - 1];
    if (Array.isArray(parent)) {
      const i = key === "-" ? parent.length : +key;
      if (op.op === "add") parent.splice(i, 0, op.value); else if (op.op === "replace") parent[i] = op.value; else if (op.op === "remove") parent.splice(i, 1);
    } else {
      if (op.op === "add" || op.op === "replace") parent[key] = op.value; else if (op.op === "remove") delete parent[key];
    }
  }
  return doc;
}
