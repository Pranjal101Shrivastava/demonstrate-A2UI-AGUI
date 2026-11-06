// Shared browser renderer for the component catalog (mirrors common/catalog.py).
// Every declarative example converts its own format (AG-UI state, A2UI, json-render,
// OpenUI Lang, harness spec) into a nested node {type, props, children:[node]}
// and hands it to renderNode(). Unknown types render as a visible error, never as HTML.
import { mountSandboxed } from "./sandbox.js";

const h = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = String(text); return e; };

export const COMPONENTS = {
  Stack: (p, kids) => { const e = h("div", "g-stack " + (p.direction === "row" ? "row" : "column")); if (p.gap) e.style.gap = p.gap + "px"; kids.forEach(k => e.append(k)); return e; },
  Card: (p, kids) => { const e = h("div", "g-card"); if (p.title) e.append(h("div", "g-title", p.title)); kids.forEach(k => e.append(k)); return e; },
  Text: (p) => h(p.variant === "h1" ? "h1" : p.variant === "h2" ? "h2" : "p", "g-" + (p.variant || "body"), p.text),
  Metric: (p) => { const e = h("div", "g-metric"); e.append(h("div", "v", p.value), h("div", "l", p.label)); return e; },
  Table: (p) => {
    const t = h("table", "g-table"), hr = h("tr");
    (p.columns || []).forEach(c => hr.append(h("th", null, c))); t.append(hr);
    (p.rows || []).forEach(r => { const tr = h("tr"); r.forEach(c => tr.append(h("td", null, c))); t.append(tr); });
    return t;
  },
  BarChart: (p) => {
    const wrap = h("div", "g-chart"); if (p.title) wrap.append(h("div", "g-muted", p.title));
    const bars = h("div", "g-bars"), max = Math.max(1, ...(p.values || []));
    (p.values || []).forEach((v, i) => { const b = h("div", "bar"); b.style.height = (100 * v / max) + "%"; b.append(h("b", null, v), h("span", null, (p.labels || [])[i] ?? "")); bars.append(b); });
    wrap.append(bars); return wrap;
  },
  Button: (p, _k, onAction) => { const b = h("button", null, p.label); b.onclick = () => onAction && onAction(p.action, p.params || {}); return b; },
  // Hybrid escape hatch: model-written HTML, but only inside a sandboxed iframe.
  GeneratedView: (p, _k, onAction) => mountSandboxed(p.html || "", { height: p.height || 220, onAction }),
};

export function renderNode(node, onAction, allowed = COMPONENTS) {
  if (node == null) return h("div", "pending", "…");
  if (typeof node === "string") return h("span", null, node);
  const fn = allowed[node.type];
  if (!fn) return h("div", "g-error", `Rejected: unknown component "${node.type}"`);
  const kids = (node.children || []).map(c => renderNode(c, onAction, allowed));
  return fn(node.props || {}, kids, onAction);
}

// Flat element map {root, elements:{id:{type,props,children:[ids]}}} -> nested tree.
// Missing children (still streaming) become placeholders, so partial specs render.
export function flatToTree(spec) {
  const els = (spec && spec.elements) || {};
  const build = (id, seen = new Set()) => {
    const el = els[id]; if (!el || seen.has(id)) return null;
    seen.add(id);
    return { type: el.type, props: el.props || {}, children: (el.children || []).map(c => build(c, new Set(seen))) };
  };
  return build(spec && spec.root);
}

export function mount(target, node, onAction) { target.replaceChildren(renderNode(node, onAction)); }
