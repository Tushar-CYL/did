"use client";
import { useEffect, useMemo, useState } from "react";
import { useData, allRoles } from "@/lib/data";
import type { Data } from "@/lib/types";
import { SectionTitle } from "@/components/ui";
import Echart from "@/components/Echart";
import type { Word } from "@/components/WordCloud";

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

function _lerp(a: string, b: string, t: number): string {
  const h = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const A = h(a), B = h(b);
  return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join("");
}

// Treemap: each role/skill is a rectangle sized by its hiring count — a cleaner,
// more "finished" read than floating text. Roles use a blue magnitude scale;
// skills are colored by their tech practice.
function treemapOption(items: { text: string; count: number; color?: string }[], kind: "role" | "skill", top: number) {
  const data = [...items].sort((a, b) => b.count - a.count).slice(0, top);
  const max = Math.max(1, ...data.map((d) => d.count));
  return {
    tooltip: {
      formatter: (p: any) => `${p.name} — <b>${p.value}</b> role${p.value === 1 ? "" : "s"}`,
    },
    series: [{
      type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
      top: 2, left: 2, right: 2, bottom: 2, width: "100%", height: "100%",
      itemStyle: { borderColor: "#0f0f17", borderWidth: 2, gapWidth: 2, borderRadius: 4 },
      label: {
        show: true, position: "insideTopLeft", color: "#ffffff", fontSize: 12, fontWeight: 600,
        textShadowColor: "rgba(0,0,0,.65)", textShadowBlur: 3, overflow: "truncate",
        formatter: (p: any) => `${p.name}  ${p.value}`,
      },
      upperLabel: { show: false },
      data: data.map((d) => ({
        name: d.text, value: d.count,
        itemStyle: { color: kind === "skill" ? (d.color || "#4a72c4") : _lerp("#2b3350", "#6f82c6", d.count / max) },
      })),
    }],
  };
}

function treeOption(d: Data) {
  // sector -> company -> department (click to drill). Department counts come
  // from roles_by_company so the tree reaches the role-type level.
  const deptsFor = (slug: string) => {
    const c: Record<string, number> = {};
    for (const r of d.roles_by_company[slug] || []) c[r.department || "Other"] = (c[r.department || "Other"] || 0) + 1;
    return Object.entries(c).sort((a, b) => b[1] - a[1]);
  };
  const root = {
    name: "Open roles",
    children: d.sectors.filter((s) => s.roles > 0).map((s) => ({
      name: `${s.name} · ${s.roles}`,
      children: s.companies.slice(0, 8).map((c) => ({
        name: `${c.name} (${c.roles})`,
        children: deptsFor(c.slug).map(([dep, n]) => ({ name: `${dep} (${n})`, value: n })),
      })),
    })),
  };
  return {
    tooltip: { trigger: "item", triggerOn: "mousemove" },
    series: [{
      type: "tree", data: [root], top: 8, left: 90, bottom: 8, right: 160,
      symbolSize: 7, orient: "LR", initialTreeDepth: 1, expandAndCollapse: true,
      itemStyle: { color: BAR, borderColor: BAR },
      label: { color: "#e9e9ee", fontSize: 11, position: "left", align: "right" },
      leaves: { label: { position: "right", align: "left", color: "#c7c7d0" } },
      lineStyle: { color: "#3a3a4a", width: 1 },
      emphasis: { focus: "descendant" },
      animationDuration: 450,
    }],
  };
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

type Dim = "practice" | "sector" | "city";

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

  const options: Record<Dim, string[]> = useMemo(() => ({
    practice: data.practices.map((p) => p.name),
    sector: data.sectors.filter((s) => s.roles > 0).map((s) => s.name),
    city: data.locations.map((l) => l.city),
  }), [data]);

  const [dim, setDim] = useState<Dim>("practice");
  const [val, setVal] = useState<string>("Data & AI");

  // keep the value valid when the dimension changes
  const vals = options[dim];
  const active = vals.includes(val) ? val : vals[0];

  const matched = useMemo(() => roles.filter((r) => {
    if (dim === "practice") return (r.practices || []).includes(active);
    if (dim === "sector") return sectorOf[r.slug] === active;
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
    { k: "practice", label: "Tech practice" }, { k: "sector", label: "Sector" }, { k: "city", label: "City" },
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
            <Echart option={treemapOption(roleWords, "role", 24) as any} height={340} />
          ) : <div className="text-ey-faint text-xs py-10 text-center">No roles in this slice.</div>}
        </div>
        <div>
          <div className="sub mb-2">Skills &amp; tools in demand</div>
          {skillWords.length ? (
            <Echart option={treemapOption(skillWords, "skill", 30) as any} height={340} />
          ) : <div className="text-ey-faint text-xs py-10 text-center">No tool signals in this slice — roles here are largely non-technical.</div>}
        </div>
      </div>
      <div className="text-[11px] text-gray-500 mt-3">
        Box size reflects how many India openings mention it, across all tracked companies, in the selected {dims.find((d) => d.k === dim)!.label.toLowerCase()}. Hover a box for the exact count.
      </div>
    </div>
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

      <SectionTitle title="Technology demand radar" note="skill/tool practices hired for across the whole book" />
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4"><Echart option={radarOption(data.tech_radar) as any} height={300} /></div>
        <div className="card p-4">
          <div className="sub mb-1">Decomposition — sector → company → department</div>
          <div className="text-[11px] text-gray-500 mb-1">click to expand: a sector reveals its companies, a company reveals its departments</div>
          <Echart option={treeOption(data) as any} height={300} />
        </div>
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

      <footer className="text-gray-500 text-[11px] mt-8 pt-3.5 border-t border-[#2b2b38]">
        India hiring scraped from each client's own career portal; market signals from public news. Last 30 days. Internal use.
      </footer>
    </div>
  );
}
