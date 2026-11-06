// Shared page logic for the OpenUI Lang examples: raw program text streams in, the
// BROWSER parses it incrementally (common/web/openui.js) and re-renders root.
import { readSSE, logTo } from "/common/web/sse.js";
import { renderNode, COMPONENTS } from "/common/web/catalog.js";
import { Program, SIGNATURES, HTML_SIGNATURES } from "/common/web/openui.js";

export function setup({ sigs = { ...SIGNATURES, ...HTML_SIGNATURES }, registry = COMPONENTS, actionRoute = null } = {}) {
  const $ = (id) => document.getElementById(id), log = logTo($("log"));
  let prog = new Program(sigs), t0 = 0, first = null;
  const render = () => { const t = prog.tree(); if (t) { $("ui").replaceChildren(renderNode(t, onAction, registry)); first ??= performance.now() - t0; } };
  async function pump(route, body) {
    t0 = performance.now(); first = null;
    for await (const ev of readSSE(route, body)) {
      if (ev.text != null) { const done = prog.feed(ev.text); for (const n of done) log("stmt", n + " = " + JSON.stringify(prog.defs[n]).slice(0, 90)); if (done.length) render(); }
      if (ev.end) { for (const n of prog.close()) log("stmt", n); render(); }
      if (ev.note) log("--", ev.note);
      if (ev.error) { log("ERROR", ev.error); $("say").textContent = ev.error; }
    }
    if (prog.errors.length) log("parse errors", prog.errors);
    $("say").textContent += ` first paint ${Math.round(first ?? 0)} ms · complete ${Math.round(performance.now() - t0)} ms`;
  }
  function onAction(action, params) {
    log("action ->", { action, params });
    // In OpenUI Lang an update is just new assignments: re-defining `title = ...` replaces it.
    if (actionRoute) { $("say").textContent = ""; pump(actionRoute, { action, params }); }
    else $("say").textContent = `action ${action} (handled in 04_mixed)`;
  }
  document.querySelector("form").onsubmit = (e) => { e.preventDefault(); $("log").textContent = ""; $("say").textContent = ""; prog = new Program(sigs); pump("api/stream", { prompt: e.target.q.value }); };
  document.querySelector("form").requestSubmit();
}
