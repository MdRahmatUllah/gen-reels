/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          850: '#151f32',
          900: '#0f172a',
          950: '#0b0f19',
        },
        primary: {
          500: '#3b82f6',
          600: '#2563eb',
        },
        accent: {
          cyan: '#22d3ee',
          violet: '#a78bfa',
          coral: '#f43f5e',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s infinite',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0px rgba(34, 211, 238, 0)' },
          '50%': { boxShadow: '0 0 15px rgba(34, 211, 238, 0.5)' },
        }
      }
    },
  },
  plugins: [],
}
