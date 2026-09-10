import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        base: {
          900: '#0a0c0e',
          800: '#111418',
          700: '#181c22',
          600: '#1f2733',
          500: '#2a3441',
        },
        border: {
          DEFAULT: '#1f2937',
          subtle: '#131820',
          focus: '#38bdf8',
        },
        text: {
          primary: '#e8eaed',
          secondary: '#8b949e',
          muted: '#4b5563',
        },
        amber: {
          DEFAULT: '#f59e0b',
          dim: '#78450a',
          glow: 'rgba(245,158,11,0.15)',
        },
        sky: {
          DEFAULT: '#38bdf8',
          dim: '#0c3b5c',
          glow: 'rgba(56,189,248,0.15)',
        },
        rose: {
          DEFAULT: '#f43f5e',
          dim: '#5c1a2a',
          glow: 'rgba(244,63,94,0.12)',
        },
        emerald: {
          DEFAULT: '#10b981',
          dim: '#064e3b',
          glow: 'rgba(16,185,129,0.12)',
        },
        slate: {
          DEFAULT: '#64748b',
          dim: '#1e293b',
        },
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'pulse-subtle': 'pulse 3s ease-in-out infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
