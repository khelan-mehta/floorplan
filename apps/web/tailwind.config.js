/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}', '../../packages/ui/src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0f1115',
        panel: '#161922',
        'panel-2': '#1f2430',
        line: '#2a2f3a',
        fg: '#e6e6e6',
        muted: '#9aa0a6',
        accent: '#3b82f6',
        ok: '#2ea043',
        warn: '#d29922',
        danger: '#d1242f',
      },
    },
  },
  plugins: [],
};
