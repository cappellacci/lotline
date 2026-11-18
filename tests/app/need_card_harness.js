// Runs the built app page's scripts under node with a stub DOM, loads one state file, and prints the fee
// view the page picks and the need card's HTML. Used by tests/app/test_need_card.py.
const fs = require("fs"), vm = require("vm");
const [dir, st] = process.argv.slice(2);
const html = fs.readFileSync(dir + "/index.html", "utf8");
const data = html.match(/<script id="lotline-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
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
const out = vm.runInContext(`(() => { const b = LOADED["${st}"]; SECTIONS.results(b);
  return JSON.stringify({ fee: UI.fee, html: needHtml(b, results(b)) }); })()`, ctx);
process.stdout.write(out);
