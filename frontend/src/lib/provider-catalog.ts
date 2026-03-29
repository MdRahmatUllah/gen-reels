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
      { key: "apiKey", label: "API Key", placeholder: "Azure OpenAI key", required: true, secret: true },
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
      { key: "apiKey", label: "API Key", placeholder: "OpenAI API key", required: true, secret: true },
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
      { key: "apiKey", label: "API Key", placeholder: "Azure Content Safety key", required: true, secret: true },
    ],
  },
  {
    providerKey: "azure_openai_image",
    providerLabel: "Azure OpenAI Images",
    modality: "image",
    generationType: "image",
    description: "Azure-hosted image generation with configurable deployment and model names.",
    supportsActivation: true,
    fields: [
      { key: "endpoint", label: "Endpoint", placeholder: "https://your-resource.openai.azure.com", required: true },
      { key: "apiVersion", label: "API Version", placeholder: "2024-10-21", required: true },
      { key: "deployment", label: "Deployment", placeholder: "gpt-image-1", required: true },
      { key: "modelName", label: "Model Name", placeholder: "gpt-image-1" },
      { key: "apiKey", label: "API Key", placeholder: "Azure OpenAI key", required: true, secret: true },
    ],
  },
  {
    providerKey: "stability_image",
    providerLabel: "Stability AI",
    modality: "image",
    generationType: "image",
    description: "Credential storage only for now. Runtime routing is not enabled in this build.",
    supportsActivation: false,
    fields: [
      { key: "modelName", label: "Model Name", placeholder: "stable-image-ultra" },
      { key: "apiKey", label: "API Key", placeholder: "Stability AI API key", required: true, secret: true },
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
      { key: "apiKey", label: "API Key", placeholder: "Azure OpenAI key", required: true, secret: true },
    ],
  },
  {
    providerKey: "elevenlabs_speech",
    providerLabel: "ElevenLabs",
    modality: "speech",
    generationType: "audio",
    description: "Credential storage only for now. Runtime routing is not enabled in this build.",
    supportsActivation: false,
    fields: [
      { key: "modelName", label: "Model Name", placeholder: "eleven_multilingual_v2" },
      { key: "voice", label: "Voice", placeholder: "Voice ID or name" },
      { key: "apiKey", label: "API Key", placeholder: "ElevenLabs API key", required: true, secret: true },
    ],
  },
  {
    providerKey: "runway_video",
    providerLabel: "Runway",
    modality: "video",
    generationType: "video",
    description: "Credential storage only for now. Hosted video routing remains the active runtime path.",
    supportsActivation: false,
    fields: [
      { key: "modelName", label: "Model Name", placeholder: "gen-4-turbo" },
      { key: "apiKey", label: "API Key", placeholder: "Runway API key", required: true, secret: true },
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
      { key: "apiKey", label: "API Key", placeholder: "Kling API key", required: true, secret: true },
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
