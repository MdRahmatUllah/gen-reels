import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const THEME_STORAGE_KEY = "reels-generation-theme";

const lightThemeVars = {
  "--bg-base": "#f4f7fb",
  "--bg-surface": "#ffffff",
  "--bg-card": "#ffffff",
  "--bg-card-raised": "#f8fafc",
  "--bg-card-hero": "#eef4ff",
  "--bg-glass": "rgba(15, 23, 42, 0.04)",
  "--bg-glass-hover": "rgba(15, 23, 42, 0.08)",
  "--bg-overlay": "rgba(255, 255, 255, 0.82)",
  "--accent": "#2f6df6",
  "--accent-dim": "#2557c8",
  "--accent-bright": "#5a8fff",
  "--accent-secondary": "#0ea5e9",
  "--accent-glow": "rgba(47, 109, 246, 0.24)",
  "--accent-glow-sm": "rgba(47, 109, 246, 0.14)",
  "--accent-gradient": "linear-gradient(135deg, #2f6df6 0%, #0ea5e9 100%)",
  "--accent-gradient-v": "linear-gradient(180deg, #2f6df6 0%, #0ea5e9 100%)",
  "--text-primary": "#0f172a",
  "--text-secondary": "#475569",
  "--text-muted": "#64748b",
  "--text-on-accent": "#ffffff",
  "--border-subtle": "rgba(15, 23, 42, 0.08)",
  "--border-card": "rgba(15, 23, 42, 0.1)",
  "--border-active": "rgba(47, 109, 246, 0.28)",
  "--success-bg": "rgba(16, 185, 129, 0.1)",
  "--success-fg": "#059669",
  "--success-glow": "rgba(16, 185, 129, 0.18)",
  "--warning-bg": "rgba(245, 158, 11, 0.14)",
  "--warning-fg": "#d97706",
  "--error-bg": "rgba(239, 68, 68, 0.1)",
  "--error-fg": "#dc2626",
  "--neutral-bg": "rgba(148, 163, 184, 0.12)",
  "--neutral-fg": "#475569",
  "--primary-bg": "rgba(47, 109, 246, 0.1)",
  "--primary-fg": "#2563eb",
  "--shadow-sm": "0 1px 3px rgba(15, 23, 42, 0.08)",
  "--shadow-md": "0 10px 30px rgba(15, 23, 42, 0.1)",
  "--shadow-lg": "0 24px 60px rgba(15, 23, 42, 0.14)",
  "--shadow-accent": "0 12px 32px rgba(47, 109, 246, 0.18)",
  "--shadow-card": "0 1px 0 rgba(15, 23, 42, 0.06), 0 16px 40px rgba(15, 23, 42, 0.08)",
} as const;

const darkThemeVars = {
  "--bg-base": "#08111f",
  "--bg-surface": "#0f172a",
  "--bg-card": "#132033",
  "--bg-card-raised": "#18283f",
  "--bg-card-hero": "#193150",
  "--bg-glass": "rgba(255, 255, 255, 0.05)",
  "--bg-glass-hover": "rgba(255, 255, 255, 0.08)",
  "--bg-overlay": "rgba(8, 17, 31, 0.82)",
  "--accent": "#5b8cff",
  "--accent-dim": "#3f70ea",
  "--accent-bright": "#93b5ff",
  "--accent-secondary": "#38bdf8",
  "--accent-glow": "rgba(91, 140, 255, 0.32)",
  "--accent-glow-sm": "rgba(91, 140, 255, 0.18)",
  "--accent-gradient": "linear-gradient(135deg, #5b8cff 0%, #38bdf8 100%)",
  "--accent-gradient-v": "linear-gradient(180deg, #5b8cff 0%, #38bdf8 100%)",
  "--text-primary": "#edf4ff",
  "--text-secondary": "#bfd0e6",
  "--text-muted": "#84a0c0",
  "--text-on-accent": "#ffffff",
  "--border-subtle": "rgba(255, 255, 255, 0.08)",
  "--border-card": "rgba(255, 255, 255, 0.12)",
  "--border-active": "rgba(91, 140, 255, 0.32)",
  "--success-bg": "rgba(52, 211, 153, 0.14)",
  "--success-fg": "#34d399",
  "--success-glow": "rgba(52, 211, 153, 0.22)",
  "--warning-bg": "rgba(251, 191, 36, 0.16)",
  "--warning-fg": "#fbbf24",
  "--error-bg": "rgba(248, 113, 113, 0.16)",
  "--error-fg": "#f87171",
  "--neutral-bg": "rgba(148, 163, 184, 0.16)",
  "--neutral-fg": "#94a3b8",
  "--primary-bg": "rgba(91, 140, 255, 0.16)",
  "--primary-fg": "#9dbbff",
  "--shadow-sm": "0 8px 24px rgba(2, 8, 23, 0.35)",
  "--shadow-md": "0 18px 40px rgba(2, 8, 23, 0.42)",
  "--shadow-lg": "0 28px 80px rgba(2, 8, 23, 0.55)",
  "--shadow-accent": "0 16px 40px rgba(91, 140, 255, 0.24)",
  "--shadow-card": "0 1px 0 rgba(255, 255, 255, 0.06), 0 18px 50px rgba(2, 8, 23, 0.4)",
} as const;

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getInitialTheme(): Theme {
  if (typeof window === "undefined") {
    return "dark";
  }

  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const vars = theme === "dark" ? darkThemeVars : lightThemeVars;

  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;

  Object.entries(vars).forEach(([name, value]) => {
    root.style.setProperty(name, value);
  });
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      setTheme,
      toggleTheme: () => setTheme((current) => (current === "dark" ? "light" : "dark")),
    }),
    [theme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }

  return context;
}
