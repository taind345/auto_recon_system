/* AUTO_RECON v2 frontend — vanilla, progressive render, debounced filter. */
(()=>{"use strict";
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const S={job:null,cat:"endpoints",lang:localStorage.getItem("ar_lang")||"vi",
  theme:localStorage.getItem("ar_theme")||"dark",filter:"all",q:"",sel:null,
  eps:[],cache:{},progTimer:0,resTimer:0,notes:{},target:""};
const T=k=>(window.I18N[S.lang]&&window.I18N[S.lang][k])||k;
const esc=s=>String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const debounce=(f,ms)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>f(...a),ms);};};
function stopTimers(){clearInterval(S.progTimer);clearInterval(S.resTimer);S.progTimer=0;S.resTimer=0;}
const VIA_LABEL={"katana":"M3_CRAWL_ANON","katana-auth":"M4_CRAWL_AUTH","ffuf":"M5_FFUF_DIR",
  "passive":"M2_PASSIVE","input":"MANUAL_INPUT","form":"FORM_ACTION","script":"SCRIPT_SRC"};
function viaName(v){if(!v)return"—";if(VIA_LABEL[v])return VIA_LABEL[v];
  if(v.startsWith("href:"))return"M3_LINK "+v.slice(5);if(v.startsWith("script"))return"SCRIPT_SRC";return v;}
function sampleVal(e,name){try{const u=new URL(e.url);
  return u.searchParams.get(name)??"";}catch{return"";}}
function burpReq(e,session){try{const u=new URL(e.url);const lines=[
  `${e.method||"GET"} ${u.pathname+u.search} HTTP/1.1`,`Host: ${u.host}`,
  "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
  "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"];
  if(session)lines.push(`Cookie: ${session}`);lines.push("Connection: close");
  return lines.join("\n");}catch{return"";}}

/* theme + lang */
function applyTheme(){document.documentElement.dataset.theme=S.theme;localStorage.setItem("ar_theme",S.theme);
  $("#btnTheme").textContent=S.theme==="dark"?"☾":"☀";}
function applyLang(){const d=window.I18N[S.lang]||{};
  $$("[data-i18n]").forEach(el=>{const k=el.dataset.i18n;if(d[k])el.textContent=d[k];});
  $$("[data-i18n-ph]").forEach(el=>{const k=el.dataset.i18nPh;if(d[k])el.placeholder=d[k];});
  $("#btnLang").textContent=S.lang==="vi"?"EN":"VI";localStorage.setItem("ar_lang",S.lang);
  document.documentElement.lang=S.lang;}

/* api */
async function api(path,opt){const r=await fetch(path,opt);return r.json();}
async function health(){try{const h=await api("/api/health");$("#health").textContent=
  `req:${h.has_requests?"✓":"✗"} bs4:${h.has_bs4?"✓":"✗"} kat:${h.katana?"✓":"✗"} ffuf:${h.ffuf?"✓":"✗"} nmap:${h.nmap?"✓":"✗"}`;}catch{/*offline*/}}

/* scan */
function authPayload(){const m=$("#authMode").value;
  if(m==="cookie"){window._lastCookie=$("#authCookie").value.trim();
    return{mode:"cookie",cookie:window._lastCookie,user:$("#authUser").value.trim()};}
  if(m==="bearer"){window._lastCookie="";
    return{mode:"bearer",bearer:$("#authBearer").value.trim(),user:$("#authUser").value.trim()};}
  if(m==="login")return{mode:"login",login_url:$("#loginUrl").value.trim(),
    user:$("#authUser").value.trim(),pass:$("#authPass").value,
    session_cookie:window._sessCookie||""};
  window._lastCookie="";return{mode:"off"};}
function updateAuthFields(){const m=$("#authMode").value;
  $("#loginUrl").style.display=m==="login"?"":"none";
  $("#authUser").style.display=(m==="cookie"||m==="login")?"":"none";
  $("#authPass").style.display=m==="login"?"":"none";
  $("#authCookie").style.display=m==="cookie"?"":"none";
  $("#authBearer").style.display=m==="bearer"?"":"none";}
