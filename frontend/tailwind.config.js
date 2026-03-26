/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg:     '#050505',
        bg2:    '#0a0a0a',
        bg3:    '#111111',
        green:  '#00ff7f',
        green2: '#00cc66',
        green3: '#003d1f',
        red:    '#ff4444',
        muted:  '#555555',
      },
    },
  },
  plugins: [],
}