"""Tools shared by the four harness examples (imported as a sibling module)."""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # repo root
from common.data import sales

READ_SALES = ({"description": "Read Campus Cafe sales for the last N days (1-7).",
               "input_schema": {"type": "object", "properties": {"days": {"type": "integer"}}, "required": ["days"]}},
              lambda days: sales(days))


def terminal_surface(render, out=print):
    """Surface #1: the terminal. Same payloads the web page receives as AG-UI CUSTOM events."""
    from common.jsonrender import terminal_render
    kind = render["kind"]
    out("┌─ terminal surface " + "─" * 40)
    if kind == "spec":
        body = terminal_render(render["spec"])
    elif kind == "html":
        body = f"[custom HTML, {len(render['html'])} bytes - open the web surface]"
    else:
        p = render["props"]
        body = {"SalesCard": lambda: f"{p['title']}\n  cups {p['cups']} | revenue {p['revenue']} | best {p['best']}",
                "CupsChart": lambda: "\n".join(f"  {l:>4} {'#' * (v // 3)} {v}" for l, v in zip(p["labels"], p["values"])),
                "StockTable": lambda: "\n".join(f"  {k:<10} {v}" for k, v in p["rows"])}[render["name"]]()
    for line in body.splitlines():
        out("│ " + line)
    out("└" + "─" * 59)