async function scan(){const t=$("#target").value.trim();if(!t)return;
  stopTimers();$("#btnScan").disabled=true;S.eps=[];S.cache={};S.sel=null;S.target=t;
  $("#ftTarget").textContent=t;$("#ftStatus").textContent="SCANNING";
  try{
    const r=await api("/api/scan",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({target:t,profile:$("#profile").value,auth:authPayload(),proxy:$("#proxy").value.trim()})});
    if(!r.job_id)throw new Error(r.error||"scan failed");
    S.job=r.job_id;pollProg();pollRes();S.progTimer=setInterval(pollProg,1000);
    S.resTimer=setInterval(pollRes,2000);
  }catch(e){logLine("scan error: "+e.message);$("#btnScan").disabled=false;$("#ftStatus").textContent="ONLINE";}}
async function cancel(){if(!S.job)return;await api("/api/cancel",{method:"POST",
  headers:{"Content-Type":"application/json"},body:JSON.stringify({job_id:S.job})});
  logLine(T("cancelled"));}
async function checkSession(){const t=$("#target").value.trim();
  try{
    const r=await api("/api/check-session",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({target:t,auth:{...authPayload(),login_url:$("#loginUrl").value.trim()},proxy:$("#proxy").value.trim(),job:S.job})});
    if(r.session_cookie){window._sessCookie=r.session_cookie;window._lastCookie=r.session_cookie;}
    const lbl=r.logged_in?`[#] AUTH: ${authPayload().user||"session"}`:"[#] AUTH: off";
    $("#authUserLbl").textContent=lbl;
    $("#sessMsg").textContent=(r.logged_in?"[+] VALID ":"[−] ")+(r.msg||"");
    $("#sessMsg").style.color=r.logged_in?"var(--acc)":"var(--amber)";
  }catch(e){$("#sessMsg").textContent="check error: "+e.message;}}

/* polling */
async function pollProg(){if(!S.job)return;
  try{
    const p=await api(`/api/progress?job=${S.job}`);
    if(p.error){stopTimers();$("#btnScan").disabled=false;return;}
    renderMods(p);renderLog(p.logs||[]);renderMeta(p);
    if(p.status==="done"||p.status==="cancelled"){stopTimers();
      $("#btnScan").disabled=false;$("#ftStatus").textContent="ONLINE";logLine(T("scan_done"));pollRes();}
  }catch(e){/* transient: keep polling */}}
async function pollRes(){if(!S.job)return;
  try{
    const c=await api(`/api/result?job=${S.job}&cat=${S.cat}`);
    S.cache[S.cat]=c;
    if(S.cat==="endpoints"&&Array.isArray(c.items))S.eps=c.items;
    if(S.cat==="notes"&&c.items&&typeof c.items==="object")S.notes=c.items;
    renderCat();
  }catch(e){/* transient */}}
function logLine(m){const el=$("#log");const d=document.createElement("div");d.className="ln";
  d.innerHTML=`<span class="p">root@recon:~#</span> ${esc(m)}`;el.appendChild(d);el.scrollTop=el.scrollHeight;}
function renderMeta(p){try{
  const host=new URL(S.target||p.target||"").hostname||"—";
  $("#scopeHost").textContent=host;
  const hs=p.counts&&p.counts.homeStatus!==undefined?p.counts.homeStatus:(S.cache.overview?.items?.home?.status);
  const homeEl=$("#scopeHome");
  if(hs!==undefined&&homeEl)homeEl.textContent=`HOME: ${hs}`;
  const hc=$("#homeChip");if(hc&&hs!==undefined){hc.textContent=`[${hs} OK]`;hc.className="chip";}
  const px=$("#proxy").value.trim();$("#ftProxy").textContent=`BURP: ${px||"off"}`;
  }catch(e){/* idle */}}

/* pipeline */
const MODMETA=[["ports","M1","PORTS"],["passive","M2","PASSIVE"],["crawl_anon","M3","CRAWL_ANON"],
  ["crawl_auth","M4","CRAWL_AUTH"],["brute","M5","FFUF_DIR"],["params","M6","PARAMS"],
  ["js","M7","JS_MINER"],["tech","M8","TECH_STACK"]];
