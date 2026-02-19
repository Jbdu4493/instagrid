/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: "#0e1117",
        card: "#262730",
        border: "#41424b",
      }
    },
  },
  plugins: [],
}

