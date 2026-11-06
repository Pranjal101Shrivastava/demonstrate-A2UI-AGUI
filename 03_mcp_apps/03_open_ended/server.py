"""MCP server for MCP Apps · OPEN-ENDED: the tool returns model-written HTML.
The ui:// view is only a shell that mounts it in a NESTED sandboxed iframe:
two boundaries (host -> view -> generated content)."""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
from common.fixtures import custom_html, days_from
from common.llm import complete, strip_fences
from common.mcp import MCPServer, view_page
from common.sandbox import check_html

server = MCPServer("campus-cafe-open-ended")
URI = "ui://cafe/generated-shell.html"
SYSTEM = ("Write one self-contained HTML fragment (inline only, no URLs/fetch/storage) visualising the "
          "Campus Cafe data requested. Use genux.action(name, params) for buttons. HTML only.")


def generate_view(request: str):
    html = strip_fences(complete(SYSTEM, request, lambda p: custom_html(days_from(p))))
    problems = check_html(html)
    if problems:
        raise ValueError("generated HTML rejected: " + "; ".join(problems))
    return {"html": html, "_text": f"Generated a custom {len(html)}-byte view."}


server.tool("generate_view", "Generate a bespoke visualisation of Campus Cafe data for a free-text request.",
            {"type": "object", "properties": {"request": {"type": "string"}}, "required": ["request"]},
            generate_view, resource_uri=URI)

VIEW_SCRIPT = r"""
const app = document.getElementById("app");
const show = (html) => app.replaceChildren(mountSandboxed(html, { height: 250, allowedActions: ["set_days"], onAction: async (a, p) => {
  show((await mcp.callTool("generate_view", { request: `custom revenue trend for ${p.days} days` })).structuredContent.html);
} }));
mcp.on("ui/notifications/tool-result", (r) => show(r.structuredContent.html));
mcp.connect();
"""
server.resource(URI, "Generated view shell", lambda: view_page('<div id="app">waiting…</div>', VIEW_SCRIPT, ("sandbox.js",)))

if __name__ == "__main__":
    server.serve_stdio()
