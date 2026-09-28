/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#eef5fd',
          100: '#d9e8fa',
          600: '#0e4f8a',
          700: '#0b3d6b',
          800: '#0a2f52',
          900: '#071f38',
        },
        saffron: {
          500: '#e87722',
          600: '#c86414',
        },
      },
      fontFamily: {
        sans: [
          'Public Sans',
          'Inter',
          'Noto Sans Devanagari',
          'system-ui',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
