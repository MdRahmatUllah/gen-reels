import { useEffect, useMemo, useState } from "react";

import { FormField, FormInput } from "../../components/FormField";
import { LoadingPage, PageFrame, SectionCard } from "../../components/ui";
import {
  findCredentialById,
  useCreateProviderCredential,
  useDeleteProviderCredential,
  useProviderCredentials,
  useProviderExecutionPolicy,
  useUpdateProviderCredential,
  useUpdateProviderRoute,
  useValidateProviderCredential,
} from "../../hooks/use-providers";
import {
  getProviderOptionsByGenerationType,
  providerCatalog,
  providerGenerationLabels,
} from "../../lib/provider-catalog";
import { liveGetOllamaModels } from "../../lib/live-api";
import type {
  ProviderCatalogOption,
  ProviderCredentialInput,
  ProviderCredentialRecord,
  ProviderExecutionRoute,
  ProviderGenerationType,
  ProviderModality,
} from "../../types/domain";

type ProviderFormState = {
  name: string;
  generationType: ProviderGenerationType;
  providerKey: string;
  endpoint: string;
  apiVersion: string;
  deployment: string;
  modelName: string;
  voice: string;
  apiKey: string;
  setAsActiveRoute: boolean;
};

const modalityOrder: ProviderModality[] = ["text", "image", "speech", "video", "moderation"];

const hostedDefaults: Record<ProviderModality, string> = {
  text: "azure_openai_text",
  image: "azure_openai_image",
  speech: "azure_openai_speech",
  video: "veo_video",
  moderation: "azure_content_safety",
};

const modalityIcons: Record<ProviderModality, React.ReactNode> = {
  text: (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
    </svg>
  ),
  image: (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
    </svg>
  ),
  speech: (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
    </svg>
  ),
  video: (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
    </svg>
  ),
  moderation: (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  ),
};

function defaultFormState(): ProviderFormState {
  return {
    name: "",
    generationType: "text",
    providerKey: "azure_openai_text",
    endpoint: "",
    apiVersion: "2024-10-21",
    deployment: "",
    modelName: "",
    voice: "",
    apiKey: "",
    setAsActiveRoute: true,
  };
}

function applyProviderFormDefaults(
  current: ProviderFormState,
  option: ProviderCatalogOption | undefined,
): ProviderFormState {
  if (!option?.formDefaults) return current;
  const next = { ...current };
  for (const [key, value] of Object.entries(option.formDefaults)) {
    if (value === undefined) continue;
    if (key === "endpoint") next.endpoint = value;
    else if (key === "apiVersion") next.apiVersion = value;
    else if (key === "deployment") next.deployment = value;
    else if (key === "modelName") next.modelName = value;
    else if (key === "voice") next.voice = value;
    else if (key === "apiKey") next.apiKey = value;
  }
  return next;
}

function modalityFromGenerationType(generationType: ProviderGenerationType, providerKey: string): ProviderModality {
  const option = providerCatalog.find(
    (entry) => entry.generationType === generationType && entry.providerKey === providerKey,
  );
  return option?.modality ?? (generationType === "audio" ? "speech" : generationType);
}

function toFormState(credential: ProviderCredentialRecord): ProviderFormState {
  return {
    name: credential.name,
    generationType: credential.generationType,
    providerKey: credential.providerKey,
    endpoint: credential.endpoint,
    apiVersion: credential.apiVersion,
    deployment: credential.deployment,
    modelName: credential.modelName,
    voice: credential.voice,
    apiKey: "",
    setAsActiveRoute: credential.isActive,
  };
}

function toCredentialInput(form: ProviderFormState): ProviderCredentialInput {
  return {
    name: form.name,
    modality: modalityFromGenerationType(form.generationType, form.providerKey),
    providerKey: form.providerKey,
    endpoint: form.endpoint,
    apiVersion: form.apiVersion,
    deployment: form.deployment,
    modelName: form.modelName,
    voice: form.voice,
    apiKey: form.apiKey,
    setAsActiveRoute: form.setAsActiveRoute,
  };
}

