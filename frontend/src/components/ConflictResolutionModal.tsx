import type { ScenePlan } from "../types/domain";

export function ConflictResolutionModal({
  serverVersion,
  clientVersion,
  onResolve,
  onCancel,
}: {
  serverVersion: ScenePlan;
  clientVersion: ScenePlan;
  onResolve: (resolvedVersion: ScenePlan) => void;
  onCancel: () => void;
}) {
  const handleKeepServer = () => {
    onResolve(serverVersion);
  };

  const handleForceOverwrite = () => {
    // Provide clientVersion, but bumped to match the server so it succeeds
    onResolve({ ...clientVersion, version: serverVersion.version });
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content" style={{ maxWidth: "600px", zIndex: 999 }}>
        <h2 className="section-heading">Conflict Detected</h2>
        <p className="body-copy">
          Another user has modified this scene since you started editing.
          Please resolve the conflict below.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "16px" }}>
          <div className="surface-card" style={{ background: "var(--color-background-raised)", padding: "16px", border: "none" }}>
            <h4 style={{ fontSize: "12px", color: "var(--color-ink-lighter)", marginBottom: "8px" }}>Server Version</h4>
            <div style={{ fontSize: "12px", background: "var(--color-background)", padding: "8px", border: "1px dashed var(--color-border)", borderRadius: "4px" }}>
              <p><strong>Shot:</strong> {serverVersion.shotType}</p>
              <p><strong>Motion:</strong> {serverVersion.motion}</p>
              <p><strong>Duration:</strong> {serverVersion.durationSec}s</p>
              <p><strong>Start Prompt:</strong> {serverVersion.startImagePrompt?.substring(0, 40)}...</p>
            </div>
          </div>
          <div className="surface-card" style={{ background: "var(--color-background-raised)", padding: "16px", border: "none" }}>
            <h4 style={{ fontSize: "12px", color: "var(--color-ink-lighter)", marginBottom: "8px" }}>Your Edits</h4>
            <div style={{ fontSize: "12px", background: "var(--color-background)", padding: "8px", border: "1px dashed var(--color-border)", borderRadius: "4px", opacity: 0.9 }}>
              <p><strong>Shot:</strong> {clientVersion.shotType}</p>
              <p><strong>Motion:</strong> {clientVersion.motion}</p>
              <p><strong>Duration:</strong> {clientVersion.durationSec}s</p>
              <p><strong>Start Prompt:</strong> {clientVersion.startImagePrompt?.substring(0, 40)}...</p>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "24px" }}>
          <button className="button button--secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className="button button--secondary" onClick={handleKeepServer}>
            Discard My Edits (Keep Server)
          </button>
          <button className="button button--primary" onClick={handleForceOverwrite}>
            Force Overwrite Server
          </button>
        </div>
      </div>
    </div>
  );
}
