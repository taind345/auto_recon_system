// TC-FRONTEND (runtime): drive scan→progress→tree with canned API data.
// Run: node tests/frontend_flow.js   (exit 0 = pass)
const fs = require("fs");
const path = require("path");
const JSDIR = path.join(__dirname, "..", "static", "js");
const reg = {};
function mkEl(sel) {
  if (reg[sel]) return reg[sel];
  const el = { _sel: sel, textContent: "", innerHTML: "",
    value: "http://127.0.0.1:8899", style: {}, dataset: {},
    disabled: false, selectedIndex: 0, options: [],
    classList: { toggle() {}, add() {}, remove() {} },
    addEventListener() {}, appendChild() {},
    querySelectorAll() { return []; }, querySelector() { return mkEl(sel + ">q"); } };
  return (reg[sel] = el);
}
const EP = { url: "http://127.0.0.1:8899/my-account", path: "/my-account",
  status_anon: 302, status_auth: 200, len_anon: 24, len_auth: 4581, via: "katana",
  tags: ["auth-only", "interesting"], params: [{ name: "id", via: "query", redirect_candidate: false }],
  js_files: [], hrefs: ["/login"], forms: [], headers: {}, has_location_js: false,
  sink_inline: false, location: "/login", score: 10, final_url: "http://127.0.0.1:8899/my-account" };
const MODS = {};
for (const m of ["ports", "passive", "crawl_anon", "crawl_auth", "brute", "params", "js", "tech"])
  MODS[m] = { state: "done", pct: 100, msg: "ok", count: 1 };
let dcCb = null;
global.document = { documentElement: { dataset: {}, lang: "" },
  querySelector(s) { return mkEl(s); },
  getElementById(id) { return mkEl("#" + id); },
  querySelectorAll() { return []; },
  createElement() { return mkEl("dyn" + Math.random()); },
  addEventListener(ev, cb) { if (ev === "DOMContentLoaded") dcCb = cb; } };
global.window = {};
global.localStorage = { _s: {}, getItem(k) { return this._s[k] || null; }, setItem(k, v) { this._s[k] = v; } };
global.fetch = async (u) => ({ json: async () => {
  if (u === "/api/health") return { ok: true };
  if (String(u).startsWith("/api/scan")) return { job_id: "testjob" };
  if (String(u).startsWith("/api/progress")) return { status: "done", pct: 100, target: "t",
    modules: MODS, counts: { endpoints: 1, auth_only: 1, params: 1, js: 0, ports: 1, subdomains: 0 }, logs: ["[x] done"] };
  if (String(u).includes("cat=endpoints")) return { items: [EP] };
  return { items: [] };
} });
global.navigator = { clipboard: { writeText() {} } };
global.Blob = class {};
global.URL = function U() {};
global.URL.createObjectURL = () => "";
eval(fs.readFileSync(path.join(JSDIR, "i18n.js"), "utf8"));
eval(fs.readFileSync(path.join(JSDIR, "app.js"), "utf8"));
(async () => {
  dcCb();
  document.querySelector("#target").value = "http://127.0.0.1:8899";
  await document.querySelector("#btnScan").onclick();
  await new Promise((r) => setTimeout(r, 50));
  const mods = reg["#mods"].innerHTML, log = reg["#log"].innerHTML, tree = reg["#tree"].innerHTML;
  const checks = [
    ["mods-render-M1", mods.includes("M1")],
    ["mods-state", /done|XONG/i.test(mods)],
    ["log-done", /done|xong/i.test(log)],
    ["tree-endpoint", tree.includes("my-account")],
    ["tree-auth-badge", tree.includes("auth-only")],
  ];
  let fail = 0;
  for (const [n, ok] of checks) { console.log((ok ? "PASS " : "FAIL ") + n); if (!ok) fail++; }
  process.exit(fail ? 1 : 0);
})();
