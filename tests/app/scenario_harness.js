// Runs the built app page's scripts under node with a stub DOM (as need_card_harness.js does), loads one state
// file, and prints what the page draws per scenario: the model list, the Results section's HTML, the evidence
// card for one scenario and the every-state chart. Used by tests/app/test_scenario_toy.py.
const fs = require("fs"), vm = require("vm");
const [dir, st, scenario] = process.argv.slice(2);
const html = fs.readFileSync(dir + "/index.html", "utf8");
const between = (open, from = 0) => {
  const i = html.indexOf(open, from);
  if (i < 0) return null;
  const j = html.indexOf("</" + "script>", i + open.length);
  return { body: html.slice(i + open.length, j), next: j };
};
const data = between('<script id="lotline-data" type="application/json">').body;
const scripts = [];
for (let at = 0, b; (b = between("<script>", at)); at = b.next) scripts.push(b.body);
const el = () => new Proxy({ style: {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {} } }, {
  get: (t, k) => (k in t ? t[k] : typeof k === "string" && /^(set|add|remove|append|query|focus|scroll|get|insert|replace)/.test(k)
    ? () => (k.startsWith("query") ? (k.endsWith("All") ? [] : null) : el()) : undefined),
  set: (t, k, v) => ((t[k] = v), true) });
const document = { getElementById: (id) => (id === "lotline-data" ? { textContent: data } : el()), querySelector: () => null,
  querySelectorAll: () => [], createElement: el, addEventListener() {}, head: el(), body: el(), documentElement: el() };
const ctx = { document, console, CSS: { escape: (s) => s }, location: { hash: "" }, addEventListener() {},
  history: { replaceState() {} }, matchMedia: () => ({ matches: false, addEventListener() {} }), setTimeout, Promise };
ctx.window = ctx; ctx.globalThis = ctx; vm.createContext(ctx);
for (const s of scripts) { try { vm.runInContext(s, ctx); } catch (e) { /* page start-up touches the DOM */ } }
vm.runInContext(fs.readFileSync(`${dir}/states/${st.toLowerCase()}.js`, "utf8"), ctx);
const out = vm.runInContext(`(() => { const b = LOADED["${st}"]; const results_html = SECTIONS.results(b);
  return JSON.stringify({ hero: HERO, scenarios: DATA.scenarios, results: results_html,
    evidence: evidenceHtml(b, "${scenario}", results(b)), allstates: allStatesSvg() }); })()`, ctx);
process.stdout.write(out);