function renderMods(p){const box=$("#mods");const stName=s=>T(s)||s;
  box.innerHTML=MODMETA.map(([k,tag,label])=>{const m=(p.modules||{})[k]||{};
    const st=m.state||"queued";const run=st==="running"?" run":"";
    const dot=st==="running"?"● ":st==="done"?"✓ ":st==="fail"?"✗ ":"○ ";
    return `<div class="mod${run}"><div class="t"><span>${tag}:${label}</span><span class="st">${dot}${esc(stName(st))}</span></div>
    <div class="v">${esc(String(m.count??"—"))}</div><div class="s">${esc(m.msg||"")}</div></div>`;}).join("")+
    `<div id="modsum">[RUNNING: ${Object.values(p.modules||{}).filter(m=>m.state==="running").length}/8] · total ${p.pct||0}% · ${esc(p.status||"")} · ${esc(p.target||"")}</div>`;
  const counts=p.counts||{};
  setCnt("cnt-endpoints",counts.endpoints);setCnt("cnt-params",counts.params);setCnt("cnt-js",counts.js);
  setCnt("cnt-ports",counts.ports);setCnt("cnt-subs",counts.subdomains);}
function setCnt(id,v){const e=document.getElementById(id);if(e&&v!==undefined)e.textContent=`[${v}]`;}
function renderLog(lines){const el=$("#log");if(!lines.length)return;
  el.innerHTML=lines.slice(-50).map(l=>`<div class="ln">${esc(l)}</div>`).join("")+`<span class="cursor-blink"></span>`;
  el.scrollTop=el.scrollHeight;}

