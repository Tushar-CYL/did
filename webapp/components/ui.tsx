import clsx from "clsx";
import React from "react";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={clsx("card p-4", className)}>{children}</div>;
}

export function SectionTitle({ title, note }: { title: string; note?: string }) {
  return (
    <div className="flex items-baseline gap-3 mt-7 mb-3">
      <h2 className="text-base font-extrabold m-0 flex items-center">
        <span className="inline-block w-1 h-4 bg-ey-yellow mr-2.5" />
        {title}
      </h2>
      {note && <span className="text-ey-faint text-xs">{note}</span>}
    </div>
  );
}

const CONF: Record<string, string> = {
  High: "text-ey-good bg-green-100",
  Medium: "text-ey-amber bg-amber-100",
  Low: "text-ey-muted bg-gray-200",
  Unknown: "text-ey-faint bg-gray-100",
};
export function ConfBadge({ c }: { c: string }) {
  return <span className={clsx("chip !px-1.5 !py-px !text-[9px] font-extrabold", CONF[c] || CONF.Unknown)}>{c}</span>;
}

const PRI: Record<string, string> = {
  High: "text-ey-red bg-red-100",
  Medium: "text-ey-amber bg-amber-100",
  Low: "text-ey-muted bg-gray-100",
};
export function PriorityBadge({ p }: { p: string }) {
  return <span className={clsx("chip !px-2 !py-px !text-[9px] font-extrabold", PRI[p] || PRI.Low)}>{p}</span>;
}

export function Tag({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span className="chip text-white font-extrabold !text-[9px]" style={{ background: color }}>
      {children}
    </span>
  );
}
