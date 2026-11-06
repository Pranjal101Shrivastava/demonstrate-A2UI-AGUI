"""A minimal MCP server + client (JSON-RPC 2.0 over stdio), with the MCP Apps extension.

MCP Apps (SEP-1865, https://modelcontextprotocol.io/extensions/apps/overview):
  * a tool declares  _meta.ui.resourceUri = "ui://..."
  * resources/read of that URI returns HTML with mimeType "text/html;profile=mcp-app"
  * the HOST mounts that HTML in a sandboxed iframe and talks to it over
    postMessage JSON-RPC (ui/initialize, ui/notifications/tool-input,
    ui/notifications/tool-result, tools/call, ui/notifications/size-changed).

No SDK on purpose: every message is visible. Real projects would use the
official `mcp` Python SDK / `@modelcontextprotocol/ext-apps`.
"""
import json
import pathlib
import re
import subprocess
import sys
import threading

PROTOCOL_VERSION = "2025-06-18"
APP_MIME = "text/html;profile=mcp-app"
UI_EXTENSION = "io.modelcontextprotocol/ui"
WEB = pathlib.Path(__file__).parent / "web"


# ---------------------------------------------------------------- server side
class MCPServer:
    def __init__(self, name):
        self.name, self.tools, self.resources = name, {}, {}

    def tool(self, name, description, input_schema, handler, resource_uri=None, visibility=None):
        meta = {}
        if resource_uri:
            meta["ui"] = {"resourceUri": resource_uri}
            if visibility:
                meta["ui"]["visibility"] = visibility  # e.g. ["app"]: callable by the view, hidden from the model
        self.tools[name] = ({"name": name, "description": description, "inputSchema": input_schema, **({"_meta": meta} if meta else {})}, handler)

    def resource(self, uri, name, text_fn):
        self.resources[uri] = ({"uri": uri, "name": name, "mimeType": APP_MIME}, text_fn)

    def handle(self, req):
        method, params, rid = req.get("method"), req.get("params") or {}, req.get("id")
        if rid is None:  # notification: no response
            return None
        try:
            if method == "initialize":
                result = {"protocolVersion": PROTOCOL_VERSION, "serverInfo": {"name": self.name, "version": "1.0"},
                          "capabilities": {"tools": {}, "resources": {}, "extensions": {UI_EXTENSION: {}}}}
            elif method == "tools/list":
                result = {"tools": [t for t, _ in self.tools.values()]}
            elif method == "tools/call":
                _, fn = self.tools[params["name"]]
                structured = fn(**(params.get("arguments") or {}))
                result = {"content": [{"type": "text", "text": structured.pop("_text", json.dumps(structured)[:400])}],
                          "structuredContent": structured}
            elif method == "resources/list":
                result = {"resources": [r for r, _ in self.resources.values()]}
            elif method == "resources/read":
                meta, fn = self.resources[params["uri"]]
                result = {"contents": [{"uri": meta["uri"], "mimeType": APP_MIME, "text": fn()}]}
            else:
                return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}}
            return {"jsonrpc": "2.0", "id": rid, "result": result}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(e)}}

    def serve_stdio(self):
        """MCP stdio transport: newline-delimited JSON-RPC on stdin/stdout."""
        for line in sys.stdin:
            if line.strip():
                resp = self.handle(json.loads(line))
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()


def inline_modules(*names):
    """Inline common/web ES modules into one classic <script> so a ui:// view is self-contained
    (a sandboxed srcdoc iframe with default-src 'none' cannot fetch scripts)."""
    out = []
    for n in names:
        src = (WEB / n).read_text()
        src = re.sub(r"^import .*?;\s*$", "", src, flags=re.M)
        src = re.sub(r"^export\s+", "", src, flags=re.M)
        out.append(f"// ---- {n}\n{src}".replace("</script", "<\\/script"))  # never close the host <script> early
    return "\n".join(out)


def view_page(body_html, script, extra_modules=()):
    """Wrap a view: CSP, the shared view-side bridge, optional inlined modules, then the view script."""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; frame-src 'self' about: data:">
<style>{(WEB / 'style.css').read_text()} body{{background:transparent;padding:4px}}</style></head>
<body>{body_html}
<script>
{(WEB / 'mcp_view_bridge.js').read_text()}
{inline_modules(*extra_modules)}
{script}
</script></body></html>"""


# ---------------------------------------------------------------- client side
class MCPClient:
    """Spawns an MCP server as a subprocess and talks JSON-RPC over its stdio."""

    def __init__(self, server_path):
        self.proc = subprocess.Popen([sys.executable, str(server_path), "--stdio"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, text=True, bufsize=1)
        self.lock, self.next_id, self.log = threading.Lock(), 1, []

    def request(self, method, params=None):
        with self.lock:
            rid, self.next_id = self.next_id, self.next_id + 1
            msg = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
            resp = json.loads(self.proc.stdout.readline())
        self.log.append((msg, resp))
        if "error" in resp:
            raise RuntimeError(resp["error"]["message"])
        return resp["result"]

    def notify(self, method, params=None):
        with self.lock:
            self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}}) + "\n")
            self.proc.stdin.flush()

    def raw(self, msg):
        """Forward an arbitrary JSON-RPC message from the browser host."""
        if "id" not in msg:
            self.notify(msg["method"], msg.get("params"))
            return None
        with self.lock:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
            return json.loads(self.proc.stdout.readline())

    def close(self):
        self.proc.stdin.close()  # EOF ends serve_stdio()
        self.proc.wait(timeout=5)
        self.proc.stdout.close()


def summarize(msg, resp):
    """One-line trace of a request/response pair for the terminal walkthrough."""
    m = msg["method"]
    r = resp.get("result", {})
    if m == "initialize":
        s = f"serverInfo={r['serverInfo']['name']} extensions={list(r['capabilities'].get('extensions', {}))}"
    elif m == "tools/list":
        s = ", ".join(f"{t['name']}" + (f" -> {t['_meta']['ui']['resourceUri']}" if t.get('_meta') else "") for t in r["tools"])
    elif m == "tools/call":
        s = f"{msg['params']['name']}({json.dumps(msg['params'].get('arguments', {}))}) -> structuredContent keys {list(r.get('structuredContent', {}))}"
    elif m == "resources/read":
        c = r["contents"][0]
        s = f"{c['uri']} mimeType={c['mimeType']} ({len(c['text'])} bytes of HTML)"
    else:
        s = json.dumps(r)[:100]
    return f"  -> {m:<16} <- {s}"
