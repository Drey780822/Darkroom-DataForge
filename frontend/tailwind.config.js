/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkroom: {
          bg: "#0B1020",
          surface: "#111827",
          card: "#172033",
          border: "#1F2937",
          borderLight: "#374151",
          navy: "#1D3557",
          navyLight: "#2A4A7F",
          gold: "#D4AF37",
          goldHover: "#E5C158",
          goldLight: "rgba(212, 175, 55, 0.12)",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444",
          text: "#F9FAFB",
          muted: "#9CA3AF",
        }
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Courier New", "monospace"],
      }
    },
  },
  plugins: [],
}
