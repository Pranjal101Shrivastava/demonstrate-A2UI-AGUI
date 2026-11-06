// Host side of MCP Apps: an MCP client (JSON-RPC forwarded to the stdio server by
// the local Python host) + the postMessage bridge to a sandboxed ui:// view.
export function createHost({ mcpUrl, log, container }) {
  let id = 1, tools = [];
  async function rpc(method, params) {
    const msg = { jsonrpc: "2.0", id: id++, method, params };
    log(`->          ${method}`, params && method === "tools/call" ? `${params.name}(${JSON.stringify(params.arguments)})` : "");
    const res = await (await fetch(mcpUrl, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(msg) })).json();
    if (res.error) { log(`<-          error`, res.error.message); throw new Error(res.error.message); }
    return res.result;
  }
  const notify = (method, params) => { log(`->          ${method}`); return fetch(mcpUrl, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", method, params }) }); };

  async function connect() {
    const init = await rpc("initialize", { protocolVersion: "2025-06-18", clientInfo: { name: "genux-host", version: "1.0" }, capabilities: { extensions: { "io.modelcontextprotocol/ui": { mimeTypes: ["text/html;profile=mcp-app"] } } } });
    log(`<-          initialize`, `server=${init.serverInfo.name}`);
    await notify("notifications/initialized", {});
    tools = (await rpc("tools/list", {})).tools;
    log(`<-          tools/list`, tools.map(t => t.name + (t._meta?.ui ? " [ui]" : "")).join(", "));
    return tools;
  }

  async function callAndMount(name, args) {
    const tool = tools.find(t => t.name === name); if (!tool) throw new Error("unknown tool " + name);
    const result = await rpc("tools/call", { name, arguments: args });
    log(`<-          tools/call`, `structuredContent keys: ${Object.keys(result.structuredContent || {})}`);
    const uri = tool._meta?.ui?.resourceUri;
    if (!uri) { container.textContent = result.content?.[0]?.text || ""; return result; }
    const html = (await rpc("resources/read", { uri })).contents[0];
    log(`<-          resources/read`, `${html.mimeType}, ${html.text.length} bytes`);
    mount(uri, html.text, args, result);
    return result;
  }

  function mount(uri, html, args, result) {
    const frame = document.createElement("iframe");
    frame.className = "g-frame"; frame.style.height = "120px";
    frame.setAttribute("sandbox", "allow-scripts");          // opaque origin, no same-origin access
    frame.srcdoc = html;
    log(`host        mount ${uri}`, "sandbox=allow-scripts");
    const send = (m) => frame.contentWindow.postMessage(m, "*");
    window.onmessage = async (ev) => {
      if (ev.source !== frame.contentWindow) return;
      const m = ev.data; if (!m || m.jsonrpc !== "2.0") return;
      if (m.method === "ui/notifications/size-changed") { frame.style.height = Math.min(900, m.params.height + 4) + "px"; return; }
      log(`view->host  ${m.method}`, m.method === "tools/call" ? `${m.params.name}(${JSON.stringify(m.params.arguments)})` : "");
      if (m.method === "ui/initialize") {
        send({ jsonrpc: "2.0", id: m.id, result: { protocolVersion: "2025-06-18", hostInfo: { name: "genux-host", version: "1.0" },
          hostCapabilities: { serverTools: {} }, hostContext: { theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light", displayMode: "inline" } } });
        log("host->view  response", "hostContext + hostCapabilities");
      } else if (m.method === "ui/notifications/initialized") {
        send({ jsonrpc: "2.0", method: "ui/notifications/tool-input", params: { arguments: args } }); log("host->view  ui/notifications/tool-input");
        send({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: result }); log("host->view  ui/notifications/tool-result");
      } else if (m.method === "tools/call") {
        // The HOST decides: a view may only call tools of its own server that are marked for app use.
        const t = tools.find(t => t.name === m.params.name);
        if (!t || !t._meta?.ui) { send({ jsonrpc: "2.0", id: m.id, error: { code: -32001, message: "tool not allowed for this view" } }); log("host->view  error", "tool not allowed"); return; }
        try { const r = await rpc("tools/call", m.params); send({ jsonrpc: "2.0", id: m.id, result: r }); log("host->view  response", "tool result"); }
        catch (e) { send({ jsonrpc: "2.0", id: m.id, error: { code: -32000, message: e.message } }); }
      }
    };
    container.replaceChildren(frame);
  }
  return { connect, callAndMount, rpc, get tools() { return tools; } };
}
