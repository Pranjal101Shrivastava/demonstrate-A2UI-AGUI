// Minimal SSE reader over fetch (EventSource cannot POST a body).
export async function* readSSE(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "content-type": "application/json", accept: "text/event-stream" }, body: JSON.stringify(body || {}) });
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, i); buf = buf.slice(i + 2);
      const data = frame.split("\n").filter(l => l.startsWith("data:")).map(l => l.slice(5).trimStart()).join("\n");
      if (data) yield JSON.parse(data);
    }
  }
}
export const logTo = (pre) => (label, obj) => { pre.textContent += label + (obj === undefined ? "" : " " + (typeof obj === "string" ? obj : JSON.stringify(obj))) + "\n"; pre.scrollTop = pre.scrollHeight; };
