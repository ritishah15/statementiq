/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#172B4D',
          dark: '#0e1b33',
          light: '#253858',
          subtle: '#344563'
        },
        teal: {
          DEFAULT: '#0D9488',
          hover: '#0f766e',
          light: '#14b8a6',
          soft: '#e6fffa',
          dim: '#d5e7df'
        },
        surface: {
          DEFAULT: '#f9f9ff',
          card: '#ffffff',
          subtle: '#f1f5f9',
          border: '#e2e8f0',
          hover: '#f8fafc'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