function formatDateShort(value: string | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/* ─── Validation status pill ─────────────────────────────────────────────── */
function ValidationPill({ credential }: { credential: ProviderCredentialRecord }) {
  const { validationStatus } = credential;
  const map: Record<string, { label: string; cls: string }> = {
    valid:       { label: "Validated", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
    invalid:     { label: "Invalid",   cls: "bg-red-500/10 text-red-400 border-red-500/20" },
    unreachable: { label: "Unreachable", cls: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
    unsupported: { label: "N/A", cls: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20" },
    not_validated: { label: "Unverified", cls: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20" },
  };
  const { label, cls } = map[validationStatus] ?? map.not_validated;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${cls}`}>
      {label}
    </span>
  );
}

/* ─── Active route card ──────────────────────────────────────────────────── */
function RouteCard({
  modality,
  route,
  credential,
  isSaving,
  onUseHosted,
}: {
  modality: ProviderModality;
  route: ProviderExecutionRoute;
  credential: ProviderCredentialRecord | undefined;
  isSaving: boolean;
  onUseHosted: () => void;
}) {
  const isHosted = route.mode === "hosted";
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border-card bg-card p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <div className={`flex h-8 w-8 items-center justify-center rounded-lg border text-primary-fg ${
          isHosted ? "border-border-subtle bg-glass" : "border-accent/30 bg-accent/10 text-accent"
        }`}>
          {modalityIcons[modality]}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest text-muted">
            {providerGenerationLabels[route.generationType]}
          </p>
          <p className="text-sm font-semibold text-primary truncate">{route.providerLabel}</p>
        </div>
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
          isHosted
            ? "border-zinc-700 bg-zinc-800/50 text-zinc-400"
            : "border-accent/30 bg-accent/10 text-accent"
        }`}>
          {isHosted ? "Hosted" : "Custom"}
        </span>
      </div>

      {/* Detail */}
      <div className="rounded-xl border border-border-subtle bg-glass px-3 py-2.5 min-h-[44px]">
        {credential ? (
          <div>
            <p className="text-sm font-medium text-primary">{credential.name}</p>
            {credential.modelName && (
              <p className="text-xs text-muted mt-0.5">{credential.modelName}</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted">Platform default</p>
        )}
      </div>

      {!isHosted && (
        <button
          type="button"
          className="btn-ghost text-xs w-full justify-center"
          disabled={isSaving}
          onClick={onUseHosted}
        >
          Switch to hosted
        </button>
      )}
    </div>
  );
}

/* ─── Credential card ────────────────────────────────────────────────────── */
function CredentialCard({
  credential,
  isSaving,
  onEdit,
  onActivate,
  onDeactivate,
  onValidate,
  onDelete,
  isValidating,
}: {
  credential: ProviderCredentialRecord;
  isSaving: boolean;
  onEdit: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
  onValidate: () => void;
  onDelete: () => void;
  isValidating: boolean;
}) {
  return (
    <div className={`rounded-2xl border bg-card shadow-sm transition-all duration-200 ${
      credential.isActive ? "border-accent/40" : "border-border-card"
    }`}>
      {/* Top bar */}
      <div className="flex items-start gap-3 p-4 pb-3">
        <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${
          credential.isActive
            ? "border-accent/30 bg-accent/10 text-accent"
            : "border-border-subtle bg-glass text-primary-fg"
        }`}>
          {modalityIcons[credential.modality as ProviderModality] ?? modalityIcons.text}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-primary">{credential.name}</span>
            {credential.isActive && (
              <span className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-accent">
                <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                Active
              </span>
            )}
          </div>
          <p className="text-xs text-muted mt-0.5">{credential.providerLabel} · {providerGenerationLabels[credential.generationType]}</p>
        </div>
        <ValidationPill credential={credential} />
      </div>

      {/* Metadata grid */}
      <div className="mx-4 mb-3 grid grid-cols-2 gap-2">
        {credential.modelName && (
          <div className="col-span-2 flex items-center gap-2 rounded-lg border border-border-subtle bg-glass px-3 py-2">
            <span className="text-[10px] font-bold uppercase tracking-widest text-muted w-16 shrink-0">Model</span>
            <span className="text-xs font-medium text-primary truncate">{credential.modelName}</span>
          </div>
        )}
        {credential.deployment && (
          <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-glass px-3 py-2">
            <span className="text-[10px] font-bold uppercase tracking-widest text-muted w-16 shrink-0">Deploy</span>
            <span className="text-xs font-medium text-primary truncate">{credential.deployment}</span>
          </div>
        )}
        {credential.endpoint && (
          <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-glass px-3 py-2">
            <span className="text-[10px] font-bold uppercase tracking-widest text-muted w-16 shrink-0">URL</span>
            <span className="text-xs text-secondary truncate">{credential.endpoint}</span>
          </div>
        )}
        <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-glass px-3 py-2">
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted w-16 shrink-0">Secret</span>
          <span className={`text-xs font-medium ${credential.secretConfigured ? "text-emerald-400" : "text-red-400"}`}>
            {credential.secretConfigured ? "Configured" : "Missing"}
          </span>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-glass px-3 py-2">
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted w-16 shrink-0">Used</span>
          <span className="text-xs text-secondary">{formatDateShort(credential.lastUsedAt)}</span>
        </div>
      </div>

      {credential.validationError && (
        <div className="mx-4 mb-3 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2">
          <p className="text-xs text-red-400">{credential.validationError}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 border-t border-border-subtle px-4 py-3 flex-wrap">
        <button
          type="button"
          className="btn-ghost text-xs"
          onClick={onEdit}
        >
          Edit
        </button>

        {credential.isActive ? (
          <button
            type="button"
            className="btn-ghost text-xs"
            style={{ color: "var(--warning-fg, #f59e0b)" }}
            disabled={isSaving}
            onClick={onDeactivate}
          >
            Deactivate
          </button>
        ) : (
          <button
            type="button"
            className="btn-ghost text-xs disabled:opacity-40"
            disabled={!credential.supportsActivation || isSaving}
            onClick={onActivate}
            title={!credential.supportsActivation ? "This provider cannot be activated" : undefined}
          >
            Set Active
          </button>
        )}

        <button
          type="button"
          className="btn-ghost text-xs"
          disabled={isSaving}
          onClick={onValidate}
        >
          {isValidating ? "Validating…" : "Validate"}
        </button>

        <div className="flex-1" />

        <button
          type="button"
          className="btn-ghost text-xs"
          style={{ color: "var(--error-fg)" }}
          disabled={isSaving}
          onClick={onDelete}
        >
          Revoke
        </button>
      </div>
    </div>
  );
}

/* ─── Page ───────────────────────────────────────────────────────────────── */
export function ProviderSettingsPage() {
  const { data: credentials, isLoading: credentialsLoading } = useProviderCredentials();
  const { data: policy, isLoading: policyLoading } = useProviderExecutionPolicy();
  const createCredential = useCreateProviderCredential();
  const updateCredential = useUpdateProviderCredential();
  const deleteCredential = useDeleteProviderCredential();
  const updateRoute = useUpdateProviderRoute();
  const validateCredential = useValidateProviderCredential();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ProviderFormState>(defaultFormState);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaModelsLoading, setOllamaModelsLoading] = useState(false);
  const [ollamaModelsError, setOllamaModelsError] = useState<string | null>(null);

  const providerOptions = useMemo(
    () => getProviderOptionsByGenerationType(form.generationType),
    [form.generationType],
  );
  const selectedProvider =
    providerOptions.find((option) => option.providerKey === form.providerKey) ?? providerOptions[0];

  useEffect(() => {
    if (!selectedProvider && providerOptions[0]) {
      setForm((current) => ({ ...current, providerKey: providerOptions[0].providerKey }));
    }
  }, [providerOptions, selectedProvider]);

  useEffect(() => {
    if (selectedProvider && !selectedProvider.supportsActivation && form.setAsActiveRoute) {
      setForm((current) => ({ ...current, setAsActiveRoute: false }));
    }
  }, [form.setAsActiveRoute, selectedProvider]);

  const isLoading = credentialsLoading || policyLoading;
  const isSaving =
    createCredential.isPending ||
    updateCredential.isPending ||
    deleteCredential.isPending ||
    updateRoute.isPending ||
    validateCredential.isPending;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const resolvedName =
      form.providerKey === "ollama_text"
        ? `Ollama${form.modelName ? ` (${form.modelName})` : ""}`
        : form.name;
    const payload = {
      ...toCredentialInput({ ...form, name: resolvedName }),
      setAsActiveRoute: Boolean(selectedProvider?.supportsActivation && form.setAsActiveRoute),
    };
    if (editingId) {
      await updateCredential.mutateAsync({ credentialId: editingId, input: payload });
    } else {
      await createCredential.mutateAsync(payload);
    }
    setEditingId(null);
    setForm(defaultFormState());
  }

  async function handleUseHostedDefault(modality: ProviderModality) {
    await updateRoute.mutateAsync({
      modality,
      providerKey: hostedDefaults[modality],
      credentialId: null,
      mode: "hosted",
    });
  }

  async function handleMakeActive(credential: ProviderCredentialRecord) {
    await updateRoute.mutateAsync({
      modality: credential.modality,
      providerKey: credential.providerKey,
      credentialId: credential.id,
      mode: "byo",
    });
  }

  async function handleFetchOllamaModels() {
    setOllamaModelsError(null);
    setOllamaModelsLoading(true);
    try {
      const models = await liveGetOllamaModels(form.endpoint || "http://localhost:11434");
      setOllamaModels(models);
      if (models.length > 0 && !form.modelName) {
        setForm((current) => ({ ...current, modelName: models[0] }));
      }
    } catch (err: any) {
      setOllamaModelsError(err?.message ?? "Failed to fetch models from Ollama.");
    } finally {
      setOllamaModelsLoading(false);
    }
  }

  if (isLoading || !credentials || !policy) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Settings"
      title="Providers"
      description="Configure AI provider credentials and control which backend route handles each generation type."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Security">
            <p className="text-sm leading-relaxed text-secondary">
              API keys are encrypted at rest and never returned to the browser. Leave the key field blank when editing to keep the existing secret.
            </p>
          </SectionCard>
          <SectionCard title="Supported Providers">
            <div className="flex flex-col gap-2 text-sm text-secondary">
              <p><span className="font-medium text-primary">Text</span> — Azure OpenAI, Ollama</p>
              <p><span className="font-medium text-primary">Image</span> — Azure OpenAI, Stability AI</p>
              <p><span className="font-medium text-primary">Speech</span> — Azure OpenAI, ElevenLabs</p>
              <p><span className="font-medium text-primary">Video</span> — Runway, Kling (storage)</p>
              <p><span className="font-medium text-primary">Moderation</span> — Azure Content Safety</p>
            </div>
          </SectionCard>
        </div>
      }
    >
      {/* ── Active Routes ───────────────────────────────────────────────────── */}
      <SectionCard
        title="Active Routes"
        subtitle="The provider route currently used for each generation type. Switch between your saved credentials or fall back to the hosted platform default."
      >
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {modalityOrder.map((modality) => {
            const route = policy[modality];
            const credential = findCredentialById(credentials, route.credentialId);
            return (
              <RouteCard
                key={modality}
                modality={modality}
                route={route}
                credential={credential}
                isSaving={isSaving}
                onUseHosted={() => handleUseHostedDefault(modality)}
              />
            );
          })}
        </div>
      </SectionCard>

      {/* ── Add / Edit Credential ───────────────────────────────────────────── */}
      <SectionCard
        title={editingId ? "Edit Credential" : "Add Credential"}
        subtitle={
          editingId
            ? "Update the provider details below. Leave the API key blank to keep your existing secret."
            : "Pick a generation type, choose your provider, fill in the connection details, and save."
        }
      >
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          {/* Type + provider selects */}
          <div className="grid gap-4 md:grid-cols-2">
            <FormField htmlFor="generationType" label="Generation Type">
              <select
                id="generationType"
                className="w-full rounded-xl border border-border-card bg-glass px-3.5 py-2.5 text-sm text-primary outline-none transition-all hover:border-border-active focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
                value={form.generationType}
                onChange={(event) => {
                  const generationType = event.target.value as ProviderGenerationType;
                  const nextOptions = getProviderOptionsByGenerationType(generationType);
                  const first = nextOptions[0];
                  setForm((current) => {
                    if (editingId) {
                      return { ...current, generationType, providerKey: first?.providerKey ?? current.providerKey };
                    }
                    const base = { ...current, generationType, providerKey: first?.providerKey ?? current.providerKey };
                    return applyProviderFormDefaults(base, first);
                  });
                }}
              >
                {Object.entries(providerGenerationLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </FormField>

            <FormField htmlFor="providerKey" label="Provider">
              <select
                id="providerKey"
                className="w-full rounded-xl border border-border-card bg-glass px-3.5 py-2.5 text-sm text-primary outline-none transition-all hover:border-border-active focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
                value={selectedProvider?.providerKey ?? form.providerKey}
                onChange={(event) => {
                  const providerKey = event.target.value;
                  const option = providerOptions.find((o) => o.providerKey === providerKey);
                  setOllamaModels([]);
                  setOllamaModelsError(null);
                  setForm((current) => {
                    if (editingId) return { ...current, providerKey };
                    return applyProviderFormDefaults({ ...current, providerKey }, option);
                  });
                }}
              >
                {providerOptions.map((option) => (
                  <option key={option.providerKey} value={option.providerKey}>
                    {option.providerLabel}{option.supportsActivation ? "" : " (storage only)"}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          {/* Credential name */}
          {form.providerKey !== "ollama_text" && (
            <FormInput
              id="credentialName"
              label="Credential Name"
              value={form.name}
              onChange={(value) => setForm((current) => ({ ...current, name: value }))}
              placeholder="e.g. Azure OpenAI Primary"
            />
          )}

          {/* Provider description */}
          {selectedProvider && (
            <div className="flex items-start gap-3 rounded-xl border border-border-subtle bg-glass px-4 py-3">
              <div className="mt-0.5 text-muted shrink-0">{modalityIcons[selectedProvider.modality as ProviderModality] ?? modalityIcons.text}</div>
              <p className="text-sm text-secondary leading-relaxed">{selectedProvider.description}</p>
            </div>
          )}

          {/* Provider fields */}
          <div className="grid gap-4 md:grid-cols-2">
            {selectedProvider?.fields.map((field) => {
              if (form.providerKey === "ollama_text" && field.key === "modelName") {
                return (
                  <FormField
                    key={field.key}
                    htmlFor="modelName"
                    label={field.label}
                    error={ollamaModelsError ?? undefined}
                    help={field.help}
                  >
                    <div className="flex gap-2">
                      {ollamaModels.length > 0 ? (
                        <select
                          id="modelName"
                          className="flex-1 rounded-xl border border-border-card bg-glass px-3.5 py-2.5 text-sm text-primary outline-none transition-all hover:border-border-active focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
                          value={form.modelName}
                          onChange={(e) => setForm((current) => ({ ...current, modelName: e.target.value }))}
                        >
                          {ollamaModels.map((m) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          id="modelName"
                          className="flex-1 rounded-xl border border-border-card bg-glass px-3.5 py-2.5 text-sm text-primary outline-none transition-all hover:border-border-active focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)] placeholder:text-muted"
                          type="text"
                          value={form.modelName}
                          onChange={(e) => setForm((current) => ({ ...current, modelName: e.target.value }))}
                          placeholder={field.placeholder}
                        />
                      )}
                      <button
                        type="button"
                        className="btn-ghost text-sm shrink-0 disabled:opacity-50"
                        disabled={ollamaModelsLoading}
                        onClick={handleFetchOllamaModels}
                      >
                        {ollamaModelsLoading ? "Loading…" : "Get Models"}
                      </button>
                    </div>
                  </FormField>
                );
              }
              return (
                <FormInput
                  key={field.key}
                  id={field.key}
                  label={field.label}
                  type={field.secret ? "password" : "text"}
                  value={form[field.key as keyof ProviderFormState] as string}
                  onChange={(value) => setForm((current) => ({ ...current, [field.key]: value }))}
                  placeholder={field.placeholder}
                  help={
                    [field.key === "apiKey" && editingId ? "Leave blank to keep the existing API key." : "", field.help || ""]
                      .filter(Boolean).join(" ") || undefined
                  }
                />
              );
            })}
          </div>

          {/* Set as active route toggle */}
          <label className={`flex items-start gap-3 rounded-xl border px-4 py-3.5 cursor-pointer transition-colors ${
            form.setAsActiveRoute && selectedProvider?.supportsActivation
              ? "border-accent/30 bg-accent/5"
              : "border-border-subtle bg-glass"
          } ${!selectedProvider?.supportsActivation ? "opacity-50 cursor-not-allowed" : ""}`}>
            <input
              type="checkbox"
              checked={form.setAsActiveRoute}
              disabled={!selectedProvider?.supportsActivation}
              onChange={(e) => setForm((current) => ({ ...current, setAsActiveRoute: e.target.checked }))}
              className="mt-0.5 accent-[var(--accent)]"
            />
            <div>
              <p className="text-sm font-medium text-primary">
                Make this the active route after saving
              </p>
              <p className="text-xs text-muted mt-0.5">
                {!selectedProvider?.supportsActivation
                  ? "This provider can be stored but cannot be activated for live routing."
                  : `Will route all ${providerGenerationLabels[form.generationType].toLowerCase()} generation through this credential.`}
              </p>
            </div>
          </label>

          {/* Submit */}
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSaving || (form.providerKey !== "ollama_text" && !form.name.trim())}
              type="submit"
            >
              {editingId
                ? updateCredential.isPending ? "Saving…" : "Save changes"
                : createCredential.isPending ? "Adding…" : "Add credential"}
            </button>
            {editingId && (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => { setEditingId(null); setForm(defaultFormState()); }}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </SectionCard>

      {/* ── Configured Credentials ─────────────────────────────────────────── */}
      <SectionCard
        title="Configured Credentials"
        subtitle={`${credentials.length} saved ${credentials.length === 1 ? "credential" : "credentials"}`}
      >
        {credentials.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border-subtle bg-glass text-muted">
              <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-primary">No credentials yet</p>
              <p className="text-sm text-muted mt-1">Add your first provider credential above to get started.</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {credentials.map((credential) => (
              <CredentialCard
                key={credential.id}
                credential={credential}
                isSaving={isSaving}
                isValidating={validateCredential.isPending}
                onEdit={() => { setEditingId(credential.id); setForm(toFormState(credential)); }}
                onActivate={() => handleMakeActive(credential)}
                onDeactivate={() => handleUseHostedDefault(credential.modality)}
                onValidate={() => validateCredential.mutate(credential.id)}
                onDelete={() => deleteCredential.mutate(credential.id)}
              />
            ))}
          </div>
        )}
      </SectionCard>
    </PageFrame>
  );
}
