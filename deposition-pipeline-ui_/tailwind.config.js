/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'nextpoint-orange': '#F04E24',
        'nextpoint-navy': '#001F3F',
      }
    },
  },
  plugins: [],
}
