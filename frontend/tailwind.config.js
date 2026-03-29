/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        base: 'var(--bg-base)',
        surface: 'var(--bg-surface)',
        card: {
          DEFAULT: 'var(--bg-card)',
          raised: 'var(--bg-card-raised)',
          hero: 'var(--bg-card-hero)',
        },
        glass: {
          DEFAULT: 'var(--bg-glass)',
          hover: 'var(--bg-glass-hover)',
        },
        overlay: 'var(--bg-overlay)',
        accent: {
          DEFAULT: 'var(--accent)',
          dim: 'var(--accent-dim)',
          bright: 'var(--accent-bright)',
          secondary: 'var(--accent-secondary)',
          glow: 'var(--accent-glow)',
          'glow-sm': 'var(--accent-glow-sm)',
        },
        primary: {
          text: 'var(--text-primary)',
          DEFAULT: 'var(--primary-bg)',
          fg: 'var(--primary-fg)',
        },
        secondary: {
          text: 'var(--text-secondary)',
        },
        muted: {
          text: 'var(--text-muted)',
        },
        on: {
          accent: 'var(--text-on-accent)',
        },
        border: {
          subtle: 'var(--border-subtle)',
          card: 'var(--border-card)',
          active: 'var(--border-active)',
        },
        success: {
          bg: 'var(--success-bg)',
          fg: 'var(--success-fg)',
          glow: 'var(--success-glow)',
        },
        warning: {
          bg: 'var(--warning-bg)',
          fg: 'var(--warning-fg)',
        },
        error: {
          bg: 'var(--error-bg)',
          fg: 'var(--error-fg)',
        },
        neutral: {
          bg: 'var(--neutral-bg)',
          fg: 'var(--neutral-fg)',
        },
      },
      backgroundImage: {
        'accent-gradient': 'var(--accent-gradient)',
        'accent-gradient-v': 'var(--accent-gradient-v)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        heading: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        accent: 'var(--shadow-accent)',
        card: 'var(--shadow-card)',
      },
      borderRadius: {
        sm: 'var(--r-sm)',
        md: 'var(--r-md)',
        lg: 'var(--r-lg)',
        xl: 'var(--r-xl)',
        full: 'var(--r-full)',
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s infinite',
        'rise-in': 'rise-in 480ms cubic-bezier(0.2, 0.85, 0.2, 1) both',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0px var(--accent-glow)' },
          '50%': { boxShadow: '0 0 15px var(--accent-glow)' },
        },
        'rise-in': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}
