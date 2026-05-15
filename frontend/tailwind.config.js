/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        bg: "#0b0f17",
        surface: "#121826",
        surface2: "#1a2232",
        border: "#243047",
        text: "#e6e9ef",
        muted: "#8b95a7",
        accent: "#3B82F6",
        impactHigh: "#EF4444",
        impactMedium: "#F59E0B",
        impactLow: "#22C55E",
        nodePast: "#3B82F6",
        nodeCurrent: "#F97316",
        nodeFuture: "#6B7280",
      },
    },
  },
  plugins: [],
};
