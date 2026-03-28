import { Link } from "react-router-dom";

export function LoginPage() {
  return (
    <main className="login-shell">
      {/* ── Hero Side ───────────────────────────────────────────────────── */}
      <section className="login-hero">
        <div>
          <p className="eyebrow">Digital Director's Desk</p>
          <h1>Ship polished reels with studio-grade control.</h1>
        </div>

        <p>
          This prototype pairs the documented workflow shell with mock project
          data so product, creative, and engineering can align before backend
          integration begins.
        </p>

        <div className="login-points">
          <div className="surface-card">
            <strong>Project orchestration</strong>
            <p>Brief, script, scene, render, and export workspaces — all in one production view.</p>
          </div>
          <div className="surface-card">
            <strong>Composition-aware UI</strong>
            <p>Render monitoring exposes timing, loudness, music continuity, and snapshot checks.</p>
          </div>
          <div className="surface-card">
            <strong>Preset system</strong>
            <p>Reusable voice, look, and motion presets keep visual consistency across projects.</p>
          </div>
          <div className="surface-card">
            <strong>Admin operations</strong>
            <p>Cross-workspace queue health, provider triage, and workspace fleet visibility.</p>
          </div>
        </div>
      </section>

      {/* ── Login Card ──────────────────────────────────────────────────── */}
      <section className="login-card">
        <div>
          <p className="eyebrow">Mock access</p>
          <h2>North Star Studio</h2>
        </div>

        <p>
          Sign in to review the creator workspace, render operations desk, and
          mock admin surfaces.
        </p>

        <div className="login-actions" style={{ flexDirection: "column", gap: "0.75rem" }}>
          <Link
            className="button button--primary"
            to="/app"
            style={{ width: "100%", justifyContent: "center", minHeight: "3rem" }}
          >
            Enter Studio →
          </Link>
          <Link
            className="button button--secondary"
            to="/admin/queue"
            style={{ width: "100%", justifyContent: "center", minHeight: "3rem" }}
          >
            View Admin Queue
          </Link>
        </div>

        {/* Feature pills */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.5rem" }}>
          {["Brief", "Script", "Scenes", "Renders", "Exports", "Billing"].map((f) => (
            <span className="tag-chip" key={f}>{f}</span>
          ))}
        </div>
      </section>
    </main>
  );
}