/* categories */
function renderCat(){const c=S.cat;
  $$(".nav-it").forEach(b=>b.classList.toggle("on",b.dataset.cat===c));
  if(c==="endpoints")return renderTree();
  const d=S.cache[c];const box=$("#insp");
  if(!d){box.innerHTML=`<div class="skel">${esc(T("empty"))}</div>`;return;}
  if(c==="overview")return renderOverview(d.items||{},box);
  if(c==="subdomains")return box.innerHTML=`<div class="box"><div class="box-h"><span>SUBDOMAINS</span><span class="sp"></span><span class="chip">[${(d.items||[]).length}]</span></div><pre>${esc((d.items||[]).join("\n")||"—")}</pre></div>`;
  if(c==="ports")return box.innerHTML=`<div class="box"><div class="box-h"><span>OPEN PORTS</span><span class="sp"></span><span class="chip">[${(d.items||[]).length}]</span></div><table class="tbl"><tr><th>port</th><th>svc</th></tr>${(d.items||[]).map(p=>`<tr><td>${esc(p.port)}</td><td>${esc(p.svc)}</td></tr>`).join("")}</table></div>`;
  if(c==="params")return renderParamsTable(d.items||[],box,null);
  if(c==="js"){const it=d.items||[];
    box.innerHTML=`<div class="box"><div class="box-h"><span>JS → API EDGES</span><span class="sp"></span><span class="chip">[${(d.apis||[]).length}]</span></div><pre class="code">${esc((d.apis||[]).join("\n")||"—")}</pre></div>
    <div class="box"><div class="box-h"><span>SECRETS (MASKED)</span><span class="sp"></span><span class="chip am">[${(d.secrets||[]).length}]</span></div><pre>${esc((d.secrets||[]).map(s=>`${s.kind} @ ${s.file} :: ${s.masked}`).join("\n")||"—")}</pre></div>`;return;}
  if(c==="tech"){const t=d.items||{};
    box.innerHTML=`<div class="box"><div class="box-h"><span>STACK FINGERPRINT</span></div><div class="kv">${esc((t.tech||[]).join(" · ")||"unknown")} · HSTS:${t.hsts?"✓":"✗"} · cookies:${esc(JSON.stringify(t.cookie_flags||{}))}</div></div>
    <div class="box"><div class="box-h"><span>KNOWN FILES</span><span class="sp"></span><span class="chip">[${(t.files||[]).length}]</span></div><table class="tbl"><tr><th>file</th><th>status</th><th>len</th></tr>${(t.files||[]).map(f=>`<tr><td>${esc(f.path)}</td><td>${f.status}</td><td>${f.len}</td></tr>`).join("")}</table></div>
    <div class="box"><div class="box-h"><span>OPTIONS ALLOW</span></div><pre>${esc(JSON.stringify(t.methods||{},null,2))}</pre></div>`;return;}
  if(c==="auth"){const a=d.items||{};
    box.innerHTML=`<div class="box phos"><div class="box-h"><span>AUTH MATRIX — ${esc(a.mode||"off")} ${esc(a.user||"")}</span><span class="sp"></span><span class="chip am">AUTH-ONLY [${(a.auth_only||[]).length}]</span></div><pre>${esc((a.auth_only||[]).join("\n")||"—")}</pre></div>`;return;}
  if(c==="notes"){box.innerHTML=`<div class="box"><div class="box-h"><span>${esc(T("report_md"))}</span></div>
    <div class="actions"><button class="ghost" id="bMd">Markdown</button><button class="ghost" id="bCsv">CSV</button><button class="ghost" id="bJson">JSON</button></div>
    <pre id="expOut">${esc(T("detail_hint"))}</pre></div>
    <div class="box"><div class="box-h"><span>${esc(T("notes_saved"))}</span></div><pre id="notesOut">${esc(JSON.stringify(S.notes,null,2))}</pre></div>
    <div class="box"><div class="box-h"><span>${esc(T("scans_title"))}</span></div>
    <div class="actions"><select id="diffA"></select><select id="diffB"></select>
    <button class="ghost" id="bDiff">Diff A→B</button></div>
    <pre id="diffOut">…</pre></div>`;
    $("#bMd").onclick=exportMD;$("#bCsv").onclick=exportCSV;$("#bJson").onclick=exportJSON;
    $("#bDiff").onclick=runDiff;loadScans();return;}
}
function renderParamsTable(rows,box,ep){const h=ep?`PARAMS @ ${ep.url}`:`PARAMS & INPUTS`;
  box.innerHTML=`<div class="box"><div class="box-h"><span>${esc(h)}</span><span class="sp"></span><span class="chip">[${rows.length}]</span></div>
  <table class="tbl"><tr><th>parameter</th><th>type</th><th>sample</th><th>heuristic</th><th>action</th></tr>${rows.slice(0,300).map(r=>{
    const type=(r.via||"").startsWith("query")?"QUERY":(r.via||"").startsWith("form")?"FORM":"JS";
    const sample=r.endpoint?sampleVal({url:r.endpoint},r.name):sampleVal(ep||{url:""},r.name);
    const heu=r.redirect_candidate?'<span class="chip rd">[SINK: OPEN_REDIRECT]</span>':/id$/i.test(r.name)?'<span class="chip am">[IDOR CHECK]</span>':'<span class="chip dim">[—]</span>';
    const epU=esc(r.endpoint||(ep&&ep.url)||"");
    return `<tr><td><b>${esc(r.name)}</b></td><td class="mut">${esc(r.via||"")} [${type}]</td><td>${esc(String(sample||"—"))}</td><td>${heu}</td><td>${epU?`<button class="ghost" data-cp="${epU}::${esc(r.name)}">[COPY]</button>`:""}</td></tr>`;}).join("")||'<tr><td colspan="5" class="mut">—</td></tr>'}</table></div>`;
  box.querySelectorAll("[data-cp]").forEach(b=>b.onclick=()=>{navigator.clipboard.writeText(b.dataset.cp);b.textContent="[OK]";});}
function renderOverview(o,box){box.innerHTML=`<div class="box"><div class="box-h"><span>SYSTEM MAP — ${esc(o.target||"")}</span></div>
  <div class="kv">endpoints:<b>${o.counts?.endpoints??0}</b> · auth-only:<b>${o.counts?.auth_only??0}</b> · params:<b>${o.counts?.params??0}</b> · home:<b>${o.home?.status??""}</b></div></div>
  <div class="box"><div class="box-h"><span>TOP BY RISK_SCORE</span></div><table class="tbl"><tr><th>score</th><th>url</th><th>tags</th></tr>${(o.top||[]).map(e=>`<tr><td><b>${e.score}</b></td><td><code>${esc(e.url)}</code></td><td>${esc((e.tags||[]).join(" "))}</td></tr>`).join("")}</table></div>
  <div class="box"><div class="box-h"><span>SITE GRAPH (PAGE→JS→API)</span></div><pre class="code">${esc((o.graph||[]).map(g=>`${g.from}  --${g.kind}-->  ${g.to}`).join("\n")||"—")}</pre></div>`;}

