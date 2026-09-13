/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["'Source Serif 4'", "ui-serif", "Georgia", "serif"],
      },
      colors: {
        paper: {
          DEFAULT: "#FAF9F6",
          raised: "#FFFFFF",
        },
        ink: {
          DEFAULT: "#1B2028",
          muted: "#4B5361",
          faint: "#8B93A1",
        },
        line: {
          DEFAULT: "#E4E1DA",
          soft: "#EDEBE5",
        },
        brand: {
          50: "#EEF5F3",
          100: "#D7E7E2",
          200: "#B0CFC4",
          300: "#84B4A4",
          400: "#5B9784",
          500: "#3D7A67",
          600: "#2E6353",
          700: "#254F44",
          800: "#1E4038",
          900: "#17322D",
        },
        band: {
          good: "#2E6353",
          goodBg: "#EAF3EF",
          mid: "#9A6A16",
          midBg: "#FBF1DF",
          low: "#A03A32",
          lowBg: "#FBEAE8",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(27,32,40,0.04), 0 8px 24px -12px rgba(27,32,40,0.10)",
        raised: "0 2px 6px rgba(27,32,40,0.06), 0 16px 40px -18px rgba(27,32,40,0.16)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both",
        pulseSoft: "pulseSoft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}
