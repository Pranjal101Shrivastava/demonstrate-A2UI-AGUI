"""Hand-written SVG charts (no plotting library needed). Colours adapt to light/dark mode."""
from html import escape

STYLE = """<style>
.bg{fill:#ffffff}.ax{stroke:#c9ccd3;stroke-width:1}.tx{fill:#2b2f36;font:12px system-ui,sans-serif}
.mut{fill:#6b7280;font:11px system-ui,sans-serif}.err{stroke:#2b2f36;stroke-width:1.5}
@media (prefers-color-scheme:dark){.bg{fill:#14161a}.ax{stroke:#3a3f48}.tx{fill:#e6e8ec}.mut{fill:#9aa1ad}.err{stroke:#e6e8ec}}
</style>"""
PALETTE = ["#4f7cff", "#e8743b", "#19a979", "#a35bd6", "#d4a017", "#d64f7a", "#3bb3c3", "#7a8699"]


def bar_chart(items, title, ylabel, ymax=100, width=720, height=340):
    """items: [(label, mean, std, highlight_bool)]"""
    left, right, top, bottom = 56, 16, 40, 78
    pw, ph = width - left - right, height - top - bottom
    n = len(items)
    bw = pw / n * 0.62
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
           STYLE, f'<rect class="bg" width="{width}" height="{height}" rx="8"/>',
           f'<text class="tx" x="{left}" y="22" font-weight="600">{escape(title)}</text>']
    for k in range(0, 101, 20):
        y = top + ph - ph * k / ymax
        out.append(f'<line class="ax" x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="mut" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{k}</text>')
    out.append(f'<text class="mut" transform="translate(14,{top + ph / 2}) rotate(-90)" text-anchor="middle">{escape(ylabel)}</text>')
    for i, (label, m, s, hl) in enumerate(items):
        cx = left + pw * (i + 0.5) / n
        y = top + ph - ph * m / ymax
        color = PALETTE[i % len(PALETTE)] if hl else "#9aa1ad"
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{top + ph - y:.1f}" rx="3" fill="{color}"/>')
        if s:
            y1, y2 = top + ph - ph * (m - s) / ymax, top + ph - ph * min(ymax, m + s) / ymax
            out.append(f'<line class="err" x1="{cx:.1f}" x2="{cx:.1f}" y1="{y1:.1f}" y2="{y2:.1f}"/>')
        out.append(f'<text class="tx" x="{cx:.1f}" y="{y - 6 if not s else y2 - 6:.1f}" text-anchor="middle">{m:.1f}</text>')
        words = label.split(" ")
        for j, w in enumerate(words[:3]):
            out.append(f'<text class="mut" x="{cx:.1f}" y="{top + ph + 16 + 13 * j}" text-anchor="middle">{escape(w)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def line_chart(series, title, xlabel, ylabel, ymax=48, width=720, height=340):
    """series: [(label, [(x, y), ...])]"""
    left, right, top, bottom = 56, 150, 40, 48
    pw, ph = width - left - right, height - top - bottom
    xmax = max(x for _, pts in series for x, _ in pts) or 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
           STYLE, f'<rect class="bg" width="{width}" height="{height}" rx="8"/>',
           f'<text class="tx" x="{left}" y="22" font-weight="600">{escape(title)}</text>']
    for k in range(5):
        v = ymax * k / 4
        y = top + ph - ph * k / 4
        out.append(f'<line class="ax" x1="{left}" x2="{left + pw}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="mut" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{v:.0f}</text>')
    for k in range(5):
        xv = xmax * k / 4
        out.append(f'<text class="mut" x="{left + pw * k / 4:.1f}" y="{top + ph + 16}" text-anchor="middle">{xv:,.0f}</text>')
    out.append(f'<text class="mut" x="{left + pw / 2}" y="{height - 6}" text-anchor="middle">{escape(xlabel)}</text>')
    out.append(f'<text class="mut" transform="translate(14,{top + ph / 2}) rotate(-90)" text-anchor="middle">{escape(ylabel)}</text>')
    for i, (label, pts) in enumerate(series):
        c = PALETTE[i % len(PALETTE)]
        d = " ".join(f"{'M' if j == 0 else 'L'}{left + pw * x / xmax:.1f},{top + ph - ph * min(y, ymax) / ymax:.1f}"
                     for j, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2"/>')
        ly = top + 14 + 18 * i
        out.append(f'<rect x="{left + pw + 12}" y="{ly - 9}" width="12" height="3" fill="{c}"/>')
        out.append(f'<text class="tx" x="{left + pw + 30}" y="{ly - 4}">{escape(label)}</text>')
    out.append("</svg>")
    return "\n".join(out)
