import "./globals.css";
import type { Metadata } from "next";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "India Account Intelligence",
  description: "Technology consulting sales engine — hiring and market intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="max-w-[1320px] mx-auto px-6 pb-20">{children}</main>
      </body>
    </html>
  );
}
