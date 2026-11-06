// View side of the MCP Apps bridge (inlined into every ui:// resource).
// JSON-RPC 2.0 over postMessage to the host window.
const mcp = (() => {
  let nextId = 1; const pending = {}, handlers = {};
  window.addEventListener("message", (ev) => {
    if (ev.source !== window.parent) return;
    const m = ev.data; if (!m || m.jsonrpc !== "2.0") return;
    if (m.id != null && pending[m.id]) { const p = pending[m.id]; delete pending[m.id]; m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); return; }
    if (m.method && handlers[m.method]) handlers[m.method](m.params || {});
  });
  const request = (method, params) => new Promise((resolve, reject) => { const id = nextId++; pending[id] = { resolve, reject }; parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*"); });
  const notify = (method, params) => parent.postMessage({ jsonrpc: "2.0", method, params }, "*");
  const on = (method, fn) => { handlers[method] = fn; };
  const reportSize = () => notify("ui/notifications/size-changed", { width: document.body.scrollWidth, height: document.documentElement.scrollHeight });
  new ResizeObserver(reportSize).observe(document.body);
  // Lifecycle: ui/initialize (request) -> ui/notifications/initialized
  async function connect() {
    const init = await request("ui/initialize", { protocolVersion: "2025-06-18", appInfo: { name: document.title || "view", version: "1.0" }, appCapabilities: {} });
    notify("ui/notifications/initialized", {});
    return init;
  }
  const callTool = (name, args) => request("tools/call", { name, arguments: args });
  return { request, notify, on, connect, callTool, reportSize };
})();
