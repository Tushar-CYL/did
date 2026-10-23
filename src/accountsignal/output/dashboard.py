"""Build the static dashboard: a professional single-page app (no login, opens
from file://) plus an inlined data.js so it works offline with no server.

Writes:
  out/dashboard/data.js     window.ACCOUNTSIGNAL = {...}   (public payload, no _score)
  out/dashboard/data.json   same payload (for reuse / debugging)
  out/dashboard/index.html  the page (written once; safe to overwrite each run)

News / market-intelligence is the primary content; hiring is secondary. Internal
relevance scores are stripped from the payload.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from .. import config
from ..store import io

log = logging.getLogger("accountsignal.output.dashboard")

CATEGORIES = ("hiring", "vision", "partnerships", "financial", "expansion")


def _public_payload() -> dict:
    data = io.read_json(io.normalized_path())
    companies = []
    for c in data:
        mi = c["market_intel"]
        pub_mi = {}
        for cat in CATEGORIES:
            items = [{k: it.get(k) for k in ("title", "url", "date", "source")}
                     for it in mi[cat]["items"]]
            pub_mi[cat] = {"summary": mi[cat]["summary"], "items": items}
        companies.append({
            "company": c["company"], "ats": c.get("ats"),
            "website": c.get("website"), "career_url": c.get("career_url"),
            "hiring_india": c["hiring_india"],
            "market_intel": pub_mi,
            "signals": c.get("signals", {}),
        })
    totals = {
        "companies": len(companies),
        "roles": sum(len(c["hiring_india"]) for c in companies),
        "news": sum(len(c["market_intel"][k]["items"]) for c in companies for k in CATEGORIES),
    }
    return {"generated": date.today().isoformat(), "totals": totals, "companies": companies}


def build(out_dir: Path | None = None) -> Path:
    out_dir = out_dir or config.DASHBOARD_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = _public_payload()
    (out_dir / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "data.js").write_text(
        "window.ACCOUNTSIGNAL = " + json.dumps(payload, ensure_ascii=False) + ";",
        encoding="utf-8")
    (out_dir / "index.html").write_text(_INDEX_HTML, encoding="utf-8")
    log.info("Dashboard written -> %s", out_dir / "index.html")
    return out_dir / "index.html"


_INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AccountSignal — EY India Account Intelligence</title>
<style>
  :root{
    --navy:#1a2238; --navy2:#232d4b; --ink:#1b1f2a; --muted:#5b6475;
    --line:#e5e8ee; --bg:#f4f6fa; --card:#ffffff; --accent:#ffe600; --accent2:#2e5bff;
    --good:#1f9d55; --crit:#c0392b;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:"Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif;
       background:var(--bg);color:var(--ink);font-size:15px;line-height:1.5}
  header{background:linear-gradient(120deg,var(--navy),var(--navy2));color:#fff;padding:18px 24px;
         display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:10}
  header .mark{width:12px;height:34px;background:var(--accent);border-radius:2px}
  header h1{font-size:18px;margin:0;font-weight:600;letter-spacing:.2px}
  header .sub{color:#aeb6c9;font-size:12.5px;margin-top:2px}
  header .totals{margin-left:auto;display:flex;gap:22px}
  header .totals div{text-align:right}
  header .totals b{display:block;font-size:20px;color:var(--accent)}
  header .totals span{font-size:11px;color:#aeb6c9;text-transform:uppercase;letter-spacing:.5px}
  .wrap{display:grid;grid-template-columns:320px 1fr;gap:0;min-height:calc(100vh - 71px)}
  .side{background:#fff;border-right:1px solid var(--line);overflow:auto;max-height:calc(100vh - 71px)}
  .search{padding:12px;position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line)}
  .search input{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:8px;font-size:14px}
  .clist{list-style:none;margin:0;padding:6px}
  .clist li{padding:10px 12px;border-radius:8px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:8px}
  .clist li:hover{background:#f0f3fa}
  .clist li.active{background:var(--navy);color:#fff}
  .clist li .nm{font-weight:600;font-size:14px}
  .clist li .ct{font-size:11px;color:var(--muted)}
  .clist li.active .ct{color:#cfd6e6}
  .pill{font-size:10.5px;padding:2px 7px;border-radius:999px;background:#eef1f7;color:var(--muted)}
  main{padding:22px 26px;overflow:auto;max-height:calc(100vh - 71px)}
  .chead{display:flex;align-items:baseline;gap:12px;margin-bottom:6px;flex-wrap:wrap}
  .chead h2{margin:0;font-size:22px}
  .chead a{font-size:12.5px;color:var(--accent2);text-decoration:none}
  .takeaways{background:#fffef0;border:1px solid #f1e9a8;border-left:4px solid var(--accent);
             padding:12px 16px;border-radius:8px;margin:14px 0}
  .takeaways h3{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:#8a7f1f}
  .takeaways ul{margin:0;padding-left:18px}
  .takeaways li{margin:3px 0}
  .chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
  .chip{background:#eaf0ff;color:#2e5bff;font-size:12px;padding:3px 10px;border-radius:999px;font-weight:600}
  .sectlabel{font-size:12px;text-transform:uppercase;letter-spacing:.7px;color:var(--muted);margin:22px 0 10px;font-weight:700}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
  .card h4{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:var(--navy)}
  .card .summary{font-size:13.5px;color:#2b3242;margin-bottom:10px}
  .card ul{list-style:none;margin:0;padding:0}
  .card li{font-size:12.5px;padding:5px 0;border-top:1px dashed var(--line)}
  .card li a{color:var(--ink);text-decoration:none}
  .card li a:hover{color:var(--accent2)}
  .card li .meta{color:var(--muted);font-size:11px}
  table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
  th,td{text-align:left;padding:8px 10px;font-size:12.5px;border-bottom:1px solid var(--line)}
  th{background:#f0f3fa;color:var(--navy);text-transform:uppercase;font-size:10.5px;letter-spacing:.5px}
  td.crit{color:var(--crit);font-weight:700}
  .empty{color:var(--muted);font-style:italic;padding:8px 0}
  .tag{font-size:10.5px;padding:1px 6px;border-radius:4px;background:#eef1f7;color:var(--muted)}
  @media(max-width:860px){.wrap{grid-template-columns:1fr}.side{max-height:none}}
</style>
</head>
<body>
<header>
  <div class="mark"></div>
  <div>
    <h1>AccountSignal <span style="font-weight:400;color:#aeb6c9">· EY India Account Intelligence</span></h1>
    <div class="sub" id="sub">loading…</div>
  </div>
  <div class="totals" id="totals"></div>
</header>
<div class="wrap">
  <aside class="side">
    <div class="search"><input id="q" placeholder="Search 50 accounts…" autocomplete="off"/></div>
    <ul class="clist" id="clist"></ul>
  </aside>
  <main id="main"></main>
</div>
<script src="data.js"></script>
<script>
const D = window.ACCOUNTSIGNAL || {companies:[],totals:{}};
const CATS = [["hiring","Hiring"],["vision","Vision & Strategy"],["partnerships","Partnerships"],
              ["financial","Financial"],["expansion","Expansion"]];
const $ = s => document.querySelector(s);
let active = 0;

function init(){
  $("#sub").textContent = "Generated " + (D.generated||"") + " · India hiring + global market intelligence (last month)";
  const t = D.totals||{};
  $("#totals").innerHTML =
    `<div><b>${t.companies||0}</b><span>Accounts</span></div>
     <div><b>${t.news||0}</b><span>News signals</span></div>
     <div><b>${t.roles||0}</b><span>India roles</span></div>`;
  renderList(D.companies);
  if(D.companies.length) selectCompany(0);
}
function renderList(list){
  const ul = $("#clist"); ul.innerHTML="";
  list.forEach((c)=>{
    const idx = D.companies.indexOf(c);
    const li = document.createElement("li");
    li.className = "clist-item"+(idx===active?" active":"");
    const news = CATS.reduce((n,[k])=>n+(c.market_intel[k].items.length),0);
    li.innerHTML = `<span class="nm">${esc(c.company)}</span>
      <span class="ct">${c.hiring_india.length} roles · ${news} news</span>`;
    li.onclick = ()=>selectCompany(idx);
    ul.appendChild(li);
  });
}
function selectCompany(i){
  active=i;
  document.querySelectorAll(".clist li").forEach(el=>el.classList.remove("active"));
  renderList(filtered());
  const c = D.companies[i];
  const sig = c.signals||{};
  let html = `<div class="chead"><h2>${esc(c.company)}</h2>`;
  if(c.career_url) html += `<a href="${esc(c.career_url)}" target="_blank" rel="noopener">careers ↗</a>`;
  if(c.ats) html += `<span class="tag">${esc(c.ats)}</span>`;
  html += `</div>`;

  if((sig.insight||[]).length){
    html += `<div class="takeaways"><h3>Insight — what they're hiring for</h3><ul>`+
      sig.insight.map(t=>`<li>${esc(t)}</li>`).join("")+`</ul></div>`;
  }
  if((sig.tool_gravitation||[]).length){
    html += `<div class="chips">`+sig.tool_gravitation.map(t=>`<span class="chip">${esc(t)}</span>`).join("")+`</div>`;
  }

  html += `<div class="sectlabel">Market intelligence — global, last month</div><div class="grid">`;
  for(const [k,label] of CATS){
    const f = c.market_intel[k];
    html += `<div class="card"><h4>${label}</h4>`;
    html += f.summary ? `<div class="summary">${esc(f.summary)}</div>` : `<div class="empty">No notable items.</div>`;
    html += `<ul>`+ f.items.slice(0,6).map(it=>
      `<li><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title)}</a>
        <div class="meta">${esc(it.date||"")} · ${esc(it.source||"")}</div></li>`).join("") +`</ul></div>`;
  }
  html += `</div>`;

  html += `<div class="sectlabel">India hiring — open roles, last month</div>`;
  if(c.hiring_india.length){
    html += `<table><thead><tr><th>Role</th><th>Dept</th><th>Skills/Tools</th><th>City</th>
      <th>Seniority</th><th>Posted</th><th>Aging</th><th></th></tr></thead><tbody>`;
    html += c.hiring_india.map(r=>`<tr>
      <td>${esc(r.role)}</td><td>${esc(r.department||"")}</td>
      <td>${esc((r.tools||[]).join(", "))}</td><td>${esc(r.city||"")}</td>
      <td>${esc(r.seniority||"")}</td>
      <td>${esc(r.posted_date||"")}</td>
      <td>${r.days_open!=null?`${r.days_open}d`:""}</td>
      <td>${r.source_url?`<a href="${esc(r.source_url)}" target="_blank" rel="noopener">open ↗</a>`:""}</td>
      </tr>`).join("");
    html += `</tbody></table>`;
  } else {
    html += `<div class="empty">No India openings captured in the last month.</div>`;
  }
  $("#main").innerHTML = html;
  $("#main").scrollTop = 0;
}
function filtered(){
  const q = ($("#q").value||"").toLowerCase().trim();
  return q ? D.companies.filter(c=>c.company.toLowerCase().includes(q)) : D.companies;
}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));}
$("#q").addEventListener("input",()=>renderList(filtered()));
init();
</script>
</body>
</html>
"""
