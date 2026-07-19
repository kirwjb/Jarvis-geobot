/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // <--- Vital: tells Tailwind to scan React files
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}