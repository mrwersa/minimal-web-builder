/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#f7f9fb",
        surface: "#ffffff",
        border2: "#e3e8ee",
        text2: "#222222",
        muted: "#78909c",
        accent: "#1976d2",
        accentSoft: "#e3f2fd",
        disabled: "#b0b8c1",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};