/* tree */
function shortUrl(u){try{const x=new URL(u);return (x.pathname+x.search)||"/";}catch{return u;}}
function grouped(){const q=S.q.toLowerCase();
  let list=S.eps.filter(e=>!q||e.url.toLowerCase().includes(q)||(e.params||[]).some(p=>p.name.toLowerCase().includes(q))||(e.tags||[]).join(" ").includes(q));
  if(S.filter==="auth")list=list.filter(e=>(e.tags||[]).includes("auth-only"));
  if(S.filter==="params")list=list.filter(e=>(e.params||[]).length);
  if(S.filter==="redir")list=list.filter(e=>(e.tags||[]).includes("client-redirect")||(e.params||[]).some(p=>p.redirect_candidate));
  list=list.slice().sort((a,b)=>b.score-a.score||a.url.localeCompare(b.url)).slice(0,300);
  const g={};for(const e of list){const seg="/"+(e.path||"/").split("/").filter(Boolean)[0]||"/";
    (g[seg]=g[seg]||[]).push(e);}return g;}
function renderTree(){const box=$("#tree");const g=grouped();
  const names=Object.keys(g).sort();if(!names.length){box.innerHTML=`<div class="skel">${esc(T("empty"))}</div>`;$("#treeSel").textContent="SELECTED: 0/0";return;}
  box.innerHTML=names.map(seg=>{const items=g[seg];
    const maxS=Math.max(...items.map(e=>e.score||0));
    const zone=items.every(e=>(e.tags||[]).includes("auth-only"))?'<span class="chip am">AUTH ZONE</span>':"";
    const forb=items.some(e=>[401,403].includes(e.status_anon))?'<span class="chip rd">403 ZONE</span>':"";
    return `<details class="grp" open><summary><span>${esc(seg)}</span><span class="mut">· ${items.length}</span>${zone}${forb}<span class="fscore">[SCORE: ${maxS}]</span></summary><div class="kids">${
    items.map((e,i)=>{const m=(e.method||"GET").toUpperCase();const mc=m==="POST"?"mPOST":"mGET";
      const st=e.status_auth||e.status_anon||"··";
      return `<div class="ep${S.sel===e.url?" sel":""}" data-u="${esc(e.url)}"><span class="conn">${i===items.length-1?"└──":"├──"}</span><span class="m ${mc}">[${m}]</span><span class="u">${esc(shortUrl(e.url))}${(e.tags||[]).map(t=>`<span class="badge ${esc(t)}">${esc(t)}</span>`).join("")}</span><span class="st">${st}</span></div>`;}).join("")}</div></details>`;}).join("");
  const total=Object.values(g).reduce((a,l)=>a+l.length,0);
  $("#treeSel").textContent=`SELECTED: ${S.sel?1:0}/${total}`;
  box.querySelectorAll(".ep").forEach(el=>el.onclick=()=>{S.sel=el.dataset.u;
    box.querySelectorAll(".ep").forEach(x=>x.classList.remove("sel"));el.classList.add("sel");showDetail();});}

