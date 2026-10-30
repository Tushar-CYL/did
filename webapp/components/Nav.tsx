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
        <div className="flex items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/ey-logo.png" alt="EY" className="h-9 w-9 rounded" />
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
