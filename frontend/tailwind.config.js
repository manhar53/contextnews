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
        // Calm neutral graphite (Uncodixfy: no blue cast, low chroma)
        bg: "#0c0c0d",
        surface: "#161617",
        surface2: "#1f1f22",
        border: "#2b2b30",
        text: "#e6e6e6",
        muted: "#8a8a90",
        accent: "#5b6168",
        impactHigh: "#d05656",
        impactMedium: "#c79a3a",
        impactLow: "#5fae67",
        nodePast: "#7a8290",
        nodeCurrent: "#c2702f",
        nodeFuture: "#4b4f57",
      },
      borderRadius: {
        // Uncodixfy: no oversized corners — cap the scale
        lg: "8px",
        xl: "8px",
        "2xl": "10px",
        "3xl": "10px",
        full: "9999px",
      },
    },
  },
  plugins: [],
};
