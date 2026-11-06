// Browser A2UI surface: applies createSurface / updateComponents / updateDataModel /
// deleteSurface messages, resolves {path} bindings against the data model, converts
// the flat component list to a nested node and renders it with the shared catalog.
import { renderNode, COMPONENTS } from "./catalog.js";
import { mountSandboxed } from "./sandbox.js";

export class Surface {
  constructor(el, { onAction } = {}) { this.el = el; this.onAction = onAction; this.components = {}; this.data = {}; this.catalogId = null; this.id = null; }
  apply(m) {
    if (m.createSurface) { this.id = m.createSurface.surfaceId; this.catalogId = m.createSurface.catalogId; }
    if (m.updateComponents) for (const c of m.updateComponents.components) this.components[c.id] = c;
    if (m.updateDataModel) this.set(m.updateDataModel.path, m.updateDataModel.value);
    if (m.deleteSurface) { this.components = {}; this.data = {}; }
    this.render();
  }
  set(path, value) {
    const ps = path.split("/").filter(Boolean);
    if (!ps.length) { this.data = value; return; }
    let cur = this.data; for (const p of ps.slice(0, -1)) cur = (cur[p] ??= {});
    cur[ps.at(-1)] = value;
  }
  get(path) { return path.split("/").filter(Boolean).reduce((c, p) => c?.[p], this.data); }
  resolve(v) { return v && typeof v === "object" && !Array.isArray(v) && Object.keys(v).length === 1 && "path" in v ? this.get(v.path) : v; }

  // A2UI component -> shared catalog node. This mapping IS the client's catalog.
  toNode(id) {
    const c = this.components[id]; if (!c) return null;
    const p = {}; for (const [k, v] of Object.entries(c)) if (!["id", "component", "child", "children"].includes(k)) p[k] = this.resolve(v);
    const kids = [...(c.child ? [c.child] : []), ...(c.children || [])].map(k => this.toNode(k));
    const map = {
      Column: () => ({ type: "Stack", props: { direction: "column" }, children: kids }),
      Row: () => ({ type: "Stack", props: { direction: "row" }, children: kids }),
      Card: () => ({ type: "Card", props: { title: p.title }, children: kids }),
      Text: () => ({ type: "Text", props: { text: p.text, variant: p.variant } }),
      Divider: () => ({ type: "Text", props: { text: "―――", variant: "muted" } }),
      Metric: () => ({ type: "Metric", props: p }),
      BarChart: () => ({ type: "BarChart", props: p }),
      Table: () => ({ type: "Table", props: p }),
      // Actions carry a name + context; context values may be bindings too.
      Button: () => ({ type: "Button", props: { label: p.label, action: p.action?.name, params: Object.fromEntries(Object.entries(p.action?.context || {}).map(([k, v]) => [k, this.resolve(v)])), _src: id } }),
      HtmlFrame: () => ({ type: "GeneratedView", props: { html: p.html, height: p.height } }),
    };
    return map[c.component] ? map[c.component]() : { type: "Unknown:" + c.component };
  }
  render() {
    if (!this.components.root) { this.el.textContent = ""; return; }
    this.el.replaceChildren(renderNode(this.toNode("root"), (name, context) =>
      this.onAction && this.onAction({ version: "v0.9", action: { name, surfaceId: this.id, context } })));
  }
}
