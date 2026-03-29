import { useState } from "react";
import { PageFrame, SectionCard, StatusBadge, LoadingPage } from "../../components/ui";
import { FormInput } from "../../components/FormField";
import { useProviderKeys, useAddProviderKey, useDeleteProviderKey } from "../../hooks/use-providers";
import type { ProviderKey } from "../../types/domain";

export function ProviderSettingsPage() {
  const { data: keys, isLoading } = useProviderKeys();
  const addKey = useAddProviderKey();
  const deleteKey = useDeleteProviderKey();

  const [provider, setProvider] = useState<ProviderKey["provider"]>("openai");
  const [key, setKey] = useState("");

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key.trim()) return;
    await addKey.mutateAsync({ provider, key });
    setKey("");
  };

  if (isLoading) return <LoadingPage />;

  return (
    <PageFrame 
      eyebrow="Settings" 
      title="API Keys & Providers" 
      description="Manage Bring-Your-Own API credentials for hybrid rendering."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Data Security">
            <p className="body-copy">
              Keys are encrypted at rest using envelope encryption. They are strictly used server-side during generation orchestration and are never exposed to the frontend after initial submission.
            </p>
          </SectionCard>
        </div>
      }
    >
      <SectionCard title="Configured Keys" subtitle="Secured keys currently available for routing in this workspace.">
        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Key Prefix</th>
                <th>Added On</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys?.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", color: "var(--color-ink-lighter)" }}>No custom keys configured. Using default platform pools.</td>
                </tr>
              )}
              {keys?.map((k) => (
                <tr key={k.id}>
                  <td style={{ textTransform: "capitalize" }}>{k.provider}</td>
                  <td style={{ fontFamily: "monospace", color: "var(--color-ink-lighter)" }}>{k.keyPrefix}</td>
                  <td>{new Date(k.createdAt).toLocaleDateString()}</td>
                  <td><StatusBadge status="active" /></td>
                  <td>
                    <button type="button" className="button button--secondary" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => deleteKey.mutate(k.id)}>Revoke</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard title="Add New Key" subtitle="Keys are heavily encrypted and can never be viewed again once saved.">
        <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: "16px", maxWidth: "400px" }}>
          <div className="form-field">
            <label className="field-label" htmlFor="provider">Provider</label>
            <select id="provider" className="field-input" value={provider} onChange={(e) => setProvider(e.target.value as any)}>
              <option value="openai">OpenAI</option>
              <option value="stability">Stability AI</option>
              <option value="elevenlabs">ElevenLabs</option>
              <option value="runway">RunwayML</option>
            </select>
          </div>
          <FormInput id="key" label="API Key" type="password" value={key} onChange={setKey} placeholder="sk-..." />
          <div>
            <button type="submit" className="button button--primary" disabled={!key || addKey.isPending}>
              {addKey.isPending ? "Encrypting and Saving..." : "Add Provider Key"}
            </button>
          </div>
        </form>
      </SectionCard>
    </PageFrame>
  );
}
