// Shared page logic for the four A2UI examples: stream A2UI messages over SSE into a Surface.
import { readSSE, logTo } from "/common/web/sse.js";
import { Surface } from "/common/web/a2ui.js";

export function setup({ onActionRoute = null } = {}) {
  const $ = (id) => document.getElementById(id), log = logTo($("log"));
  const show = (m) => { const k = Object.keys(m).find(k => k !== "version"); log(k, m[k]); };
  async function pump(route, body) {
    for await (const ev of readSSE(route, body)) {
      if (ev.a2ui) { show(ev.a2ui); surface.apply(ev.a2ui); }
      if (ev.note) log("--", ev.note);
      if (ev.error) { log("ERROR", ev.error); $("say").textContent = ev.error; }
    }
  }
  const surface = new Surface($("ui"), { onAction: (a) => {
    log("client -> agent action", a.action);
    if (onActionRoute) pump(onActionRoute, a); else $("say").textContent = `action ${a.action.name} (handled in 04_mixed)`;
  } });
  document.querySelector("form").onsubmit = (e) => { e.preventDefault(); $("log").textContent = ""; $("say").textContent = ""; pump("api/stream", { prompt: e.target.q.value }); };
  document.querySelector("form").requestSubmit();
}
