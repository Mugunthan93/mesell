/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fff6ed",
          100: "#ffead4",
          500: "#ed6c1f",
          600: "#d65510",
          700: "#a8400b",
        },
      },
    },
  },
  plugins: [],
};
