import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        gold: {
          DEFAULT: "#bc892d",
          light: "#d4a040",
          dark: "#9a6f1f",
        },
      },
      fontFamily: {
        body: ["Figtree", "system-ui", "sans-serif"],
        heading: ["Oswald", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
