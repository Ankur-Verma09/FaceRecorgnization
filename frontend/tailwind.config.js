/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: "#0f172a",
        cardBg: "rgba(30, 41, 59, 0.7)",
        cardBorder: "rgba(255, 255, 255, 0.1)",
        accentBlue: "#3b82f6",
        accentPurple: "#8b5cf6",
        accentCyan: "#06b6d4"
      }
    },
  },
  plugins: [],
}
