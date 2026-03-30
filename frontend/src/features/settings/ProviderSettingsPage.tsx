import { useEffect, useMemo, useState } from "react";

import { FormField, FormInput } from "../../components/FormField";
import { LoadingPage, PageFrame, SectionCard, StatusBadge } from "../../components/ui";
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
  supportedExecutionModes,
} from "../../lib/provider-catalog";
import type {
  ProviderCatalogOption,
  ProviderCredentialInput,
  ProviderCredentialRecord,
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

function formatDate(value: string | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

function validationBadgeStatus(credential: ProviderCredentialRecord): string {
  if (credential.validationStatus === "valid") return "validated";
  if (credential.validationStatus === "invalid") return "invalid";
  if (credential.validationStatus === "unsupported") return "validation unavailable";
  if (credential.validationStatus === "unreachable") return "provider unreachable";
  return "not validated";
}

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
    const payload = {
      ...toCredentialInput(form),
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

  if (isLoading || !credentials || !policy) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Settings"
      title="Providers"
      description="Manage encrypted provider credentials, model names, and which provider route is active for text, audio, image, video, and moderation generation."
      inspector={
        <div className="flex flex-col gap-4">
          <SectionCard title="Security">
            <p className="text-sm leading-relaxed text-slate-300">
              API keys are only sent to the backend, encrypted at rest, and never returned to the browser after save. Leave the API key field blank while editing to keep the existing secret unchanged.
            </p>
          </SectionCard>
          <SectionCard title="Runtime Notes">
            <p className="text-sm leading-relaxed text-slate-300">
              Azure OpenAI remains the recommended text route in this build. Stability AI image, ElevenLabs audio, and Runway video can now be activated from this screen, while Kling remains storage-only until its adapter is added.
            </p>
          </SectionCard>
        </div>
      }
    >
      <SectionCard
        title="Active Routes"
        subtitle="Choose which provider route the workspace currently uses for each generation type."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modalityOrder.map((modality) => {
            const route = policy[modality];
            const credential = findCredentialById(credentials, route.credentialId);
            return (
              <div
                key={modality}
                className="rounded-xl border border-slate-800/70 bg-slate-950/40 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      {providerGenerationLabels[route.generationType]}
                    </p>
                    <h4 className="mt-1 text-sm font-semibold text-slate-100">
                      {route.providerLabel}
                    </h4>
                  </div>
                  <StatusBadge status={supportedExecutionModes[route.mode]} />
                </div>
                <p className="mt-3 text-sm text-slate-300">
                  {credential
                    ? `${credential.name}${credential.modelName ? ` · ${credential.modelName}` : ""}`
                    : "Using the hosted platform default."}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {credential ? `Deployment: ${credential.deployment || "Not set"}` : route.providerKey}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-md border border-slate-700/60 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-800"
                    disabled={route.mode === "hosted" || isSaving}
                    onClick={() => handleUseHostedDefault(modality)}
                  >
                    Use hosted default
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard
        title={editingId ? "Edit Credential" : "Add Credential"}
        subtitle="Select a generation type, choose the provider, and save the model and endpoint details the backend should use."
      >
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <FormField htmlFor="generationType" label="Generation Type">
              <select
                id="generationType"
                className="w-full rounded-xl border border-border-card bg-glass px-3.5 py-2.5 text-sm text-primary outline-none transition-all hover:border-border-active focus:border-accent"
                value={form.generationType}
                onChange={(event) => {
                  const generationType = event.target.value as ProviderGenerationType;
                  const nextOptions = getProviderOptionsByGenerationType(generationType);
                  const first = nextOptions[0];
                  setForm((current) => {
                    if (editingId) {
                      return {
                        ...current,
                        generationType,
                        providerKey: first?.providerKey ?? current.providerKey,
                      };
                    }
                    const base = {
                      ...current,
                      generationType,
                      providerKey: first?.providerKey ?? current.providerKey,
                    };
                    return applyProviderFormDefaults(base, first);
                  });
                }}
              >
                {Object.entries(providerGenerationLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField htmlFor="providerKey" label="Provider">
              <select
                id="providerKey"
                className="w-full rounded-xl border border-border-card bg-glass px-3.5 py-2.5 text-sm text-primary outline-none transition-all hover:border-border-active focus:border-accent"
                value={selectedProvider?.providerKey ?? form.providerKey}
                onChange={(event) => {
                  const providerKey = event.target.value;
                  const option = providerOptions.find((o) => o.providerKey === providerKey);
                  setForm((current) => {
                    if (editingId) {
                      return { ...current, providerKey };
                    }
                    return applyProviderFormDefaults({ ...current, providerKey }, option);
                  });
                }}
              >
                {providerOptions.map((option) => (
                  <option key={option.providerKey} value={option.providerKey}>
                    {option.providerLabel}
                    {option.supportsActivation ? "" : " (storage only)"}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          <FormInput
            id="credentialName"
            label="Credential Name"
            value={form.name}
            onChange={(value) => setForm((current) => ({ ...current, name: value }))}
            placeholder="Azure OpenAI Primary"
          />

          {selectedProvider ? (
            <p className="rounded-xl border border-slate-800/70 bg-slate-950/40 px-4 py-3 text-sm text-slate-300">
              {selectedProvider.description}
            </p>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            {selectedProvider?.fields.map((field) => (
              <FormInput
                key={field.key}
                id={field.key}
                label={field.label}
                type={field.secret ? "password" : "text"}
                value={form[field.key]}
                onChange={(value) =>
                  setForm((current) => ({ ...current, [field.key]: value }))
                }
                placeholder={field.placeholder}
                help={
                  [field.key === "apiKey" && editingId ? "Leave blank to keep the existing API key." : "", field.help || ""]
                    .filter(Boolean)
                    .join(" ") || undefined
                }
              />
            ))}
          </div>

          <label className="flex items-start gap-3 rounded-xl border border-slate-800/70 bg-slate-950/30 px-4 py-3 text-sm text-slate-300">
            <input
              checked={form.setAsActiveRoute}
              className="mt-1"
              disabled={!selectedProvider?.supportsActivation}
              onChange={(event) =>
                setForm((current) => ({ ...current, setAsActiveRoute: event.target.checked }))
              }
              type="checkbox"
            />
            <span>
              Make this the active route for {providerGenerationLabels[form.generationType]} after
              save.
              {!selectedProvider?.supportsActivation
                ? " This provider can be stored, but it cannot be activated for runtime routing in the current backend build."
                : ""}
            </span>
          </label>

          <div className="flex flex-wrap gap-3">
            <button
              className="rounded-md bg-accent-cyan px-4 py-2 text-sm font-semibold text-slate-950 shadow-md transition-all hover:bg-accent-cyan/90 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isSaving || !form.name.trim()}
              type="submit"
            >
              {editingId
                ? updateCredential.isPending
                  ? "Saving changes..."
                  : "Save changes"
                : createCredential.isPending
                  ? "Saving credential..."
                  : "Add credential"}
            </button>
            {editingId ? (
              <button
                type="button"
                className="rounded-md border border-slate-700/60 bg-slate-900/80 px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800"
                onClick={() => {
                  setEditingId(null);
                  setForm(defaultFormState());
                }}
              >
                Cancel edit
              </button>
            ) : null}
          </div>
        </form>
      </SectionCard>

      <SectionCard
        title="Configured Credentials"
        subtitle="Saved provider connections, model metadata, and whether each credential is currently active."
      >
        <div className="overflow-x-auto rounded-lg border border-slate-800/60 bg-slate-900/40">
          <table className="w-full text-left text-sm text-slate-300">
            <thead>
              <tr>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Credential
                </th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Type
                </th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Model
                </th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Endpoint / Deployment
                </th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Last Used
                </th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Status
                </th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {credentials.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-slate-500" colSpan={7}>
                    No provider credentials configured yet.
                  </td>
                </tr>
              ) : (
                credentials.map((credential) => (
                  <tr key={credential.id} className="transition-colors hover:bg-slate-800/30">
                    <td className="border-b border-slate-800/50 px-4 py-3 align-top">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-slate-100">{credential.name}</span>
                        <span className="text-xs text-slate-500">{credential.providerLabel}</span>
                      </div>
                    </td>
                    <td className="border-b border-slate-800/50 px-4 py-3 align-top">
                      {providerGenerationLabels[credential.generationType]}
                    </td>
                    <td className="border-b border-slate-800/50 px-4 py-3 align-top">
                      <div className="flex flex-col gap-1">
                        <span>{credential.modelName || "Not set"}</span>
                        {credential.voice ? (
                          <span className="text-xs text-slate-500">Voice: {credential.voice}</span>
                        ) : null}
                      </div>
                    </td>
                    <td className="border-b border-slate-800/50 px-4 py-3 align-top">
                      <div className="flex flex-col gap-1">
                        <span className="break-all text-xs text-slate-400">
                          {credential.endpoint || "No endpoint"}
                        </span>
                        <span className="text-xs text-slate-500">
                          {credential.deployment
                            ? `Deployment: ${credential.deployment}`
                            : "No deployment"}
                        </span>
                      </div>
                    </td>
                    <td className="border-b border-slate-800/50 px-4 py-3 align-top">
                      <div className="flex flex-col gap-1">
                        <span>{formatDate(credential.lastUsedAt)}</span>
                        <span className="text-xs text-slate-500">
                          Added {formatDate(credential.createdAt)}
                        </span>
                      </div>
                    </td>
                    <td className="border-b border-slate-800/50 px-4 py-3 align-top">
                      <div className="flex flex-col gap-2">
                        <StatusBadge
                          status={
                            credential.isActive
                              ? "active"
                              : credential.supportsActivation
                                ? "saved"
                                : "storage only"
                          }
                        />
                        <span className="text-xs text-slate-500">
                          {credential.secretConfigured ? "Secret configured" : "Missing secret"}
                        </span>
                        <StatusBadge status={validationBadgeStatus(credential)} />
                        <span className="text-xs text-slate-500">
                          {credential.validationStatus === "not_validated"
                            ? "Not validated yet"
                            : credential.validationStatus === "unsupported"
                              ? "Remote validation is not available for this provider yet"
                              : credential.validationStatus === "unreachable"
                                ? `Last validation attempt ${formatDate(credential.lastValidatedAt)}`
                                : `Validated ${formatDate(credential.lastValidatedAt)}`}
                        </span>
                        {credential.validationError ? (
                          <span className="text-xs text-rose-300">{credential.validationError}</span>
                        ) : null}
                      </div>
                    </td>
                    <td className="border-b border-slate-800/50 px-4 py-3 align-top">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="rounded-md border border-slate-700/60 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-800"
                          onClick={() => {
                            setEditingId(credential.id);
                            setForm(toFormState(credential));
                          }}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-slate-700/60 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={!credential.supportsActivation || credential.isActive || isSaving}
                          onClick={() => handleMakeActive(credential)}
                        >
                          Make active
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-emerald-700/60 bg-emerald-950/30 px-3 py-1.5 text-xs font-medium text-emerald-200 transition-colors hover:bg-emerald-900/50 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isSaving}
                          onClick={() => validateCredential.mutate(credential.id)}
                        >
                          {validateCredential.isPending ? "Validating..." : "Validate"}
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-rose-700/60 bg-rose-950/40 px-3 py-1.5 text-xs font-medium text-rose-200 transition-colors hover:bg-rose-900/60 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isSaving}
                          onClick={() => deleteCredential.mutate(credential.id)}
                        >
                          Revoke
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </PageFrame>
  );
}
