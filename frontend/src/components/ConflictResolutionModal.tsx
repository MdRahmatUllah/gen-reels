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
    onResolve({ ...clientVersion, version: serverVersion.version });
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content max-w-3xl">
        <h2 className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted">
          Conflict Detected
        </h2>
        <p className="mt-2 text-sm text-secondary">
          Another user has modified this scene since you started editing. Please resolve the
          conflict below.
        </p>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-border-subtle bg-glass p-4">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted">
              Server Version
            </h4>
            <div className="rounded-xl border border-dashed border-border-card bg-card p-3 text-sm text-secondary">
              <p><strong className="text-primary">Shot:</strong> {serverVersion.shotType}</p>
              <p><strong className="text-primary">Motion:</strong> {serverVersion.motion}</p>
              <p><strong className="text-primary">Duration:</strong> {serverVersion.durationSec}s</p>
              <p>
                <strong className="text-primary">Start Prompt:</strong>{" "}
                {serverVersion.startImagePrompt?.substring(0, 40)}...
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-border-subtle bg-glass p-4">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted">
              Your Edits
            </h4>
            <div className="rounded-xl border border-dashed border-border-card bg-card p-3 text-sm text-secondary">
              <p><strong className="text-primary">Shot:</strong> {clientVersion.shotType}</p>
              <p><strong className="text-primary">Motion:</strong> {clientVersion.motion}</p>
              <p><strong className="text-primary">Duration:</strong> {clientVersion.durationSec}s</p>
              <p>
                <strong className="text-primary">Start Prompt:</strong>{" "}
                {clientVersion.startImagePrompt?.substring(0, 40)}...
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button
            className="inline-flex items-center justify-center rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 hover:-translate-y-px hover:border-border-active hover:bg-glass-hover"
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
          <button
            className="inline-flex items-center justify-center rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 hover:-translate-y-px hover:border-border-active hover:bg-glass-hover"
            onClick={handleKeepServer}
            type="button"
          >
            Discard My Edits
          </button>
          <button
            className="inline-flex items-center justify-center rounded-xl bg-accent-gradient px-4 py-2 text-sm font-semibold text-on-accent shadow-sm transition-all duration-200 hover:-translate-y-px hover:shadow-accent"
            onClick={handleForceOverwrite}
            type="button"
          >
            Force Overwrite
          </button>
        </div>
      </div>
    </div>
  );
}
