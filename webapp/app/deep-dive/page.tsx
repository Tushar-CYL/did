"use client";
import { useMemo, useState } from "react";
import {
  useReactTable, getCoreRowModel, getSortedRowModel, getFilteredRowModel,
  flexRender, createColumnHelper, SortingState,
} from "@tanstack/react-table";
import { useData, allRoles, RoleRow } from "@/lib/data";
import type { Company } from "@/lib/types";
import { SectionTitle } from "@/components/ui";
import Echart from "@/components/Echart";

const BAR = "#ffe600";
function hbar(data: [string, number][], n = 10) {
  const d = data.slice(0, n).reverse();
  return {
    grid: { left: 150, right: 36, top: 6, bottom: 6 },
    xAxis: { type: "value", show: false },
    yAxis: { type: "category", data: d.map((x) => x[0]), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: "#c7c7d0", fontSize: 11 } },
    series: [{ type: "bar", data: d.map((x) => x[1]), barWidth: 13, itemStyle: { color: BAR, borderRadius: 4 }, label: { show: true, position: "right", color: "#e9e9ee", fontWeight: 800, fontSize: 11 } }],
  };
}
function radarOption(axes: string[], values: number[]) {
  const max = Math.max(...values, 1);
  return {
    radar: {
      indicator: axes.map((a) => ({ name: a, max })), radius: "64%", splitNumber: 4,
      axisName: { color: "#c7c7d0", fontSize: 10 }, splitLine: { lineStyle: { color: "#2b2b38" } },
      splitArea: { areaStyle: { color: ["#15151f", "#1a1a24"] } }, axisLine: { lineStyle: { color: "#2b2b38" } },
    },
    series: [{ type: "radar", data: [{ value: values, areaStyle: { color: "rgba(255,230,0,.22)" }, lineStyle: { color: BAR, width: 2 }, itemStyle: { color: BAR } }] }],
  };
}

const col = createColumnHelper<RoleRow>();

