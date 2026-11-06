// Visit every example in Chromium, wait for it to render, record console errors,
// and save docs/screenshots/<tech>__<mode>.png.   node scripts/screenshots.mjs [baseUrl] [filter]
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");  // npm i playwright if not preinstalled
import fs from "node:fs";

const base = process.argv[2] || "http://127.0.0.1:8000";
const filter = process.argv[3] || "";
const dirs = fs.readdirSync(".").filter(d => /^\d\d_/.test(d)).flatMap(t => fs.readdirSync(t).filter(m => /^\d\d_/.test(m) && fs.existsSync(`${t}/${m}/index.html`)).map(m => `${t}/${m}`)).filter(d => d.includes(filter));
fs.mkdirSync("docs/screenshots", { recursive: true });
const browser = await chromium.launch();
let failures = 0;
for (const d of dirs) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  await page.goto(`${base}/${d}/`);
  await page.waitForTimeout(3500);   // let the stream finish
  const text = (await page.locator("#ui").innerText().catch(() => "")).slice(0, 80).replace(/\s+/g, " ");
  const frames = await page.locator("#ui iframe").count();
  await page.screenshot({ path: `docs/screenshots/${d.replace("/", "__")}.png`, fullPage: true });
  // Mixed mode: click "Reorder beans" (in the page or inside the MCP view iframe) and prove the loop closed.
  let action = "";
  if (d.endsWith("04_mixed")) {
    const roots = [page, page.frameLocator("#ui iframe").first()];
    for (const r of roots) {
      const b = r.getByRole("button", { name: "Reorder beans" });
      if (await b.count().catch(() => 0)) {
        await b.first().click(); await page.waitForTimeout(2500);
        const all = await page.locator("body").innerText() + (await r.locator("body").innerText().catch(() => ""));
        action = /beans_kg\s*9/.test(all) ? " action=OK(beans_kg 4->9)" : " action=NOCHANGE";
        if (action.includes("NOCHANGE")) failures++;
        await page.screenshot({ path: `docs/screenshots/${d.replace("/", "__")}__after_action.png`, fullPage: true });
        break;
      }
    }
  }
  const ok = errors.length === 0 && (text.length > 0 || frames > 0);
  if (!ok) failures++;
  console.log(`${ok ? "OK  " : "FAIL"} ${d.padEnd(28)} iframes=${frames}${action} text="${text.slice(0, 50)}" ${errors.length ? "errors=" + JSON.stringify(errors) : ""}`);
  await page.close();
}
await browser.close();
process.exit(failures ? 1 : 0);
