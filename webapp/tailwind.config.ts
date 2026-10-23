import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ey: {
          black: "#2e2e38",
          black2: "#23232b",
          yellow: "#ffe600",
          yellow2: "#f3c300",
          ink: "#2e2e38",
          muted: "#9a9aa8",
          faint: "#b6b6c2",
          line: "#e7e7ea",
          lt: "#f6f6f8",
          bg: "#f2f2f4",
          good: "#15803d",
          amber: "#b45309",
          red: "#b42318",
          blue: "#35a4e8",
        },
      },
      fontFamily: {
        sans: ["'Segoe UI'", "Arial", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px #2e2e3810, 0 12px 30px -20px #2e2e3840",
      },
      borderRadius: { xl2: "14px" },
    },
  },
  plugins: [],
};
export default config;
