"use client";
import React from "react";

export interface Word {
  text: string;
  count: number;
  color?: string;
}

/**
 * Dependency-free "word cloud": each term is sized by its hiring count (sqrt
 * scale so a few huge counts don't swamp the rest). Flows/wraps, works in light
 * and dark, and shows the exact count on hover. No external library.
 */
export default function WordCloud({
  words,
  max = 60,
  min = 12,
  maxPx = 30,
  minPx = 11.5,
  empty = "No data for this slice.",
}: {
  words: Word[];
  max?: number;
  min?: number;
  maxPx?: number;
  minPx?: number;
  empty?: string;
}) {
  const items = [...words].sort((a, b) => b.count - a.count).slice(0, max);
  if (items.length === 0) {
    return <div className="text-ey-faint text-xs py-8 text-center">{empty}</div>;
  }
  const hi = Math.max(...items.map((w) => w.count));
  const lo = Math.min(...items.map((w) => w.count));
  const size = (c: number) => {
    if (hi === lo) return (maxPx + minPx) / 2;
    const t = (Math.sqrt(c) - Math.sqrt(lo)) / (Math.sqrt(hi) - Math.sqrt(lo));
    return minPx + t * (maxPx - minPx);
  };
  // brightest for the largest, dimming toward the smallest, when no color given
  const opacity = (c: number) => (hi === lo ? 0.92 : 0.55 + 0.45 * ((c - lo) / (hi - lo)));

  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5 leading-tight">
      {items.map((w) => (
        <span
          key={w.text}
          title={`${w.text} — ${w.count} role${w.count === 1 ? "" : "s"}`}
          className="font-bold whitespace-nowrap cursor-default transition-colors"
          style={{
            fontSize: `${size(w.count).toFixed(1)}px`,
            color: w.color || "#e9e9ee",
            opacity: w.color ? 1 : opacity(w.count),
          }}
        >
          {w.text}
          <span className="align-super ml-0.5 text-[9px] font-extrabold opacity-60">{w.count}</span>
        </span>
      ))}
    </div>
  );
}
