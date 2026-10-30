"use client";
import { useEffect, useMemo, useState } from "react";
import { useData, allRoles } from "@/lib/data";
import type { Data } from "@/lib/types";
import { SectionTitle } from "@/components/ui";
import Echart from "@/components/Echart";
import dynamic from "next/dynamic";
import type { Word } from "@/components/WordCloud";
// word-cloud extension references `window`, so load it client-only (no SSR prerender)
const WordCloudChart = dynamic(() => import("@/components/WordCloudChart"), {
  ssr: false,
  loading: () => <div className="text-ey-faint text-xs py-10 text-center">Rendering…</div>,
});

function CountUp({ value }: { value: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf = 0; const start = performance.now(), dur = 850;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      setN(Math.round(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{n.toLocaleString()}</>;
}

const BAR = "#ffe600";
function hbar(data: [string, number][], n = 8) {
  const d = data.slice(0, n).reverse();
  return {
    grid: { left: 140, right: 40, top: 6, bottom: 6 },
    xAxis: { type: "value", show: false },
    yAxis: {
      type: "category", data: d.map((x) => x[0]),
      axisTick: { show: false }, axisLine: { show: false },
      axisLabel: { color: "#c7c7d0", fontSize: 11.5 },
    },
    series: [{
      type: "bar", data: d.map((x) => x[1]), barWidth: 14,
      itemStyle: { color: BAR, borderRadius: 4 },
      label: { show: true, position: "right", color: "#e9e9ee", fontWeight: 800, fontSize: 11 },
    }],
  };
}

function radarOption(items: { practice: string; value: number }[]) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return {
    tooltip: {},
    radar: {
      indicator: items.map((i) => ({ name: i.practice, max })),
      radius: "66%", splitNumber: 4,
      axisName: { color: "#c7c7d0", fontSize: 10.5 },
      splitLine: { lineStyle: { color: "#2b2b38" } },
      splitArea: { areaStyle: { color: ["#15151f", "#1a1a24"] } },
      axisLine: { lineStyle: { color: "#2b2b38" } },
    },
    series: [{
      type: "radar",
      data: [{
        value: items.map((i) => i.value),
        areaStyle: { color: "rgba(255,230,0,.22)" },
        lineStyle: { color: BAR, width: 2 }, itemStyle: { color: BAR },
      }],
    }],
  };
}

const PRACTICE_COLOR: Record<string, string> = {
  "Data & AI": "#35a4e8", "SAP / ERP": "#ffe600", "Cloud & Infra": "#27acaa",
  "Cyber": "#ff6d6d", "Salesforce / CRM": "#9c82d4", "Finance tools": "#57e188",
  "Supply Chain tools": "#ff8a4a", "Automation": "#8ad1ff",
};

type DrillSel = { sector: string; slug: string; client: string; dept: string };

// Popup opened by clicking a department in the decomposition tree: every role
// in that department, either for the clicked account or across the whole book.
function DrillModal({ data, sel, onClose }: { data: Data; sel: DrillSel; onClose: () => void }) {
  const [scope, setScope] = useState<"company" | "all">("company");
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", esc);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", esc); document.body.style.overflow = ""; };
  }, [onClose]);

  const all = useMemo(() => allRoles(data), [data]);
  const inDept = useMemo(() => all.filter((r) => (r.department || "Other") === sel.dept), [all, sel.dept]);
  const rows = scope === "all" ? inDept : inDept.filter((r) => r.slug === sel.slug);
  const companies = new Set(rows.map((r) => r.slug)).size;
  const href = `/deep-dive/?company=${scope === "all" ? "all" : sel.slug}&dept=${encodeURIComponent(sel.dept)}`;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="card !p-0 w-full max-w-[1000px] max-h-[86vh] flex flex-col overflow-hidden"
           onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-[#2b2b38]">
          <div className="flex items-start gap-3">
            <div>
              <div className="sub">Department drill-down</div>
              <h3 className="text-xl font-extrabold text-ey-yellow m-0 mt-0.5">{sel.dept}</h3>
              <div className="text-[11.5px] text-gray-400 mt-0.5">
                {sel.sector} {"›"} {scope === "company" ? sel.client : "all accounts"}
              </div>
            </div>
            <button onClick={onClose} aria-label="Close"
              className="ml-auto text-gray-400 hover:text-white text-lg leading-none px-2 py-1">&times;</button>
          </div>
          <div className="flex items-center gap-2 flex-wrap mt-3">
            <div className="flex rounded-lg overflow-hidden border border-[#2b2b38]">
              {([["company", `${sel.client} (${inDept.filter((r) => r.slug === sel.slug).length})`],
                 ["all", `All companies (${inDept.length})`]] as const).map(([k, lbl]) => (
                <button key={k} onClick={() => setScope(k)}
                  className={`px-3 py-1.5 text-[12px] font-semibold transition-colors ${scope === k ? "bg-ey-yellow text-black" : "bg-transparent text-gray-300 hover:bg-white/5"}`}>
                  {lbl}
                </button>
              ))}
            </div>
            <span className="text-[12px] text-gray-400">
              {rows.length} role{rows.length === 1 ? "" : "s"}
              {scope === "all" && ` · ${companies} account${companies === 1 ? "" : "s"}`}
            </span>
            <a href={href} className="ml-auto text-[12px] font-semibold text-[#5fb0f0] hover:underline">
              Open in Deep dive {"→"}
            </a>
          </div>
        </div>
        <div className="overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0">
              <tr className="bg-ey-black text-white text-left">
                <th className="p-2.5 text-[11px]">Role</th>
                {scope === "all" && <th className="p-2.5 text-[11px]">Company</th>}
                <th className="p-2.5 text-[11px]">Skills / tools</th>
                <th className="p-2.5 text-[11px]">Location</th>
                <th className="p-2.5 text-[11px]">Seniority</th>
                <th className="p-2.5 text-[11px]">Posted</th>
                <th className="p-2.5 text-[11px]"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-[#2b2b38] hover:bg-[#23232e] align-top">
                  <td className="p-2.5 font-medium text-gray-100">{r.role_title}</td>
                  {scope === "all" && <td className="p-2.5 text-gray-300 whitespace-nowrap">{r.client}</td>}
                  <td className="p-2.5">
                    {(r.tools || []).length
                      ? <div className="flex flex-wrap gap-1">{(r.tools || []).slice(0, 5).map((t) => <span key={t} className="chip !text-[10px] bg-[#2a2a38] text-gray-200">{t}</span>)}</div>
                      : <span className="text-ey-faint">{"—"}</span>}
                  </td>
                  <td className="p-2.5 text-gray-300">{r.location || r.city || "—"}</td>
                  <td className="p-2.5 text-gray-300">{r.seniority || "—"}</td>
                  <td className="p-2.5 text-gray-400 whitespace-nowrap">{r.posted_date || "—"}</td>
                  <td className="p-2.5">{r.source_url ? <a href={r.source_url} target="_blank" rel="noopener" className="text-[#5fb0f0]">open</a> : null}</td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td className="p-3 text-ey-faint" colSpan={7}>No roles in this department.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Decomposition as three linked columns instead of a tree: every label stays
// horizontal and each column scrolls, so a fully expanded view never collides.
function DrillColumn({
  label, note, items, selected, onPick, emptyText, opens,
}: {
  label: string; note: string;
  items: { key: string; name: string; n: number }[];
  selected?: string; onPick: (key: string) => void; emptyText: string;
  opens?: boolean;   // rows open the role popup rather than filling the next column
}) {
  const max = Math.max(...items.map((i) => i.n), 1);
  return (
    <div className="min-w-0 rounded-xl border border-[#2b2b38] bg-[#15151f] overflow-hidden flex flex-col">
      <div className="px-3 py-2 border-b border-[#2b2b38] flex items-baseline gap-2">
        <span className="sub">{label}</span>
        <span className="text-[10.5px] text-gray-500 ml-auto">{note}</span>
      </div>
      <div className="overflow-y-auto max-h-[340px] p-1.5 space-y-0.5">
        {items.length === 0 && <div className="text-ey-faint text-[12px] p-3">{emptyText}</div>}
        {items.map((it) => {
          const on = it.key === selected;
          return (
            <button key={it.key} onClick={() => onPick(it.key)} title={`${it.name} — ${it.n}`}
              className={`group relative w-full text-left rounded-lg px-2.5 py-1.5 transition-colors ${on ? "bg-ey-yellow/15" : "hover:bg-white/5"}`}>
              <span className="absolute left-0 bottom-0 h-[2px] bg-ey-yellow/70 rounded-full"
                    style={{ width: `${Math.max(4, (it.n / max) * 100)}%` }} />
              <span className="flex items-baseline gap-2">
                <span className={`truncate text-[12.5px] ${on ? "text-ey-yellow font-bold" : "text-gray-200"}`}>{it.name}</span>
                <span className={`ml-auto flex-none text-[12px] tabular-nums ${on ? "text-ey-yellow font-bold" : "text-gray-400"}`}>{it.n}</span>
                {opens && <span className="flex-none text-[11px] text-ey-yellow opacity-0 group-hover:opacity-100 transition-opacity">{"→"}</span>}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DecompositionBrowser({ data, onDept }: { data: Data; onDept: (sel: DrillSel) => void }) {
  const sectors = useMemo(() => data.sectors.filter((s) => s.roles > 0), [data]);
  const [sector, setSector] = useState(() => sectors[0]?.name ?? "");
  const cur = sectors.find((s) => s.name === sector) ?? sectors[0];
  const companies = useMemo(() => (cur?.companies ?? []).filter((c) => c.roles > 0), [cur]);
  const [slug, setSlug] = useState(() => companies[0]?.slug ?? "");
  const company = companies.find((c) => c.slug === slug) ?? companies[0];

  const depts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of data.roles_by_company[company?.slug ?? ""] || []) {
      const k = r.department || "Other";
      c[k] = (c[k] || 0) + 1;
    }
    return Object.entries(c).sort((a, b) => b[1] - a[1]);
  }, [data, company?.slug]);

  const pickSector = (name: string) => {
    setSector(name);
    const first = (sectors.find((s) => s.name === name)?.companies ?? []).filter((c) => c.roles > 0)[0];
    setSlug(first?.slug ?? "");
  };

  return (
    <div>
      <div className="flex items-center gap-1.5 flex-wrap text-[12px] mb-3">
        <span className="text-gray-500">All sectors</span>
        <span className="text-gray-600">{"›"}</span>
        <span className="chip bg-ey-yellow/15 text-ey-yellow font-bold">{cur?.name} <span className="opacity-70">{cur?.roles}</span></span>
        {company && <>
          <span className="text-gray-600">{"›"}</span>
          <span className="chip bg-white/10 text-gray-100 font-semibold">{company.name} <span className="opacity-60">{company.roles}</span></span>
        </>}
        <span className="ml-auto text-[11.5px] text-gray-500">pick a department to open every role in it</span>
      </div>
      <div className="grid md:grid-cols-3 gap-3">
        <DrillColumn
          label="1 · Sector" note={`${sectors.length} with demand`}
          items={sectors.map((s) => ({ key: s.name, name: s.name, n: s.roles }))}
          selected={cur?.name} onPick={pickSector} emptyText="No sectors."
        />
        <DrillColumn
          label="2 · Company" note={`${companies.length} hiring`}
          items={companies.map((c) => ({ key: c.slug, name: c.name, n: c.roles }))}
          selected={company?.slug} onPick={setSlug} emptyText="No accounts hiring in this sector."
        />
        <DrillColumn
          label="3 · Department" note={`${depts.length} in ${company?.name ?? "—"}`}
          items={depts.map(([d, n]) => ({ key: d, name: d, n }))}
          selected={undefined}
          onPick={(d) => company && onDept({ sector: cur.name, slug: company.slug, client: company.name, dept: d })}
          emptyText="No departments for this account."
          opens
        />
      </div>
    </div>
  );
}

// Collapse a messy posting title to its core role family so the cloud aggregates
// (e.g. "Beauty Advisor - Multibrand - Full Time - GVK Mall - Hyderabad" -> "Beauty Advisor").
function cleanRole(title: string): string {
  let t = title.split(/\s[-–—|]\s|,/)[0].trim();      // keep text before first dash/comma
  t = t.replace(/\s*\(.*?\)\s*/g, " ")                 // drop parentheticals
       .replace(/\s*[-–—]\s*$/,"")                     // trailing dash
       .replace(/\b(full|part)\s*time\b/gi, "")
       .replace(/\s{2,}/g, " ").trim();
  return t.length >= 3 ? t : title.trim();
}

type Dim = "practice" | "sector" | "region" | "city";

// Drill-down explorer: pick a slice (a tech practice, a sector, or a city) and
// see — across ALL companies — which roles and which skills/tools are hired for
// it. Answers "is <company> hiring <tool> inside Data & AI?" at a glance.
function ExplorePanel({ data }: { data: Data }) {
  const sectorOf = useMemo(() => {
    const m: Record<string, string> = {};
    for (const c of data.companies) m[c.slug] = c.sector;
    return m;
  }, [data]);
  const roles = useMemo(() => allRoles(data), [data]);

  const regionRank = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of roles) { const g = r.region || "Other"; c[g] = (c[g] || 0) + 1; }
    const order = ["North", "West", "South", "East", "Other"];
    return order.filter((g) => c[g]);
  }, [roles]);

  const options: Record<Dim, string[]> = useMemo(() => ({
    practice: data.practices.map((p) => p.name),
    sector: data.sectors.filter((s) => s.roles > 0).map((s) => s.name),
    region: regionRank,
    city: data.locations.map((l) => l.city),
  }), [data, regionRank]);

  const [dim, setDim] = useState<Dim>("practice");
  const [val, setVal] = useState<string>("Data & AI");

  // keep the value valid when the dimension changes
  const vals = options[dim];
  const active = vals.includes(val) ? val : vals[0];

  const matched = useMemo(() => roles.filter((r) => {
    if (dim === "practice") return (r.practices || []).includes(active);
    if (dim === "sector") return sectorOf[r.slug] === active;
    if (dim === "region") return (r.region || "Other") === active;
    return r.city === active;
  }), [roles, dim, active, sectorOf]);

  const roleWords: Word[] = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of matched) {
      const t = cleanRole(r.role_title || "");
      if (t) c[t] = (c[t] || 0) + 1;
    }
    return Object.entries(c).map(([text, count]) => ({ text, count }));
  }, [matched]);

  const skillWords: Word[] = useMemo(() => {
    const c: Record<string, number> = {};
    const practiceOfTool: Record<string, string> = {};
    for (const r of matched) {
      for (const t of r.tools || []) {
        c[t] = (c[t] || 0) + 1;
        if (!practiceOfTool[t] && (r.practices || [])[0]) practiceOfTool[t] = r.practices[0];
      }
    }
    return Object.entries(c).map(([text, count]) => ({
      text, count, color: PRACTICE_COLOR[practiceOfTool[text]] || undefined,
    }));
  }, [matched]);

  const companies = new Set(matched.map((r) => r.slug)).size;
  const dims: { k: Dim; label: string }[] = [
    { k: "practice", label: "Tech practice" }, { k: "sector", label: "Domain" },
    { k: "region", label: "Region" }, { k: "city", label: "City" },
  ];

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <div className="flex rounded-lg overflow-hidden border border-[#2b2b38]">
          {dims.map((d) => (
            <button key={d.k} onClick={() => setDim(d.k)}
              className={`px-3 py-1.5 text-[12px] font-semibold transition-colors ${dim === d.k ? "bg-ey-yellow text-black" : "bg-transparent text-gray-300 hover:bg-white/5"}`}>
              {d.label}
            </button>
          ))}
        </div>
        <select value={active} onChange={(e) => setVal(e.target.value)} className="rounded-lg px-3 py-1.5 text-[13px]">
          {vals.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <span className="ml-auto text-[12px] text-gray-400">
          <b className="text-white">{matched.length}</b> role{matched.length === 1 ? "" : "s"} · {companies} compan{companies === 1 ? "y" : "ies"}
        </span>
      </div>
      <div className="grid md:grid-cols-2 gap-4 mt-3">
        <div>
          <div className="sub mb-2">Roles being hired</div>
          {roleWords.length ? (
            <WordCloudChart words={roleWords} max={55} height={360} />
          ) : <div className="text-ey-faint text-xs py-10 text-center">No roles in this slice.</div>}
        </div>
        <div>
          <div className="sub mb-2">Skills &amp; tools in demand</div>
          {skillWords.length ? (
            <WordCloudChart words={skillWords} max={75} height={360} />
          ) : <div className="text-ey-faint text-xs py-10 text-center">No tool signals in this slice — roles here are largely non-technical.</div>}
        </div>
      </div>
      <div className="text-[11px] text-gray-500 mt-3">
        Box size reflects how many India openings mention it, across all tracked companies, in the selected {dims.find((d) => d.k === dim)!.label.toLowerCase()}. Hover a box for the exact count.
      </div>
    </div>
  );
}

