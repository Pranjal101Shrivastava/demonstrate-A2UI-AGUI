"""Python half of the local MCP Apps host: owns the MCP server subprocess and the model call.

Each MCP example's example.py calls make_host(server_path, scripted_pick) to get
ROUTES {"mcp": forward JSON-RPC, "chat": model picks a tool} plus a cli() trace.
"""
import json

from common.llm import complete, strip_fences
from common.mcp import MCPClient, summarize

_clients = {}


def client_for(server_path):
    key = str(server_path)
    if key not in _clients:
        _clients[key] = MCPClient(server_path)
    return _clients[key]


def make_routes(server_path, scripted_pick):
    def mcp(body):
        return client_for(server_path).raw(body) or {}

    def chat(body):
        # Tools marked visibility=["app"] are for the view only; the model never sees them.
        tools = [t for t in body.get("tools", []) if t.get("_meta", {}).get("ui", {}).get("visibility") != ["app"]]
        system = ("Pick ONE tool for the user's request. Tools:\n" + "\n".join(f"- {t['name']}: {t['description']} schema={json.dumps(t['inputSchema'])}" for t in tools)
                  + '\nReply JSON only: {"tool": name, "arguments": {...}}')
        return json.loads(strip_fences(complete(system, body.get("prompt", ""), scripted_pick)))

    return {"mcp": mcp, "chat": chat}


def trace(server_path, tool, args, out=print):
    """Run the host's server-side conversation and print it (the browser does the same + the bridge)."""
    c = MCPClient(server_path)
    try:
        c.request("initialize", {"protocolVersion": "2025-06-18", "clientInfo": {"name": "cli-host"},
                                 "capabilities": {"extensions": {"io.modelcontextprotocol/ui": {}}}})
        c.notify("notifications/initialized")
        tools = {t["name"]: t for t in c.request("tools/list")["tools"]}
        result = c.request("tools/call", {"name": tool, "arguments": args})
        uri = tools[tool].get("_meta", {}).get("ui", {}).get("resourceUri")
        html = c.request("resources/read", {"uri": uri})["contents"][0]["text"] if uri else None
        for msg, resp in c.log:
            out(summarize(msg, resp))
        return tools, result, html
    finally:
        c.close()
