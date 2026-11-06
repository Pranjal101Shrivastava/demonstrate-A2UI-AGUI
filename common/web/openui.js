// OpenUI Lang streaming parser for the browser (mirror of common/openui.py).
// Feed raw model text as it arrives; every complete statement is parsed at once,
// and root is re-resolved. Undefined (not-yet-streamed) references render as placeholders.
export const SIGNATURES = {
  Stack: ["children", "direction"], Card: ["title", "children"], Text: ["text", "variant"], Metric: ["label", "value"],
  Table: ["columns", "rows"], BarChart: ["labels", "values", "title"], Button: ["label", "action", "params"],
};
export const HTML_SIGNATURES = { HtmlArtifact: ["html", "height"] };
const TOKEN = /\s*(?:("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?)|([A-Za-z_]\w*)|([()\[\]{},=:]))/y;

function tokenize(src) {
  const out = []; TOKEN.lastIndex = 0;
  while (TOKEN.lastIndex < src.length && src.slice(TOKEN.lastIndex).trim()) {
    const at = TOKEN.lastIndex, m = TOKEN.exec(src);
    if (!m) throw new SyntaxError("unexpected character at " + at);
    if (m[1]) out.push(["str", JSON.parse(m[1])]); else if (m[2]) out.push(["num", +m[2]]); else if (m[3]) out.push(["id", m[3]]); else out.push(["p", m[4]]);
  }
  return out;
}
function parseStatement(src) {
  const t = tokenize(src); let i = 0;
  const peek = () => t[i] || [null, null], take = (e) => { const x = t[i++]; if (e && (!x || x[1] !== e)) throw new SyntaxError(`expected ${e}`); return x; };
  const list = (close, item) => { const xs = []; while (peek()[1] !== close) { xs.push(item()); if (peek()[1] === ",") take(","); } take(close); return xs; };
  const expr = () => {
    const [k, v] = take();
    if (k === "str" || k === "num") return v;
    if (k === "id") {
      if (v === "true" || v === "false" || v === "null") return JSON.parse(v);
      if (peek()[1] === "(") { take("("); return { $call: v, args: list(")", expr) }; }
      return { $ref: v };
    }
    if (v === "[") return list("]", expr);
    if (v === "{") { const o = {}; while (peek()[1] !== "}") { const key = take()[1]; take(":"); o[key] = expr(); if (peek()[1] === ",") take(","); } take("}"); return o; }
    throw new SyntaxError("unexpected " + v);
  };
  const [k, name] = take(); if (k !== "id") throw new SyntaxError("statement must start with an identifier");
  take("="); const value = expr(); if (i !== t.length) throw new SyntaxError("trailing tokens");
  return [name, value];
}
function splitStatements(text) {
  const out = []; let depth = 0, inStr = false, esc = false, start = 0;
  for (let j = 0; j < text.length; j++) {
    const ch = text[j];
    if (inStr) { esc = ch === "\\" && !esc; if (ch === '"' && !esc) inStr = false; continue; }
    if (ch === '"') { inStr = true; esc = false; } else if ("([{".includes(ch)) depth++; else if (")]}".includes(ch)) depth--;
    else if (ch === "\n" && depth === 0) { if (text.slice(start, j).trim()) out.push(text.slice(start, j)); start = j + 1; }
  }
  return [out, text.slice(start)];
}
export class Program {
  constructor(sigs = SIGNATURES) { this.sigs = sigs; this.defs = {}; this.buf = ""; this.errors = []; }
  feed(chunk) { this.buf += chunk; const [stmts, rest] = splitStatements(this.buf); this.buf = rest; return stmts.map(s => this.add(s)).filter(Boolean); }
  close() { const r = this.buf; this.buf = ""; return r.trim() ? [this.add(r)].filter(Boolean) : []; }
  add(src) { try { const [n, v] = parseStatement(src); this.defs[n] = v; return n; } catch (e) { this.errors.push(e.message); return null; } }
  tree(name = "root", seen = []) { return name in this.defs && !seen.includes(name) ? this.resolve(this.defs[name], [...seen, name]) : null; }
  resolve(v, seen) {
    if (v && v.$ref) return this.tree(v.$ref, seen);
    if (Array.isArray(v)) return v.map(x => this.resolve(x, seen));
    if (v && v.$call) {
      const sig = this.sigs[v.$call]; if (!sig) return { type: v.$call, props: {} };
      const props = {}; sig.forEach((p, i) => { if (i < v.args.length) props[p] = this.resolve(v.args[i], seen); });
      const children = props.children || []; delete props.children;
      return { type: v.$call === "HtmlArtifact" ? "GeneratedView" : v.$call, props, children };
    }
    return v;
  }
}