const REGION_COLOR: Record<string, string> = {
  North: "#35a4e8", West: "#ffe600", South: "#57e188", East: "#ff8a4a", Other: "#8a8a96",
};

// BD account-allocation status colours (matches the leadership board legend).
const STATUS_COLOR: Record<string, string> = {
  Existing: "#57e188", New: "#35a4e8", "White Spaces": "#f3c300",
};
function statusDot(status: string) {
  return <span className="inline-block w-2.5 h-2.5 rounded-full flex-none" style={{ background: STATUS_COLOR[status] || "#8a8a96" }} />;
}

// "Hiring by region" — open roles per North/West/South/East and the accounts
// driving each region (the data-backed version of the BD account-allocation view).
function RegionSection({ data }: { data: Data }) {
  const rs = data.region_summary;
  const [reg, setReg] = useState(rs[0]?.name || "");
  const current = rs.find((r) => r.name === reg) || rs[0];
  if (!rs.length) return null;
  const bar = {
    grid: { left: 70, right: 36, top: 6, bottom: 6 },
    xAxis: { type: "value", show: false },
    yAxis: {
      type: "category", data: [...rs].reverse().map((r) => r.name),
      axisTick: { show: false }, axisLine: { show: false },
      axisLabel: { color: "#e9e9ee", fontSize: 12, fontWeight: 600 },
    },
    series: [{
      type: "bar", barWidth: 18,
      data: [...rs].reverse().map((r) => ({ value: r.roles, itemStyle: { color: REGION_COLOR[r.name] || "#8a8a96", borderRadius: 4 } })),
      label: { show: true, position: "right", color: "#e9e9ee", fontWeight: 800, fontSize: 11 },
    }],
  };
  return (
    <>
      <SectionTitle title="Hiring by region" note="India demand across North / West / South / East — and the accounts driving each region" />
      <div className="grid md:grid-cols-5 gap-4">
        <div className="card p-4 md:col-span-2">
          <div className="sub mb-2">Open roles by region</div>
          <Echart option={bar as any} height={210} />
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-[10.5px] text-gray-300">
            <span className="flex items-center gap-1">{statusDot("Existing")} Existing</span>
            <span className="flex items-center gap-1">{statusDot("New")} New</span>
            <span className="flex items-center gap-1">{statusDot("White Spaces")} White Spaces</span>
          </div>
        </div>
        <div className="card p-0 md:col-span-3 overflow-hidden flex flex-col">
          <div className="flex gap-1 p-3 pb-2 flex-wrap">
            {rs.map((r) => (
              <button key={r.name} onClick={() => setReg(r.name)}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors ${reg === r.name ? "bg-ey-yellow text-black" : "bg-white/5 text-gray-300 hover:bg-white/10"}`}>
                {r.name} <span className="opacity-70">{r.roles}</span>
              </button>
            ))}
          </div>
          <div className="overflow-auto max-h-[300px]">
            <table className="w-full text-[12.5px]">
              <thead className="sticky top-0 bg-ey-black text-white text-left">
                <tr>
                  <th className="px-3 py-2 font-semibold text-[11px]">Account</th>
                  <th className="px-3 py-2 font-semibold text-[11px]">Domain</th>
                  <th className="px-3 py-2 font-semibold text-[11px]">Status</th>
                  <th className="px-3 py-2 font-semibold text-[11px] text-right">Open roles</th>
                </tr>
              </thead>
              <tbody>
                {current.accounts.map((a) => (
                  <tr key={a.slug} className="border-b border-[#2b2b38] hover:bg-[#23232e]">
                    <td className="px-3 py-2 font-medium text-gray-100">{a.name}</td>
                    <td className="px-3 py-2 text-gray-400">{a.sector}</td>
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-2 text-gray-200">{statusDot(a.status)}{a.status}</span>
                    </td>
                    <td className="px-3 py-2 text-right"><b className="text-white">{a.roles}</b></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="text-[10.5px] text-gray-500 px-3 py-2 border-t border-[#2b2b38]">
            Status shows <b>Existing</b> for tracked accounts with live India demand. <b>New</b> / <b>White Spaces</b> populate once the BD target list is added.
          </div>
        </div>
      </div>
    </>
  );
}

function heatmapOption(dm: Data["demand_matrix"]) {
  const secs = dm.sectors.map((s) => s.name);
  const pracs = dm.practices.map((p) => p.name.replace(" tools", "").replace(" / CRM", "").replace(" & Infra", ""));
  const maxVal = Math.max(1, ...dm.cells.map((c) => c[2]));
  return {
    tooltip: {
      position: "top",
      formatter: (p: any) =>
        `${secs[p.data[1]]}<br/>${dm.practices[p.data[0]].name}: <b>${p.data[2]}</b> role${p.data[2] === 1 ? "" : "s"}`,
    },
    grid: { left: 150, right: 18, top: 44, bottom: 10, containLabel: false },
    xAxis: {
      type: "category", data: pracs, position: "top",
      axisTick: { show: false }, axisLine: { show: false },
      axisLabel: { color: "#c7c7d0", fontSize: 10.5, interval: 0, rotate: 0, hideOverlap: false,
        formatter: (v: string) => v.length > 10 ? v.slice(0, 9) + "…" : v },
      splitArea: { show: false },
    },
    yAxis: {
      type: "category", data: secs,
      axisTick: { show: false }, axisLine: { show: false },
      axisLabel: { color: "#e9e9ee", fontSize: 11, fontWeight: 600 },
      splitArea: { show: false },
    },
    visualMap: {
      min: 1, max: maxVal, calculable: false, show: false,
      // >=1 cells use the brightened ramp; 0-count cells fall out of range and
      // render as a visible dark box (outOfRange) rather than vanishing.
      inRange: { color: ["#363d5a", "#6e6015", "#b89a0f", "#ffe600"] },
      outOfRange: { color: ["#20273c"] },
    },
    series: [{
      type: "heatmap",
      // store expects [sectorIdx, practiceIdx, count]; ECharts heatmap wants [x,y,val]=[prac,sec,val].
      // keep real counts (incl. 0) so every cell stays a box; 0s get the outOfRange color.
      data: dm.cells.map((c) => [c[1], c[0], c[2]]),
      label: {
        show: true, fontSize: 11, fontWeight: 800,
        // light number on dark (low) cells, dark number on bright (high) cells
        color: (p: any) => (p.data[2] >= maxVal * 0.45 ? "#0b0b0f" : "#eef0f6"),
        formatter: (p: any) => (p.data[2] > 0 ? p.data[2] : ""),
      },
      itemStyle: { borderColor: "#0b0b0f", borderWidth: 2, borderRadius: 3 },
      emphasis: { itemStyle: { borderColor: "#fff", borderWidth: 1.5 } },
    }],
  };
}

export default function Summary() {
  const { data, error } = useData();
  const [view, setView] = useState<"charts" | "explore">("charts");
  const [drill, setDrill] = useState<DrillSel | null>(null);
  if (error) return <div className="mt-10 text-[#ff8a7a]">Could not load data.json — {error}</div>;
  if (!data) return <div className="mt-10 text-gray-500">Loading…</div>;

  const t = data.totals;
  const topCity = data.locations[0]?.city || "—";
  const kpis = [
    { v: t.roles, l: "Open India roles", s: "last 30 days", accent: "text-white" },
    { v: t.with_roles, l: "Accounts hiring", s: `of ${t.companies} tracked`, accent: "text-[#57e188]" },
    { v: t.sectors, l: "Industry sectors", s: "coverage", accent: "text-ey-yellow" },
    { v: data.locations[0]?.roles || 0, l: `Roles in ${topCity}`, s: "top GCC hub", accent: "text-[#35a4e8]" },
  ];

  return (
    <div>
      <div className="mt-5">
        <h1 className="text-xl font-extrabold m-0 text-white">Market Insights — Summary</h1>
        <div className="text-gray-500 text-xs">{data.month_label}</div>
      </div>

      <div className="grid gap-3.5 grid-cols-2 md:grid-cols-4 mt-4">
        {kpis.map((k, i) => (
          <div key={i} className="card p-4 relative overflow-hidden animate-in" style={{ animationDelay: `${i * 0.06}s` }}>
            <span className="absolute left-0 top-0 bottom-0 w-1 bg-ey-yellow" />
            <div className={`text-[28px] font-extrabold leading-none ${k.accent}`}><CountUp value={k.v} /></div>
            <div className="text-gray-300 text-xs mt-1.5 font-semibold">{k.l}</div>
            <div className="text-gray-500 text-[11px]">{k.s}</div>
          </div>
        ))}
      </div>

      <div className="flex items-baseline gap-3 mt-7 mb-3 flex-wrap">
        <h2 className="text-base font-extrabold m-0 flex items-center">
          <span className="inline-block w-1 h-4 bg-ey-yellow mr-2.5" />
          Overall open roles
        </h2>
        <span className="text-ey-faint text-xs">
          {view === "charts" ? "where the demand sits — by sector, tech space and location" : "drill into a slice — which roles & skills are hired across all companies"}
        </span>
        <div className="ml-auto flex rounded-lg overflow-hidden border border-[#2b2b38]">
          {([["charts", "Charts"], ["explore", "Explore"]] as const).map(([k, lbl]) => (
            <button key={k} onClick={() => setView(k)}
              className={`px-3 py-1.5 text-[12px] font-semibold transition-colors ${view === k ? "bg-ey-yellow text-black" : "bg-transparent text-gray-300 hover:bg-white/5"}`}>
              {lbl}
            </button>
          ))}
        </div>
      </div>
      {view === "charts" ? (
        <div className="grid md:grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="sub mb-2">In different sectors / industry</div>
            <Echart option={hbar(data.sectors.map((s) => [s.name, s.roles])) as any} height={210} />
          </div>
          <div className="card p-4">
            <div className="sub mb-2">In different tech space</div>
            <Echart option={hbar(data.practices.map((p) => [p.name, p.roles])) as any} height={210} />
          </div>
          <div className="card p-4">
            <div className="sub mb-2">In different locations</div>
            <Echart option={hbar(data.locations.map((l) => [l.city, l.roles])) as any} height={210} />
          </div>
        </div>
      ) : (
        <ExplorePanel data={data} />
      )}

      <RegionSection data={data} />

      <SectionTitle title="Technology demand radar" note="skill/tool practices hired for across the whole book" />
      <div className="card p-4 grid md:grid-cols-5 gap-4 items-center">
        <div className="md:col-span-3">
          <Echart option={radarOption(data.tech_radar) as any} height={330} />
        </div>
        <div className="md:col-span-2">
          <div className="sub mb-2">Roles per capability</div>
          <div className="space-y-1.5">
            {[...data.tech_radar].sort((a, b) => b.value - a.value).map((r) => {
              const max = Math.max(...data.tech_radar.map((x) => x.value), 1);
              const c = PRACTICE_COLOR[r.practice] || "#8a8a96";
              return (
                <div key={r.practice} className="flex items-center gap-2.5">
                  <span className="w-2 h-2 rounded-full flex-none" style={{ background: c }} />
                  <span className="text-[12.5px] text-gray-200 truncate flex-none w-[118px]">{r.practice}</span>
                  <span className="flex-1 h-1.5 rounded-full bg-[#23232e] overflow-hidden">
                    <span className="block h-full rounded-full" style={{ width: `${(r.value / max) * 100}%`, background: c }} />
                  </span>
                  <span className="text-[12px] tabular-nums text-gray-300 w-8 text-right">{r.value}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <SectionTitle
        title="Decomposition — sector → company → department"
        note="walk the book one level at a time: pick a sector, then an account, then a department"
      />
      <div className="card p-4">
        <DecompositionBrowser data={data} onDept={setDrill} />
      </div>

      <SectionTitle title="Where capabilities are being built" note="sector × tech practice — India roles mapped to each capability, by industry" />
      <div className="card p-4">
        {data.demand_matrix.sectors.length > 0 ? (
          <>
            <Echart
              option={heatmapOption(data.demand_matrix) as any}
              height={Math.max(220, data.demand_matrix.sectors.length * 34 + 60)}
            />
            <div className="text-[11px] text-gray-500 mt-2">
              Brighter cells mark where a sector is building most. Rows and columns are ranked by total demand; blank cells mean no India roles mapped to that capability this month.
            </div>
          </>
        ) : (
          <div className="text-ey-faint text-xs py-8 text-center">No tech-mapped roles yet.</div>
        )}
      </div>

      {drill && <DrillModal data={data} sel={drill} onClose={() => setDrill(null)} />}

      <footer className="text-gray-500 text-[11px] mt-8 pt-3.5 border-t border-[#2b2b38]">
        India hiring scraped from each client's own career portal; market signals from public news. Last 30 days. Internal use.
      </footer>
    </div>
  );
}
