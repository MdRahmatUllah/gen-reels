import type {
  ExecutionMode,
  ProviderCatalogOption,
  ProviderGenerationType,
  ProviderModality,
} from "../types/domain";

const catalog: ProviderCatalogOption[] = [
  {
    providerKey: "azure_openai_text",
    providerLabel: "Azure OpenAI",
    modality: "text",
    generationType: "text",
    description: "Recommended for all text generation in this workspace.",
    supportsActivation: true,
    fields: [
      { key: "endpoint", label: "Endpoint", placeholder: "https://your-resource.openai.azure.com", required: true },
      { key: "apiVersion", label: "API Version", placeholder: "2024-10-21", required: true },
      { key: "deployment", label: "Deployment", placeholder: "gpt-4.1", required: true },
      { key: "modelName", label: "Model Name", placeholder: "gpt-4.1", help: "Optional display label for the deployment." },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
        help: "Paste Key 1 or Key 2; stored encrypted and never shown again after save.",
      },
    ],
  },
  {
    providerKey: "openai_text",
    providerLabel: "OpenAI",
    modality: "text",
    generationType: "text",
    description: "Credential storage only for now. Runtime routing is not enabled in this build.",
    supportsActivation: false,
    fields: [
      { key: "modelName", label: "Model Name", placeholder: "gpt-4.1" },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
      },
    ],
  },
  {
    providerKey: "azure_content_safety",
    providerLabel: "Azure Content Safety",
    modality: "moderation",
    generationType: "moderation",
    description: "Used for text moderation and policy checks.",
    supportsActivation: true,
    fields: [
      { key: "endpoint", label: "Endpoint", placeholder: "https://your-resource.cognitiveservices.azure.com", required: true },
      { key: "apiVersion", label: "API Version", placeholder: "2024-09-01", required: true },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
        help: "Paste the resource key; stored encrypted and never shown again after save.",
      },
    ],
  },
  {
    providerKey: "azure_openai_image",
    providerLabel: "Azure OpenAI Images",
    modality: "image",
    generationType: "image",
    description:
      "Use the resource base URL only (e.g. https://your-name.cognitiveservices.azure.com) — not the full /openai/deployments/... path. Deployment name must match the portal (e.g. gpt-image-1.5). API version 2024-02-01 matches Azure’s image generations docs.",
    supportsActivation: true,
    formDefaults: {
      apiVersion: "2024-02-01",
      deployment: "gpt-image-1.5",
    },
    fields: [
      {
        key: "endpoint",
        label: "Endpoint",
        placeholder: "https://your-resource.cognitiveservices.azure.com",
        required: true,
        help: "Resource base URL from Keys and Endpoint (no /openai/... suffix).",
      },
      {
        key: "apiVersion",
        label: "API Version",
        placeholder: "2024-02-01",
        required: true,
        help: "Must match the version shown on your deployment’s REST example (often 2024-02-01).",
      },
      {
        key: "deployment",
        label: "Deployment",
        placeholder: "gpt-image-1.5",
        required: true,
        help: "Exactly as in Azure Portal → Deployments (name of the image model deployment).",
      },
      {
        key: "modelName",
        label: "Model Name",
        placeholder: "gpt-image-1.5",
        help: "Optional label; the deployment name above drives the API path.",
      },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
        help: "Key 1 or Key 2 from the same Azure resource; stored encrypted and never shown again after save.",
      },
    ],
  },
  {
    providerKey: "stability_image",
    providerLabel: "Stability AI",
    modality: "image",
    generationType: "image",
    description: "Routable image generation for this build. Use a Stability model name such as stable-image-core or stable-image-ultra.",
    supportsActivation: true,
    fields: [
      { key: "modelName", label: "Model Name", placeholder: "stable-image-core", help: "Use stable-image-core or stable-image-ultra." },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
      },
    ],
  },
  {
    providerKey: "azure_openai_speech",
    providerLabel: "Azure OpenAI Audio",
    modality: "speech",
    generationType: "audio",
    description: "Recommended for narration and speech synthesis in this workspace.",
    supportsActivation: true,
    fields: [
      { key: "endpoint", label: "Endpoint", placeholder: "https://your-resource.openai.azure.com", required: true },
      { key: "apiVersion", label: "API Version", placeholder: "2024-10-21", required: true },
      { key: "deployment", label: "Deployment", placeholder: "gpt-4o-mini-tts", required: true },
      { key: "modelName", label: "Model Name", placeholder: "gpt-4o-mini-tts" },
      { key: "voice", label: "Voice", placeholder: "alloy", help: "Optional default voice for speech generation." },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
        help: "Paste Key 1 or Key 2; stored encrypted and never shown again after save.",
      },
    ],
  },
  {
    providerKey: "elevenlabs_speech",
    providerLabel: "ElevenLabs",
    modality: "speech",
    generationType: "audio",
    description: "Routable narration and speech synthesis in this build when you provide a voice ID and API key.",
    supportsActivation: true,
    fields: [
      { key: "modelName", label: "Model Name", placeholder: "eleven_multilingual_v2" },
      { key: "voice", label: "Voice", placeholder: "Voice ID", required: true, help: "Use the ElevenLabs voice ID that should synthesize narration." },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
      },
    ],
  },
  {
    providerKey: "runway_video",
    providerLabel: "Runway",
    modality: "video",
    generationType: "video",
    description: "Routable video generation for this build using Runway image-to-video task polling.",
    supportsActivation: true,
    fields: [
      { key: "endpoint", label: "Endpoint", placeholder: "https://api.dev.runwayml.com", help: "Optional custom API base URL." },
      { key: "modelName", label: "Model Name", placeholder: "gen4_turbo", help: "For example gen4_turbo." },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
      },
    ],
  },
  {
    providerKey: "kling_video",
    providerLabel: "Kling",
    modality: "video",
    generationType: "video",
    description: "Credential storage only for now. Hosted video routing remains the active runtime path.",
    supportsActivation: false,
    fields: [
      { key: "modelName", label: "Model Name", placeholder: "kling-v1.6" },
      {
        key: "apiKey",
        label: "API Key",
        placeholder: "••••••••••••••••••••",
        required: true,
        secret: true,
      },
    ],
  },
];

const generationLabels: Record<ProviderGenerationType, string> = {
  text: "Text generation",
  moderation: "Moderation",
  image: "Image generation",
  video: "Video generation",
  audio: "Audio generation",
};

const modalityToGenerationType: Record<ProviderModality, ProviderGenerationType> = {
  text: "text",
  moderation: "moderation",
  image: "image",
  video: "video",
  speech: "audio",
};

export const providerCatalog = catalog;
export const providerGenerationLabels = generationLabels;
export const supportedExecutionModes: Record<ExecutionMode, string> = {
  hosted: "Hosted default",
  byo: "Bring your own",
  local: "Local worker",
};

export function getProviderCatalogOption(providerKey: string): ProviderCatalogOption | undefined {
  return catalog.find((option) => option.providerKey === providerKey);
}

export function getProviderOptionsByGenerationType(
  generationType: ProviderGenerationType,
): ProviderCatalogOption[] {
  return catalog.filter((option) => option.generationType === generationType);
}

export function generationTypeFromModality(modality: ProviderModality): ProviderGenerationType {
  return modalityToGenerationType[modality];
}

export function providerLabelFromKey(providerKey: string): string {
  if (providerKey === "veo_video") {
    return "Google Veo";
  }
  return getProviderCatalogOption(providerKey)?.providerLabel ?? providerKey;
}
