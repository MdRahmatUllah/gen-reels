import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { FormInput } from "../components/FormField";

export function LoginPage() {
  const { login, error, isLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("alex@studio.io");
  const [password, setPassword] = useState("password123");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ email, password });
      navigate("/app", { replace: true });
    } catch {
      // error is set in auth context
    }
  };

  return (
    <div className="login-shell">
      <div className="login-card surface-card">
        <div className="brand-lockup" style={{ marginBottom: "2rem" }}>
          <div className="brand-mark" aria-hidden="true" />
          <div>
            <p className="eyebrow">Production Atelier</p>
            <h1>Reels Generation Studio</h1>
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
            placeholder="••••••••"
            disabled={isLoading}
          />

          {error ? (
            <div className="alert-item" style={{ marginBottom: "1rem" }}>
              <span className="tone-pill tone-pill--error" />
              <div>
                <strong>Login failed</strong>
                <p>{error}</p>
              </div>
            </div>
          ) : null}

          <button
            type="submit"
            className="button button--primary"
            disabled={isLoading}
            style={{ width: "100%", justifyContent: "center" }}
          >
            {isLoading ? "Signing in…" : "Sign in"}
          </button>

          <p className="body-copy" style={{ textAlign: "center", marginTop: "1rem", opacity: 0.6, fontSize: "0.75rem" }}>
            Demo: alex@studio.io / password123
          </p>
        </form>
      </div>
    </div>
  );
}
