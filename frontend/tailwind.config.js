/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        base: "var(--bg-base)",
        surface: "var(--bg-surface)",
        card: "var(--bg-card)",
        "card-raised": "var(--bg-card-raised)",
        "card-hero": "var(--bg-card-hero)",
        glass: "var(--bg-glass)",
        "glass-hover": "var(--bg-glass-hover)",
        overlay: "var(--bg-overlay)",
        accent: "var(--accent)",
        "accent-dim": "var(--accent-dim)",
        "accent-bright": "var(--accent-bright)",
        "accent-secondary": "var(--accent-secondary)",
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        "on-accent": "var(--text-on-accent)",
        border: {
          subtle: "var(--border-subtle)",
          card: "var(--border-card)",
          active: "var(--border-active)",
        },
        success: "var(--success-fg)",
        "success-bg": "var(--success-bg)",
        "success-glow": "var(--success-glow)",
        warning: "var(--warning-fg)",
        "warning-bg": "var(--warning-bg)",
        error: "var(--error-fg)",
        "error-bg": "var(--error-bg)",
        neutral: "var(--neutral-fg)",
        "neutral-bg": "var(--neutral-bg)",
        "primary-bg": "var(--primary-bg)",
        "primary-fg": "var(--primary-fg)",
      },
      backgroundImage: {
        "accent-gradient": "var(--accent-gradient)",
        "accent-gradient-v": "var(--accent-gradient-v)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        heading: ["Manrope", "Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        accent: "var(--shadow-accent)",
        card: "var(--shadow-card)",
      },
      animation: {
        "fade-in-up": "fadeInUp 0.3s ease-out",
        "pulse-glow": "pulseGlow 2s infinite",
        "rise-in": "rise-in 480ms cubic-bezier(0.2, 0.85, 0.2, 1) both",
      },
      keyframes: {
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0px var(--accent-glow)" },
          "50%": { boxShadow: "0 0 15px var(--accent-glow)" },
        },
        "rise-in": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