/* detail */
function cur(){return S.eps.find(e=>e.url===S.sel);}
function showDetail(sub){const e=cur();const box=$("#insp");if(!e){box.innerHTML=`<p class="mut">${esc(T("detail_hint"))}</p>`;return;}
  $("#treeSel").textContent=`SELECTED: 1/${S.eps.length}`;
  $("#inspMeta").textContent=`// ${viaName(e.via)}`;
  const m=(e.method||"GET").toUpperCase();
  const stTxt=e.status_auth||e.status_anon||"··";
  const sink=(e.tags||[]).includes("client-redirect")||e.has_location_js;
  const tabs=["info","js","hrefs","forms","diff","raw","burp"];
  box.innerHTML=`<div class="insp-top"><span class="mchip ${m}">${m}</span><h2>${esc(shortUrl(e.url))}</h2></div>
  <div class="chipsrow"><span class="chip">[${m} ${stTxt}]</span><span class="chip rd">[SCORE: ${e.score}]</span>${sink?'<span class="chip cy">[DOM-INVOKED SINK]</span>':""}${(e.tags||[]).includes("auth-only")?'<span class="chip am">[AUTH-ONLY]</span>':""}</div>
  <div class="actions"><button class="ghost" id="bRep">[# REPEATER]</button><button class="ghost" id="bInt">[# INTRUDER]</button><button class="ghost" id="bChr">[# CHROMIUM]</button><span class="via">DISCOVERED VIA: ${esc(viaName(e.via))}</span></div>
  <div class="tabs">${tabs.map(t=>`<button data-t="${t}" class="${(sub||"info")===t?"on":""}">${esc(T("tab_"+t)||t)}</button>`).join("")}</div><div id="pane"></div>
  <div class="box phos rec"><div class="box-h"><span>✓ ${esc(T("rec_title"))}</span><span class="sp"></span><span class="chip fill">HIGH CONFIDENCE</span></div><ul id="rec"></ul></div>
  <div class="box"><div class="box-h"><span>NOTE</span></div><textarea id="noteBox" rows="2" style="width:100%;background:var(--bg0);border:1px solid var(--line2);color:var(--txt);font:inherit" placeholder="${esc(T("notes_ph"))}">${esc(S.notes[e.url]||"")}</textarea>
  <div class="actions"><button class="ghost" id="saveNote">Save note</button></div></div>`;
  box.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>showDetail(b.dataset.t));
  const req=burpReq(e,(S.cache.auth?.items?.mode!=="off")?(window._lastCookie||""):"");
  $("#bRep").onclick=()=>showDetail("burp"); // jump straight into the repeater
  $("#bInt").onclick=()=>navigator.clipboard.writeText(req||e.url);
  $("#bChr").onclick=()=>window.open(e.url,"_blank");
  $("#saveNote").onclick=async()=>{S.notes[e.url]=$("#noteBox").value;
    if(S.job)await api("/api/note",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({job:S.job,url:e.url,text:S.notes[e.url]})});};
  $("#rec").innerHTML=recFor(e);pane(e,sub||"info");}
function recFor(e){const out=[];
  if((e.params||[]).some(p=>p.redirect_candidate))out.push(`<li><span class="mk">[ ! ]</span><b>Client-side Open Redirect / DOM XSS:</b> param <code>${esc((e.params.find(p=>p.redirect_candidate)||{}).name||"")}</code> flows into sink <code>window.location</code> — test <code>?x=//attacker.com</code>, <code>javascript:alert(domain)</code>.</li>`);
  if((e.tags||[]).includes("auth-only"))out.push(`<li><span class="mk">[ # ]</span><b>IDOR Checklist:</b> anon ${e.status_anon} vs auth ${e.status_auth} (+${(e.len_auth||0)-(e.len_anon||0)}b) — decrement id params, test user→admin.</li>`);
  if(e.has_location_js)out.push(`<li><span class="mk">[ + ]</span><b>DOM sink:</b> <code>window.location</code> reachable — trace JS, test redirect/XSS.</li>`);
  if((e.tags||[]).includes("api"))out.push(`<li><span class="mk">[ + ]</span><b>API:</b> OPTIONS verb check, mass-assign probe (manual).</li>`);
  if(!(out.length))out.push(`<li><span class="mk">[ = ]</span>enum baseline — check hrefs/forms, then move on.</li>`);
  return out.join("");}
