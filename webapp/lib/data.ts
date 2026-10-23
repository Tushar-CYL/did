"use client";
import { useEffect, useState } from "react";
import type { Data } from "./types";

// Data-driven: the app fetches /data.json at runtime, so swapping the file + reload updates everything.
export function useData() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch(`/data.json?v=${Date.now()}`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`data.json ${r.status}`);
        return r.json();
      })
      .then((d: Data) => setData(d))
      .catch((e) => setError(String(e)));
  }, []);
  return { data, error };
}

export const allRoles = (d: Data) =>
  Object.entries(d.roles_by_company).flatMap(([slug, rs]) =>
    rs.map((r) => ({ ...r, slug, client: d.names[slug] }))
  );

export type RoleRow = ReturnType<typeof allRoles>[number];
