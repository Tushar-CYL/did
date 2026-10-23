"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const LINKS = [
  { href: "/", label: "Insight summary" },
  { href: "/deep-dive/", label: "Deep dive" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-20 bg-ey-black text-white">
      <div className="max-w-[1320px] mx-auto px-6 h-14 flex items-center gap-5">
        <div className="flex items-center gap-2.5">
          <span aria-hidden className="flex items-end gap-[3px] h-8 w-8 justify-center">
            <span className="w-1.5 bg-ey-yellow rounded-sm" style={{ height: "40%" }} />
            <span className="w-1.5 bg-ey-yellow rounded-sm" style={{ height: "68%" }} />
            <span className="w-1.5 bg-ey-yellow rounded-sm" style={{ height: "100%" }} />
          </span>
          <div className="leading-tight">
            <div className="font-extrabold text-[13.5px]">India Account Intelligence</div>
            <div className="text-[10.5px] text-gray-300">Technology consulting sales engine</div>
          </div>
        </div>
        <nav className="ml-6 flex gap-1">
          {LINKS.map((l) => {
            const on = path === l.href || (l.href !== "/" && path.startsWith(l.href));
            return (
              <Link
                key={l.href}
                href={l.href}
                className={clsx(
                  "px-3.5 py-1.5 rounded-md text-[13px] font-semibold transition-colors",
                  on ? "bg-ey-yellow text-ey-black" : "text-gray-300 hover:bg-ey-black2 hover:text-white"
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
