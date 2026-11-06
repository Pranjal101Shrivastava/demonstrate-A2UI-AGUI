// Mount model-generated HTML in a sandboxed iframe.
//  - sandbox="allow-scripts" WITHOUT allow-same-origin => opaque origin: no cookies,
//    no storage, no access to the parent DOM.
//  - A CSP meta tag blocks all network (default-src 'none'); inline script/style only.
//  - The only channel back is postMessage with ONE allowed shape:
//      {type:"genux:action", action:"<name>", params:{...}}
//    and the host still decides whether that action is allowed.
export const CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:";

export function wrapHtml(html) {
  return `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${CSP}">
<style>body{font:14px system-ui,sans-serif;margin:10px;color:#1d2433}</style></head><body>
${html}
<script>window.genux={action:(a,p)=>parent.postMessage({type:"genux:action",action:String(a),params:p||{}},"*")};<\/script>
</body></html>`;  // note: <\/script> keeps this file safe to inline inside a <script> tag
}

export function mountSandboxed(html, { height = 220, onAction, allowedActions } = {}) {
  const f = document.createElement("iframe");
  f.className = "g-frame";
  f.setAttribute("sandbox", "allow-scripts");
  f.style.height = height + "px";
  f.srcdoc = wrapHtml(html);
  window.addEventListener("message", (ev) => {
    if (ev.source !== f.contentWindow) return;               // only from THIS frame
    const m = ev.data;
    if (!m || m.type !== "genux:action" || typeof m.action !== "string") return; // one shape only
    if (allowedActions && !allowedActions.includes(m.action)) { console.warn("blocked action", m.action); return; }
    onAction && onAction(m.action, m.params || {});
  });
  return f;
}