export default function DeepDive() {
  const { data, error } = useData();
  const [client, setClient] = useState("");
  const [dept, setDept] = useState("all");
  const [juniorOnly, setJuniorOnly] = useState(false);
  const [q, setQ] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "aging_days", desc: false }]);

  const company: Company | undefined = useMemo(() => {
    if (!data) return undefined;
    const withRoles = data.companies.filter((c) => c.total > 0);
    const sel = client || (withRoles[0]?.slug ?? data.companies[0]?.slug);
    return data.companies.find((c) => c.slug === sel);
  }, [data, client]);

  const rows = useMemo(() => {
    if (!data || !company) return [];
    return allRoles(data).filter((r) =>
      r.slug === company.slug &&
      (dept === "all" || r.department === dept) &&
      (!juniorOnly || !["Executive"].includes(r.seniority)) &&
      (!q || (r.role_title + " " + (r.tools || []).join(" ") + " " + r.location).toLowerCase().includes(q.toLowerCase()))
    );
  }, [data, company, dept, juniorOnly, q]);

  const columns = useMemo(() => [
    col.accessor("role_title", { header: "Role", cell: (i) => <span className="font-medium block max-w-[220px] truncate" title={i.getValue() as string}>{i.getValue()}</span> }),
    col.accessor("department", { header: "Department" }),
    col.accessor((r) => (r.tools || []).join(", "), {
      id: "tools", header: "Skills / tools", enableSorting: false,
      cell: (i) => {
        const ts = i.row.original.tools || [];
        return ts.length ? <div className="flex flex-wrap gap-1">{ts.slice(0, 6).map((t) => <span key={t} className="chip !text-[10px] bg-[#2a2a38] text-gray-200">{t}</span>)}</div> : <span className="text-ey-faint">—</span>;
      },
    }),
    col.accessor("team", { header: "Team", cell: (i) => i.getValue() || <span className="text-ey-faint">—</span> }),
    col.accessor("seniority", { header: "Seniority" }),
    col.accessor("location", { header: "Location" }),
    col.accessor("posted_date", { header: "Posted" }),
    col.accessor("aging_days", { header: "Aging", cell: (i) => (i.getValue() == null ? "—" : `${i.getValue()}d`) }),
    col.accessor("source_url", { header: "", enableSorting: false, cell: (i) => i.getValue() ? <a href={i.getValue() as string} target="_blank" rel="noopener" className="text-[#5fb0f0]">open</a> : null }),
  ], []);

  const table = useReactTable({
    data: rows, columns, state: { sorting }, onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getFilteredRowModel: getFilteredRowModel(),
  });

  if (error) return <div className="mt-10 text-[#ff8a7a]">Could not load data.json — {error}</div>;
  if (!data || !company) return <div className="mt-10 text-gray-500">Loading…</div>;

  const depts = [...new Set(allRoles(data).filter((r) => r.slug === company.slug).map((r) => r.department))].sort();
  const axes = data.tech_radar.map((p) => p.practice);
  const pracMap = new Map(company.practices);
  const radarVals = axes.map((a) => pracMap.get(a) || 0);

  return (
    <div>
      <div className="flex items-center gap-2 flex-wrap mt-5">
        <div>
          <h1 className="text-xl font-extrabold m-0 text-white">Market Insights — Deep Dive</h1>
          <div className="text-gray-500 text-xs">{data.month_label}</div>
        </div>
        <div className="ml-auto flex gap-2 flex-wrap items-center">
          <select value={client || company.slug} onChange={(e) => setClient(e.target.value)} className="rounded-lg px-3 py-2 text-[13px]">
            {data.companies.map((c) => <option key={c.slug} value={c.slug}>{c.name}{c.total ? ` (${c.total})` : ""}</option>)}
          </select>
          <select value={dept} onChange={(e) => setDept(e.target.value)} className="rounded-lg px-3 py-2 text-[13px]">
            <option value="all">All departments</option>
            {depts.map((d) => <option key={d}>{d}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-[13px] text-gray-400"><input type="checkbox" checked={juniorOnly} onChange={(e) => setJuniorOnly(e.target.checked)} /> Manager &amp; below</label>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search role / tool / location" className="rounded-lg px-3 py-2 text-[13px] min-w-[210px]" />
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap mt-4">
        <h2 className="text-2xl font-extrabold text-ey-yellow m-0">{company.name}</h2>
        <span className="text-[12px] text-gray-400">{company.sector}</span>
        {company.region && <span className="chip bg-white/10 text-gray-200">Base: {data.regions[company.region] || company.region}</span>}
        {company.career_url && <a href={company.career_url} target="_blank" rel="noopener" className="text-[12px] text-[#5fb0f0]">Careers portal</a>}
        <span className="ml-auto text-[13px] text-gray-400"><b className="text-white text-lg">{company.total}</b> open India roles</span>
      </div>

      <div className="grid md:grid-cols-2 gap-4 mt-3">
        <div className="card p-4">
          <div className="sub mb-2">Insight</div>
          {company.tools.length > 0 && (
            <div className="mb-3">
              <div className="text-[11px] text-gray-400 font-semibold mb-1.5">Top skills in demand</div>
              <div className="flex flex-wrap gap-1.5">
                {company.tools.slice(0, 10).map(([tool, n]) => (
                  <span key={tool} className="chip !text-[11px] bg-ey-yellow/15 text-ey-yellow font-semibold">
                    {tool} <span className="opacity-60">{n}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          {company.insight.length ? (
            <ul className="space-y-2 border-t border-[#2b2b38] pt-3">
              {company.insight.map((t, i) => (
                <li key={i} className="flex gap-2.5 text-[13.5px] leading-snug text-gray-200">
                  <span className="mt-[7px] w-1.5 h-1.5 rounded-full flex-none bg-ey-yellow" /><span>{t}</span>
                </li>
              ))}
            </ul>
          ) : <p className="text-ey-faint text-sm">No hiring insight for this account in the window.</p>}
        </div>
        <div className="card p-4">
          <div className="sub mb-2">{company.practices.length ? "Across tech space" : "Hiring by department"}</div>
          {company.practices.length ? <>
            <Echart option={hbar(company.practices.map((p) => [p[0], p[1]])) as any} height={150} />
            <Echart option={radarOption(axes, radarVals) as any} height={180} />
          </> : company.departments.length ? <>
            <p className="text-ey-faint text-[12px] mb-1 leading-snug">
              Roles here are largely non-technical, so no tool practices were extracted. Demand by business function:
            </p>
            <Echart option={hbar(company.departments.map((d) => [d[0], d[1]])) as any} height={240} />
          </> : <p className="text-ey-faint text-sm">No roles in the window for this account.</p>}
        </div>
      </div>

      {company.news.length > 0 && (() => {
        const ORDER = ["Vision & strategy", "Partnerships", "Financial", "Expansion", "Hiring"];
        const groups = ORDER
          .map((cat) => ({ cat, items: company.news.filter((n) => n.category === cat) }))
          .filter((g) => g.items.length > 0);
        return (
          <>
            <SectionTitle title="Recent news" note="public market signals from the last 30 days — grouped by theme" />
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
              {groups.map((g) => (
                <div key={g.cat} className="card p-4">
                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="inline-block w-1 h-3.5 bg-ey-yellow" />
                    <div className="font-extrabold text-[13px] text-white">{g.cat}</div>
                    <span className="text-[11px] text-gray-400 ml-auto">{g.items.length}</span>
                  </div>
                  <ul className="space-y-2.5">
                    {g.items.map((n, i) => (
                      <li key={i} className="leading-snug">
                        {n.url ? (
                          <a href={n.url} target="_blank" rel="noopener" className="text-[12.5px] text-gray-100 hover:text-[#5fb0f0]">{n.title}</a>
                        ) : (
                          <span className="text-[12.5px] text-gray-100">{n.title}</span>
                        )}
                        <div className="text-[10.5px] text-gray-400 mt-0.5">{[n.source, n.date].filter(Boolean).join(" · ")}</div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </>
        );
      })()}

      <SectionTitle title="Open roles" note={`${rows.length} roles · skills/tools + aging · sort any column`} />
      <div className="card p-0 overflow-auto max-h-[620px]">
        <table className="w-full text-xs">
          <thead className="sticky top-0">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="bg-ey-black text-white text-left">
                {hg.headers.map((h) => (
                  <th key={h.id} onClick={h.column.getToggleSortingHandler()} className="p-2.5 text-[11px] cursor-pointer select-none whitespace-nowrap">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: " ▲", desc: " ▼" }[h.column.getIsSorted() as string] ?? ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-[#2b2b38] hover:bg-[#23232e] align-top">
                {row.getVisibleCells().map((cell) => <td key={cell.id} className="p-2.5">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
              </tr>
            ))}
            {rows.length === 0 && <tr><td className="p-2.5 text-ey-faint" colSpan={9}>No roles match.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
