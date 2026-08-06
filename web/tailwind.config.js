/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // App chrome palette (neutral, professional)
        bg: "#f8fafc",
        surface: "#ffffff",
        border2: "#e2e8f0",
        text2: "#0f172a",
        muted: "#64748b",
        muted2: "#94a3b8",
        accent: "#2563eb",
        accentSoft: "#eff6ff",
        accentHover: "#1d4ed8",
        disabled: "#cbd5e1",
        success: "#16a34a",
        warning: "#d97706",
        danger: "#dc2626",
        dangerSoft: "#fef2f2",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out",
        "slide-up": "slide-up 0.15s ease-out",
      },
    },
  },
  plugins: [],
};