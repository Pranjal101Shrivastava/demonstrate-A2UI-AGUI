// Shared page logic for the json-render examples: apply streamed JSON patches to a spec, re-render.
import { readSSE, logTo } from "/common/web/sse.js";
import { renderNode, flatToTree, COMPONENTS } from "/common/web/catalog.js";
import { applyPatch } from "/common/web/jsonpatch.js";

export function setup({ registry = COMPONENTS, actionRoute = null } = {}) {
  const $ = (id) => document.getElementById(id), log = logTo($("log"));
  let spec = { root: null, elements: {} }, data = {}, t0 = 0, firstPaint = null;
  const render = () => {
    if (!spec.root) return;
    const tree = flatToTree(spec);
    // static mode: preset components read their values from the side-channel data
    const withData = (n) => n && ({ ...n, props: { ...n.props, $data: data }, children: (n.children || []).map(withData) });
    $("ui").replaceChildren(renderNode(withData(tree), onAction, registry));
    if (firstPaint === null) { firstPaint = performance.now() - t0; }
  };
  async function pump(route, body) {
    for await (const ev of readSSE(route, body)) {
      if (ev.patch) { log("patch", ev.patch.path + (ev.patch.op === "add" && ev.patch.value?.type ? `  (${ev.patch.value.type})` : "")); spec = applyPatch(spec, [ev.patch]); render(); }
      if (ev.data) { data = ev.data; log("data", Object.keys(ev.data).join(",")); }
      if (ev.note) log("--", ev.note);
      if (ev.error) { log("ERROR", ev.error); $("say").textContent = ev.error; }
    }
    $("say").textContent += ` first paint ${Math.round(firstPaint ?? 0)} ms · complete ${Math.round(performance.now() - t0)} ms`;
  }
  function onAction(action, params) {
    log("action ->", { action, params });
    if (actionRoute) { t0 = performance.now(); firstPaint = 0; $("say").textContent = ""; pump(actionRoute, { action, params, spec }); }
    else $("say").textContent = `action ${action} (handled in 04_mixed)`;
  }
  document.querySelector("form").onsubmit = (e) => {
    e.preventDefault(); $("log").textContent = ""; $("say").textContent = ""; spec = { root: null, elements: {} }; t0 = performance.now(); firstPaint = null;
    pump("api/stream", { prompt: e.target.q.value });
  };
  document.querySelector("form").requestSubmit();
}
