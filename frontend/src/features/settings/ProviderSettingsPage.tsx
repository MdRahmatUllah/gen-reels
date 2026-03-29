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
        <div className="flex flex-col gap-4">
          <SectionCard title="Data Security">
            <p className="text-sm text-slate-300 leading-relaxed">
              Keys are encrypted at rest using envelope encryption. They are strictly used server-side during generation orchestration and are never exposed to the frontend after initial submission.
            </p>
          </SectionCard>
        </div>
      }
    >
      <SectionCard title="Configured Keys" subtitle="Secured keys currently available for routing in this workspace.">
        <div className="overflow-x-auto rounded-lg border border-slate-800/60 bg-slate-900/40">
          <table className="w-full text-left text-sm text-slate-300">
            <thead>
              <tr>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Provider</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Key Prefix</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Added On</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Status</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys?.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-slate-500">No custom keys configured. Using default platform pools.</td>
                </tr>
              )}
              {keys?.map((k) => (
                <tr key={k.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="border-b border-slate-800/50 px-4 py-3 capitalize">{k.provider}</td>
                  <td className="border-b border-slate-800/50 px-4 py-3 font-mono text-slate-400 text-xs">{k.keyPrefix}</td>
                  <td className="border-b border-slate-800/50 px-4 py-3">{new Date(k.createdAt).toLocaleDateString()}</td>
                  <td className="border-b border-slate-800/50 px-4 py-3"><StatusBadge status="active" /></td>
                  <td className="border-b border-slate-800/50 px-4 py-3">
                    <button type="button" className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md transition-colors border border-slate-700/50" onClick={() => deleteKey.mutate(k.id)}>Revoke</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard title="Add New Key" subtitle="Keys are heavily encrypted and can never be viewed again once saved.">
        <form onSubmit={handleAdd} className="flex flex-col gap-4 max-w-md">
          <div className="flex flex-col gap-1.5 w-full">
            <label className="text-xs font-semibold text-slate-300" htmlFor="provider">Provider</label>
            <select id="provider" className="w-full rounded-md border border-slate-800/80 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none hover:border-slate-700/80 focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-all" value={provider} onChange={(e) => setProvider(e.target.value as any)}>
              <option value="openai">OpenAI</option>
              <option value="stability">Stability AI</option>
              <option value="elevenlabs">ElevenLabs</option>
              <option value="runway">RunwayML</option>
            </select>
          </div>
          <FormInput id="key" label="API Key" type="password" value={key} onChange={setKey} placeholder="sk-..." />
          <div className="mt-2">
            <button type="submit" className="w-full rounded-md bg-accent-cyan px-4 py-2 text-sm font-semibold text-slate-950 shadow-md hover:bg-accent-cyan/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed" disabled={!key || addKey.isPending}>
              {addKey.isPending ? "Encrypting and Saving..." : "Add Provider Key"}
            </button>
          </div>
        </form>
      </SectionCard>
    </PageFrame>
  );
}