async function pane(e,t){const p=$("#pane");
  if(t==="info")p.innerHTML=`<div class="kv">anon: <b>${e.status_anon}</b> (${e.len_anon}b) · auth: <b>${e.status_auth}</b> (${e.len_auth}b)${e.location?` · Location: <code>${esc(e.location)}</code>`:""} · final: ${esc(e.final_url||"")}</div>
    <div class="kv">params: ${(e.params||[]).map(x=>`<code>${esc(x.name)}</code>(${esc(x.via)}${x.redirect_candidate?" ⚠️":""})`).join(", ")||"—"}</div>`;
  else if(t==="js"){const files=e.js_files||[];
    if(!files.length){p.innerHTML=`<p class="mut">[—] no JS files captured on this page (redirect / no &lt;script&gt; tags / JS-rendered?). Check the Raw tab.</p>`;return;}
    p.innerHTML=files.map(j=>`<div><button class="ghost" data-js="${esc(j)}">[VIEW]</button> <code>${esc(j)}</code></div>`).join("")+`<pre class="code" id="jsout">// [+] press [VIEW] to load source…</pre>`;
    p.querySelectorAll("[data-js]").forEach(b=>b.onclick=()=>loadJS(b.dataset.js));}
  else if(t==="hrefs")p.innerHTML=`<pre>${esc((e.hrefs||[]).join("\n")||"—")}</pre>`;
  else if(t==="forms")renderParamsTable(e.params||[],p,e);
  else if(t==="diff"){const d=(e.len_auth||0)-(e.len_anon||0);
    p.innerHTML=`<div class="box"><div class="box-h"><span>RESPONSE DIFF COMPARISON</span><span class="sp"></span><span class="chip">${d>=0?"+":""}${d} BYTES DELTA</span></div>
    <div class="diff2"><div class="diffcol"><div class="dh"><span>ANONYMOUS</span><span>HTTP ${e.status_anon}</span></div><div class="dl">Length: ${e.len_anon}b</div>${e.location?`<div class="dl">Location: ${esc(e.location)}</div>`:""}<div class="dl">// ${e.status_anon===200?"body readable":"no body (redirect/denied)"}</div></div>
    <div class="diffcol auth"><div class="dh"><span>AUTH</span><span>HTTP ${e.status_auth}</span></div><div class="dl">Length: ${e.len_auth}b</div><div class="dl">// ${e.status_auth===200?"authenticated body":"same as anon"}</div></div></div></div>`;}
  else if(t==="raw"){p.innerHTML="<pre>loading…</pre>";const r=await api("/api/fetch?url="+encodeURIComponent(e.url));
    p.innerHTML=`<div class="mut">final: ${esc(r.final||"")} · ${r.status}</div><pre class="code">${esc((r.body||"").slice(0,20000))}</pre>`;}
  else if(t==="burp"){const req=burpReq(e,window._lastCookie||"");
    p.innerHTML=`<div class="box phos"><div class="box-h"><span>REPEATER — EDIT + SEND</span><span class="sp"></span>
    <label class="mut"><input type="checkbox" id="useSess" checked> ${esc(T("attach_session"))}</label>
    <button class="ghost" id="sendReq">[${esc(T("send"))}]</button></div>
    <textarea id="rawReq" rows="9" style="width:100%">${esc(req||"")}</textarea>
    <div class="mut" id="repMeta">// edit raw request above, then SEND. scope = this job's target.</div>
    <pre class="code" id="repRes">…</pre></div>`;
    $("#sendReq").onclick=()=>sendRaw(e);}}
async function sendRaw(e){const btn=$("#sendReq"),out=$("#repRes"),meta=$("#repMeta");
  if(!S.job){meta.textContent="// no job";return;}
  btn.disabled=true;meta.textContent="// sending…";
  try{
    const r=await api("/api/send",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({job:S.job,raw:$("#rawReq").value,use_session:$("#useSess").checked})});
    if(r.error){meta.textContent="// ERR: "+r.error;out.textContent="";return;}
    meta.textContent=`// HTTP ${r.status} · ${r.len}b · ${r.ms}ms${r.location?` · Location: ${r.location}`:""}`;
    out.textContent=`HTTP ${r.status} (${r.ms}ms)\n${Object.entries(r.headers||{}).map(([k,v])=>`${k}: ${v}`).join("\n")}\n\n${r.body||""}`;
  }catch(err){meta.textContent="// ERR: "+err.message;}
  btn.disabled=false;}
async function loadJS(u){const out=$("#jsout");if(out)out.textContent=`// loading ${u} …`;
  try{
    const r=await api("/api/fetch?url="+encodeURIComponent(u));
    if(out)out.textContent=`// ${u} [${r.status}]\n\n`+((r.body||"").slice(0,20000)||"// [—] empty body");
  }catch(e){if(out)out.textContent=`// ERR loading ${u}: ${e.message}`;}}

