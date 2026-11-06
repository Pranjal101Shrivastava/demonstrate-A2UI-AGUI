"""Scripted model outputs shared by the examples.

These are what a model *would* return. Live mode replaces them with real
Claude output, which then goes through the very same validation.
"""
import re

from common.data import sales


def days_from(prompt: str, default: int = 7) -> int:
    m = re.search(r"(\d+)\s*day", prompt or "")
    return max(1, min(7, int(m.group(1)))) if m else default


def dashboard_spec(days: int, hybrid: bool = False) -> dict:
    """A flat element map {root, elements} built only from catalog components."""
    s = sales(days)
    els = {
        "root": {"type": "Stack", "props": {"direction": "column"}, "children": ["title", "kpis", "chart", "table", "actions"]},
        "title": {"type": "Text", "props": {"text": f"Campus Cafe - last {s['days']} days", "variant": "h1"}},
        "kpis": {"type": "Stack", "props": {"direction": "row"}, "children": ["m_cups", "m_rev", "m_best"]},
        "m_cups": {"type": "Metric", "props": {"label": "Cups sold", "value": s["total_cups"]}},
        "m_rev": {"type": "Metric", "props": {"label": "Revenue", "value": f"${s['total_revenue']:.2f}"}},
        "m_best": {"type": "Metric", "props": {"label": "Best day", "value": s["best_day"]}},
        "chart": {"type": "Card", "props": {"title": "Cups per day"}, "children": ["bars"]},
        "bars": {"type": "BarChart", "props": {"labels": s["labels"], "values": s["cups"]}},
        "table": {"type": "Card", "props": {"title": "Stock"}, "children": ["stock"]},
        "stock": {"type": "Table", "props": {"columns": ["Item", "Qty"], "rows": [[k, v] for k, v in s["stock"].items()]}},
        "actions": {"type": "Stack", "props": {"direction": "row"}, "children": ["b3", "b7", "restock"]},
        "b3": {"type": "Button", "props": {"label": "Last 3 days", "action": "set_days", "params": {"days": 3}}},
        "b7": {"type": "Button", "props": {"label": "Last 7 days", "action": "set_days", "params": {"days": 7}}},
        "restock": {"type": "Button", "props": {"label": "Reorder beans", "action": "restock", "params": {"item": "beans_kg", "qty": 5}}},
    }
    if hybrid:
        els["root"]["children"].insert(3, "custom")
        els["custom"] = {"type": "GeneratedView", "props": {"html": custom_html(days), "height": 230}}
    return {"root": "root", "elements": els}


def custom_html(days: int) -> str:
    """Open-ended output: a bespoke visual no catalog component offers
    (an SVG revenue line with a hover readout and a peak marker)."""
    s = sales(days)
    w, h, pad = 460, 150, 24
    mx = max(s["revenue"])
    n = len(s["revenue"])
    pts = [(pad + i * (w - 2 * pad) / max(1, n - 1), h - pad - v / mx * (h - 2 * pad)) for i, v in enumerate(s["revenue"])]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    peak = max(range(n), key=lambda i: s["revenue"][i])
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{6 if i == peak else 4}" fill="{"#d6336c" if i == peak else "#2457d6"}" '
        f'onmouseover="r.textContent=\'{s["labels"][i]}: ${s["revenue"][i]:.2f}\'"/>'
        f'<text x="{x:.1f}" y="{h - 4}" font-size="11" text-anchor="middle" fill="#5d6b82">{s["labels"][i]}</text>'
        for i, (x, y) in enumerate(pts)
    )
    return (
        f'<div style="font-weight:600">Revenue trend (custom view)</div>'
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<polyline points="{poly}" fill="none" stroke="#2457d6" stroke-width="2.5"/>{dots}</svg>'
        f'<div>Hover a point: <b id="r">peak {s["labels"][peak]} ${s["revenue"][peak]:.2f}</b></div>'
        f'<button onclick="genux.action(\'set_days\',{{days:3}})">Zoom to 3 days</button>'
    )


def a2ui_dashboard(days: int, html: bool = False, actions: bool = False) -> list:
    """Scripted A2UI reply: components bound to a data model, as message dicts."""
    from common import a2ui
    s = sales(days)
    cat = a2ui.CAFE_HTML_CATALOG if html else a2ui.CAFE_CATALOG
    kids = ["title", "kpis", "chart_card", "stock_card"]
    comps = [
        {"id": "root", "component": "Column", "children": kids},
        {"id": "title", "component": "Text", "variant": "h1", "text": {"path": "/title"}},
        {"id": "kpis", "component": "Row", "children": ["cups", "rev", "best"]},
        {"id": "cups", "component": "Metric", "label": "Cups sold", "value": {"path": "/sales/total_cups"}},
        {"id": "rev", "component": "Metric", "label": "Revenue", "value": {"path": "/sales/revenue_fmt"}},
        {"id": "best", "component": "Metric", "label": "Best day", "value": {"path": "/sales/best_day"}},
        {"id": "chart_card", "component": "Card", "title": "Cups per day", "child": "chart"},
        {"id": "chart", "component": "BarChart", "labels": {"path": "/sales/labels"}, "values": {"path": "/sales/cups"}},
        {"id": "stock_card", "component": "Card", "title": "Stock", "child": "stock"},
        {"id": "stock", "component": "Table", "columns": ["Item", "Qty"], "rows": {"path": "/stock_rows"}},
    ]
    if html:
        kids.insert(3, "custom")
        comps.append({"id": "custom", "component": "HtmlFrame", "height": 230, "html": {"path": "/custom_html"}})
    if actions:
        kids.append("actions")
        comps += [
            {"id": "actions", "component": "Row", "children": ["d3", "d7", "reorder"]},
            {"id": "d3", "component": "Button", "label": "Last 3 days", "action": {"name": "set_days", "context": {"days": 3}}},
            {"id": "d7", "component": "Button", "label": "Last 7 days", "action": {"name": "set_days", "context": {"days": 7}}},
            {"id": "reorder", "component": "Button", "label": "Reorder beans", "action": {"name": "restock", "context": {"item": "beans_kg", "qty": 5}}},
        ]
    return [
        a2ui.create_surface("cafe", cat),
        a2ui.update_components("cafe", comps),
        a2ui.update_data("cafe", "/", a2ui_data(days, html)),
    ]


def a2ui_data(days: int, html: bool = False, stock: dict = None) -> dict:
    s = sales(days)
    s["revenue_fmt"] = f"${s['total_revenue']:.2f}"
    d = {"title": f"Campus Cafe - last {s['days']} days", "sales": s,
         "stock_rows": [[k, v] for k, v in (stock or s["stock"]).items()]}
    if html:
        d["custom_html"] = custom_html(days)
    return d
