// Shared host page for the four MCP Apps examples.
import { createHost } from "/common/web/mcp_host.js";
import { logTo } from "/common/web/sse.js";

const $ = (id) => document.getElementById(id), log = logTo($("log"));
const host = createHost({ mcpUrl: "api/mcp", log, container: $("ui") });
const ready = host.connect();
document.querySelector("form").onsubmit = async (e) => {
  e.preventDefault(); await ready;
  // The host's model picks a tool for the prompt (scripted offline, Claude when GENUX_LIVE=1).
  const pick = await (await fetch("api/chat", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ prompt: e.target.q.value, tools: host.tools }) })).json();
  $("say").textContent = `model chose ${pick.tool}(${JSON.stringify(pick.arguments)})`;
  log("model       picks", `${pick.tool}(${JSON.stringify(pick.arguments)})`);
  await host.callAndMount(pick.tool, pick.arguments);
};
document.querySelector("form").requestSubmit();