/* export */
function dl(name,text,type){const b=new Blob([text],{type});const a=document.createElement("a");
  a.href=URL.createObjectURL(b);a.download=name;a.click();}
async function loadScans(){try{
    let host="";try{host=new URL($("#target").value.trim()).hostname;}catch(e){/* list all */}
    const r=await api("/api/scans"+(host?"?host="+encodeURIComponent(host):""));
    const opts=(r.items||[]).map(s=>`<option value="${esc(s.path)}">${esc(s.file)}</option>`).join("");
    const a=$("#diffA"),b=$("#diffB");if(!a||!b)return;
    a.innerHTML=opts;b.innerHTML=opts;if(a.options.length>1)b.selectedIndex=0,a.selectedIndex=1;
  }catch(e){/* ignore */}}
async function runDiff(){const a=$("#diffA").value,b=$("#diffB").value;if(!a||!b)return;
  const r=await api(`/api/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
  $("#diffOut").textContent=`A:${r.count_a} B:${r.count_b}\nNEW:\n${(r.new||[]).join("\n")}\nLOST:\n${(r.lost||[]).join("\n")}`;}
function exportJSON(){dl("recon.json",JSON.stringify({job:S.job,endpoints:S.eps},null,2),"application/json");}
function exportCSV(){const rows=["url,method,status_anon,status_auth,score,tags,params"];
  for(const e of S.eps)rows.push([e.url,e.method||"GET",e.status_anon,e.status_auth,e.score,(e.tags||[]).join("|"),(e.params||[]).map(p=>p.name).join("|")].map(v=>`"${String(v).replace(/"/g,'""')}"`).join(","));
  dl("recon.csv",rows.join("\n"),"text/csv");}
function exportMD(){const lines=[`# AUTO_RECON report (${S.job})`,"","enum-only, no auto-exploit","","- [ ] reviewed"];
  for(const e of S.eps.slice(0,200))lines.push(`\n## ${e.url}\n- status anon=${e.status_anon} auth=${e.status_auth} score=${e.score}\n- tags: ${(e.tags||[]).join(", ")}\n- params: ${(e.params||[]).map(p=>p.name).join(", ")||"—"}\n- note: ${S.notes[e.url]||""}\n- [ ] checked`);
  const md=lines.join("\n");const o=$("#expOut");if(o)o.textContent=md;dl("recon.md",md,"text/markdown");}
function quickBurp(){const e=cur();const txt=e?burpReq(e,window._lastCookie||""):S.eps.map(x=>x.url).join("\n");
  if(txt)navigator.clipboard.writeText(txt);}

/* wire */
function wire(){
  applyTheme();applyLang();health();
  $("#btnTheme").onclick=()=>{S.theme=S.theme==="dark"?"light":"dark";applyTheme();};
  $("#btnLang").onclick=()=>{S.lang=S.lang==="vi"?"en":"vi";applyLang();renderCat();};
  $("#btnScan").onclick=scan;$("#btnStop").onclick=cancel;
  $("#btnCheck").onclick=checkSession;$("#btnExport").onclick=exportJSON;
  $("#btnBurpCopy").onclick=quickBurp;
  $$(".nav-it").forEach(b=>b.onclick=()=>{S.cat=b.dataset.cat;pollRes();});
  $$("#filters button").forEach(b=>b.onclick=()=>{S.filter=b.dataset.f;
    $$("#filters button").forEach(x=>x.classList.remove("on"));b.classList.add("on");renderTree();});
  $("#q").addEventListener("input",debounce(ev=>{S.q=ev.target.value;renderTree();},180));
  $("#q").addEventListener("keydown",ev=>{if(ev.key==="Escape"){ev.target.value="";S.q="";renderTree();}});
  $("#authMode").onchange=updateAuthFields;updateAuthFields();
  document.addEventListener("keydown",ev=>{if(ev.key==="Enter"&&document.activeElement===$("#target"))scan();});
}
document.addEventListener("DOMContentLoaded",wire);
})();
