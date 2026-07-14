/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#0A0E1A',
          card: '#161F30',
          border: '#233554',
          text: '#F3F4F6',
          muted: '#9CA3AF',
          accent: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          info: '#3B82F6'
        }
      }
    },
  },
  plugins: [],
}
