import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { FormInput } from "../components/FormField";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";

export function LoginPage() {
  const { login, error, isLoading } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [email, setEmail] = useState("alex@studio.io");
  const [password, setPassword] = useState("password123");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await login({ email, password });
      navigate("/app", { replace: true });
    } catch {
      // Error state is managed by the auth provider.
    }
  };

  return (
    <div className="login-shell">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-base [background-image:radial-gradient(circle_at_top_left,rgba(47,109,246,0.16),transparent_26%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.12),transparent_22%)] dark:[background-image:radial-gradient(circle_at_top_left,rgba(91,140,255,0.24),transparent_26%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.14),transparent_22%),linear-gradient(180deg,rgba(8,17,31,0.9),rgba(8,17,31,1))]"
      />

      <button
        className="absolute right-4 top-4 inline-flex items-center rounded-full border border-border-subtle bg-glass px-3 py-1.5 text-xs font-semibold text-primary transition-all duration-200 hover:border-border-active hover:bg-glass-hover"
        onClick={toggleTheme}
        type="button"
      >
        {theme === "dark" ? "Light mode" : "Dark mode"}
      </button>

      <div className="login-card surface-card--hero">
        <div className="mb-8 flex items-center gap-3 border-b border-border-subtle pb-4">
          <div className="brand-mark" aria-hidden="true" />
          <div>
            <p className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted">Production Atelier</p>
            <h1 className="font-heading text-2xl font-bold text-primary">Reels Generation Studio</h1>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <FormInput
            id="login-email"
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="email@studio.io"
            disabled={isLoading}
          />

          <FormInput
            id="login-password"
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="password123"
            disabled={isLoading}
          />

          {error ? (
            <div className="rounded-2xl border border-error/20 bg-error-bg p-4">
              <strong className="text-sm font-semibold text-error">Login failed</strong>
              <p className="mt-1 text-sm text-secondary">{error}</p>
            </div>
          ) : null}

          <button
            type="submit"
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent-gradient px-4 py-3 text-sm font-semibold text-on-accent shadow-sm transition-all duration-200 hover:-translate-y-px hover:shadow-accent disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isLoading}
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </button>

          <p className="text-center text-xs text-muted">Demo: alex@studio.io / password123</p>
        </form>
      </div>
    </div>
  );
}
