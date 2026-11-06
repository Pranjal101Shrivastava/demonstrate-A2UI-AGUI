// Web surface for the harness examples: AG-UI events in, transcript + rendered UI out.
import { readSSE, logTo } from "/common/web/sse.js";
import { renderNode, flatToTree, COMPONENTS as C } from "/common/web/catalog.js";
import { mountSandboxed } from "/common/web/sandbox.js";

const PRESETS = {
  SalesCard: (p) => C.Card({ title: p.title }, [C.Stack({ direction: "row" }, [C.Metric({ label: "Cups", value: p.cups }), C.Metric({ label: "Revenue", value: p.revenue }), C.Metric({ label: "Best day", value: p.best })])]),
  CupsChart: (p) => C.Card({ title: "Cups per day" }, [C.BarChart(p)]),
  StockTable: (p) => C.Card({ title: "Stock" }, [C.Table({ columns: ["Item", "Qty"], rows: p.rows })]),
};

export function setup({ actionRoute = null, rerun = null } = {}) {
  const $ = (id) => document.getElementById(id), log = logTo($("log"));
  const draw = (r) => {
    if (r.kind === "component") $("ui").replaceChildren(PRESETS[r.name](r.props));
    if (r.kind === "spec") $("ui").replaceChildren(renderNode(flatToTree(r.spec), onAction));
    if (r.kind === "html") $("ui").replaceChildren(mountSandboxed(r.html, { height: 250, allowedActions: ["set_days"], onAction }));
  };
  async function run(route, body) {
    const calls = {};
    for await (const ev of readSSE(route, { threadId: "web", ...body })) {
      if (ev.type === "TOOL_CALL_START") calls[ev.toolCallId] = { name: ev.toolCallName, args: "" };
      if (ev.type === "TOOL_CALL_ARGS") calls[ev.toolCallId].args += ev.delta;
      if (ev.type === "TOOL_CALL_END") log("model → tool", `${calls[ev.toolCallId].name}(${calls[ev.toolCallId].args.slice(0, 110)})`);
      if (ev.type === "TOOL_CALL_RESULT") log("tool → model", ev.content.slice(0, 110));
      if (ev.type === "TEXT_MESSAGE_CONTENT") { log("model says", ev.delta); $("say").textContent = ev.delta; }
      if (ev.type === "CUSTOM" && ev.name === "render") { log("surface", "render " + ev.value.kind); draw(ev.value); }
      if (ev.type === "RUN_STARTED" || ev.type === "RUN_FINISHED") log(ev.type);
    }
  }
  function onAction(action, params) {
    log("user → harness", `${action} ${JSON.stringify(params)}`);
    if (actionRoute) run(actionRoute, { action, params });
    else if (rerun) { const q = document.querySelector("form").q; q.value = rerun(action, params); run("api/run", { prompt: q.value }); }  // start a fresh agent run
    else $("say").textContent = `action ${action} (handled in 04_mixed)`;
  }
  document.querySelector("form").onsubmit = (e) => { e.preventDefault(); $("log").textContent = ""; run("api/run", { prompt: e.target.q.value }); };
  document.querySelector("form").requestSubmit();
}
