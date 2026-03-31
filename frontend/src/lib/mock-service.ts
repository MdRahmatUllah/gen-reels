/**
 * Stateful mock service that simulates the backend API.
 * All data lives in-memory. Idea and script generation use realistic delays.
 * This is the remaining explicit mock-mode adapter after retiring the old mock-api layer.
 */
import type {
  AuthSession,
  ProviderCredentialInput,
  ProviderCredentialRecord,
  ProviderModality,
  WorkspaceExecutionPolicy,
  BriefData,
  CreateProjectPayload,
  DashboardData,
  IdeaCandidate,
  IdeaSet,
  LoginCredentials,
  QuickCreateProjectPayload,
  QuickCreateProjectResponse,
  QuickCreateStatus,
  RenderJob,
  RenderStep,
  ExportArtifact,
  ProjectSummary,
  ScenePlan,
  ScenePlanSet,
  SceneSegment,
  ScriptData,
  ShellData,
  VisualPreset,
  VoicePreset,
  WorkspaceSummary,
  UserProfile,
  BillingData,
  PresetCard,
  TemplateCard,
  AssetRecord,
  SettingsSection,
  ProjectBundle,
  UsageRecord,
  InvoiceItem,
  BrandKit,
  Comment,
  AdminQueueItem,
  AdminWorkspaceRow,
  AdminRenderRow,
  ProviderKey,
  LocalWorker,
} from "../types/domain";
import { isMockMode } from "./config";
import {
  generationTypeFromModality,
  getProviderCatalogOption,
  providerLabelFromKey,
} from "./provider-catalog";
import {
  liveAddProviderKey,
  liveAddComment,
  liveApproveScenePlan,
  liveApproveScript,
  liveCancelRender,
  liveCreateProviderCredential,
  liveCreateProject,
  liveCreateVisualPreset,
  liveCreateVoicePreset,
  liveDeleteProviderCredential,
  liveDeleteProviderKey,
  liveGenerateIdeas,
  liveGetQuickCreateStatus,
  liveGeneratePromptPairs,
  liveGenerateScenePlan,
  liveGenerateScript,
  liveGetBrandKits,
  liveGetAssets,
  liveGetBilling,
  liveGetBillingData,
  liveGetBrief,
  liveGetComments,
  liveGetDashboardData,
  liveGetExports,
  liveGetIdeas,
  liveGetLocalWorkers,
  liveGetPresets,
  liveGetProject,
  liveGetProjectBundle,
  liveGetProjects,
  liveGetProviderCredentials,
  liveGetExecutionPolicy,
  liveGetProviderKeys,
  liveGetRenders,
  liveGetScenePlan,
  liveGetScript,
  liveGetSession,
  liveGetSettings,
  liveGetShellData,
  liveGetTemplates,
  liveGetVisualPresets,
  liveGetVoicePresets,
  liveCloneTemplate,
  liveLogin,
  liveLogout,
  liveQuickCreateProject,
  liveResolveComment,
  liveRetryRenderStep,
  liveSaveBrandKit,
  liveSelectIdea,
  liveSetScenePlanPreset,
  liveStartRender,
  liveUpdateBrief,
  liveUpdateExecutionPolicyRoute,
  liveUpdateProviderCredential,
  liveUpdateScene,
  liveUpdateScript,
  liveValidateProviderCredential,
  liveGetAdminQueue,
  liveApproveQueueItem,
  liveRejectQueueItem,
  liveGetAdminWorkspaces,
  liveGetAdminRenders,
} from "./live-api";

/* ─── Helpers ─────────────────────────────────────────────────────────────── */
let idCounter = 1000;
function nextId(prefix: string): string {
  return `${prefix}_${++idCounter}`;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomDelay(min = 300, max = 800): Promise<void> {
  return delay(min + Math.random() * (max - min));
}

/* ─── Seed Data ───────────────────────────────────────────────────────────── */
const seedUser: UserProfile = {
  id: "user_1",
  name: "Alex Rivera",
  email: "alex@studio.io",
  role: "Admin",
  avatarInitials: "AR",
};

const seedWorkspaces: WorkspaceSummary[] = [
  {
    id: "workspace_north_star",
    name: "North Star Studio",
    plan: "Pro",
    seats: 5,
    creditsRemaining: 842,
    creditsTotal: 1200,
    monthlyBudget: 500,
    queueCount: 2,
    notifications: 3,
  },
  {
    id: "workspace_moonrise",
    name: "Moonrise Creative",
    plan: "Creator",
    seats: 2,
    creditsRemaining: 180,
    creditsTotal: 300,
    monthlyBudget: 150,
    queueCount: 0,
    notifications: 1,
  },
];

const seedBrief: BriefData = {
  objective: "Drive pre-orders for Aurora Serum by demonstrating the visible glow effect within 5 seconds of application.",
  hook: "What if your skin could literally glow?",
  targetAudience: "Women 24-38, skincare-curious, active on TikTok and Instagram Reels",
  callToAction: "Tap the link to pre-order Aurora Serum. First 500 get the Starter Kit free.",
  brandNorthStar: "Scientific luxury — clinical results with a sensory, premium feel.",
  guardrails: [
    "No before/after claims without clinical backing",
    "No competitor mentions",
    "Keep language inclusive and body-positive",
    "Follow FDA guidance for cosmetic claims",
  ],
  mustInclude: [
    "Product close-up with glow effect",
    "Ingredient callout: Vitamin C + Niacinamide",
    "Price and limited-time offer",
    "Brand logo in final frame",
  ],
  approvalSteps: [
    "Script review by brand lead",
    "Visual direction sign-off",
    "Legal compliance check for claims",
    "Final export approval",
  ],
};

function makeSeedProject(id: string, title: string, stage: string): ProjectSummary {
  return {
    id,
    title,
    client: "North Star Beauty",
    stage: stage as ProjectSummary["stage"],
    renderStatus: "draft",
    updatedAt: new Date().toISOString(),
    aspectRatio: "9:16",
    sceneCount: 0,
    durationSec: 0,
    tags: ["skincare", "product-launch"],
    hook: "",
    palette: "Warm Coral + Cloud White",
    voicePreset: "Confident Narrator",
    objective: "",
    nextMilestone: "Complete brief",
    selectedIdeaId: null,
  };
}

/* ─── In-Memory State ─────────────────────────────────────────────────────── */
interface MockState {
  isAuthenticated: boolean;
  user: UserProfile;
  workspaces: WorkspaceSummary[];
  activeWorkspaceId: string;
  projects: Map<string, ProjectSummary>;
  briefs: Map<string, BriefData>;
  ideaSets: Map<string, IdeaSet>;
  scripts: Map<string, ScriptData>;
  scenePlanSets: Map<string, ScenePlanSet>;
  renderJobs: Map<string, RenderJob>;
  exports: Map<string, ExportArtifact[]>;
  visualPresets: VisualPreset[];
  voicePresets: VoicePreset[];
  usageRecords: UsageRecord[];
  invoices: InvoiceItem[];
  assets: AssetRecord[];
  templates: TemplateCard[];
  brandKits: BrandKit[];
  comments: Comment[];
  providerKeys: ProviderKey[];
  providerCredentials: ProviderCredentialRecord[];
  executionPolicy: WorkspaceExecutionPolicy;
  localWorkers: LocalWorker[];
  quickCreateStatuses: Map<string, QuickCreateStatus>;
}

const seedTemplates: TemplateCard[] = [
  { id: "tpl_skincare", name: "Premium Skincare Launch", description: "Soft lighting, ASMR pacing, and clinical text callouts.", duration: "15-30s", scenes: 6, style: "Minimal" },
  { id: "tpl_founder", name: "Founder Story Talking Head", description: "Direct camera appeal with b-roll intercut.", duration: "45-60s", scenes: 12, style: "Documentary" },
  { id: "tpl_howto", name: "Step-by-Step Tutorial", description: "Numbered beats, top-down angles, energetic pacing.", duration: "30-45s", scenes: 8, style: "Energetic" },
];

const seedAssets: AssetRecord[] = [
  { id: "ast_1", type: "video", sourceProjectId: "project_aurora_serum", sourceSceneId: "scene_1", thumbnailUrl: "https://images.unsplash.com/photo-1615397323861-1250ec46be22?q=80&w=200&auto=format&fit=crop", url: "#", prompt: "A slow pan over glowing serum bottle", tags: ["skincare", "bottle", "slow-pan", "approved"], createdAt: new Date(Date.now() - 86400000).toISOString() },
  { id: "ast_2", type: "image", sourceProjectId: "project_aurora_serum", sourceSceneId: "scene_2", thumbnailUrl: "https://images.unsplash.com/photo-1596755389378-c11d4d1253e2?q=80&w=200&auto=format&fit=crop", url: "#", prompt: "Drip of serum on face", tags: ["skincare", "macro"], createdAt: new Date(Date.now() - 186400000).toISOString() },
  { id: "ast_3", type: "audio", sourceProjectId: null, sourceSceneId: null, thumbnailUrl: "https://images.unsplash.com/photo-1620288627223-53302f4e8c74?q=80&w=200&auto=format&fit=crop", url: "#", prompt: "Ambient corporate 1", tags: ["music", "corporate", "ambient", "cleared"], createdAt: new Date(Date.now() - 286400000).toISOString() },
  { id: "ast_4", type: "video", sourceProjectId: "project_glow", sourceSceneId: "scene_4", thumbnailUrl: "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?q=80&w=200&auto=format&fit=crop", url: "#", prompt: "Woman smiling applying cream", tags: ["lifestyle", "application"], createdAt: new Date(Date.now() - 386400000).toISOString() },
  { id: "ast_5", type: "image", sourceProjectId: "project_x", sourceSceneId: null, thumbnailUrl: "https://images.unsplash.com/photo-1571781564993-4a1251993cc0?q=80&w=200&auto=format&fit=crop", url: "#", prompt: "Clean white studio background", tags: ["background", "minimal"], createdAt: new Date(Date.now() - 486400000).toISOString() },
];

const seedVisualPresets: VisualPreset[] = [
  { id: "vp_editorial", name: "Editorial Clean", description: "Cool daylight, matte surfaces, negative space", category: "Beauty", style: "editorial", palette: "Frosted cobalt / ivory", lighting: "Cool daylight, diffused" },
  { id: "vp_cinematic", name: "Warm Cinematic", description: "Golden hour tones with filmic grain and depth", category: "Lifestyle", style: "cinematic", palette: "Amber / deep shadow", lighting: "Golden hour, directional" },
  { id: "vp_minimal", name: "Minimal Studio", description: "Pure white backdrop with sharp product focus", category: "Product", style: "minimal", palette: "White / charcoal accent", lighting: "Even studio, high-key" },
];

const seedVoicePresets: VoicePreset[] = [
  { id: "voice_confident", name: "Confident Narrator", description: "Clear, authoritative, measured pacing", tone: "authoritative", pacing: "measured", accent: "neutral" },
  { id: "voice_warm", name: "Warm Storyteller", description: "Friendly, conversational, approachable", tone: "warm", pacing: "natural", accent: "neutral" },
  { id: "voice_editorial", name: "Ava Editorial", description: "Polished, calm, premium feel", tone: "polished", pacing: "calm", accent: "neutral" },
];

const mockExecutionDefaults: WorkspaceExecutionPolicy = {
  text: {
    mode: "byo",
    providerKey: "azure_openai_text",
    providerLabel: "Azure OpenAI",
    credentialId: "cred_text_azure",
    generationType: "text",
  },
  moderation: {
    mode: "hosted",
    providerKey: "azure_content_safety",
    providerLabel: "Azure Content Safety",
    credentialId: null,
    generationType: "moderation",
  },
  image: {
    mode: "hosted",
    providerKey: "azure_openai_image",
    providerLabel: "Azure OpenAI Images",
    credentialId: null,
    generationType: "image",
  },
  video: {
    mode: "hosted",
    providerKey: "veo_video",
    providerLabel: "Google Veo",
    credentialId: null,
    generationType: "video",
  },
  speech: {
    mode: "hosted",
    providerKey: "azure_openai_speech",
    providerLabel: "Azure OpenAI Audio",
    credentialId: null,
    generationType: "audio",
  },
};

const seedProviderCredentials: ProviderCredentialRecord[] = [
  {
    id: "cred_text_azure",
    name: "Azure OpenAI Text",
    modality: "text",
    generationType: "text",
    providerKey: "azure_openai_text",
    providerLabel: "Azure OpenAI",
    supportsActivation: true,
    endpoint: "https://studio-dev.openai.azure.com",
    apiVersion: "2024-10-21",
    deployment: "gpt-4.1",
    modelName: "gpt-4.1",
    voice: "",
    secretConfigured: true,
    isActive: true,
    activeMode: "byo",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    lastUsedAt: new Date(Date.now() - 3600000).toISOString(),
    revokedAt: null,
    validationStatus: "valid",
    lastValidatedAt: new Date(Date.now() - 7200000).toISOString(),
    validationError: null,
  },
];

const state: MockState = {
  isAuthenticated: false,
  user: seedUser,
  workspaces: seedWorkspaces,
  activeWorkspaceId: "workspace_north_star",
  projects: new Map([
    ["project_aurora_serum", {
      ...makeSeedProject("project_aurora_serum", "Aurora Serum Launch", "brief"),
      hook: "What if your skin could literally glow?",
      objective: "Drive pre-orders for Aurora Serum",
      sceneCount: 8,
      durationSec: 72,
      nextMilestone: "Generate viral ideas",
    }],
  ]),
  briefs: new Map([
    ["project_aurora_serum", { ...seedBrief }],
  ]),
  ideaSets: new Map(),
  scripts: new Map(),
  scenePlanSets: new Map(),
  renderJobs: new Map(),
  exports: new Map(),
  visualPresets: [...seedVisualPresets],
  voicePresets: [...seedVoicePresets],
  usageRecords: [],
  invoices: [
    { id: "inv_01", label: "Pro plan subscription", amount: "$1,200", date: "Mar 1", status: "paid" }
  ],
  assets: [...seedAssets],
  templates: [...seedTemplates],
  brandKits: [
    { id: "bk_1", name: "Aurora Global", brandNorthStar: "Luminous, premium, accessible luxury", primaryPalette: "#003366, #F2F2F2", fontFamily: "Inter" }
  ],
  comments: [],
  providerKeys: [
    { id: "pk_1", provider: "openai", keyPrefix: "sk-...d92k", createdAt: new Date(Date.now() - 86400000).toISOString() },
  ],
  providerCredentials: [...seedProviderCredentials],
  executionPolicy: { ...mockExecutionDefaults },
  localWorkers: [
    {
      id: "lw_mac_studio",
      name: "Office Mac Studio M2",
      status: "online",
      lastHeartbeat: new Date().toISOString(),
      capabilities: { orderedReferenceImages: true, localTTS: true, videoFrames: false }
    },
    {
      id: "lw_rtx_4090",
      name: "Render Rig Alpha (4090)",
      status: "offline",
      lastHeartbeat: new Date(Date.now() - 3600000).toISOString(),
      capabilities: { orderedReferenceImages: true, localTTS: false, videoFrames: true }
    }
  ],
  quickCreateStatuses: new Map(),
};

/* ─── Idea Generation Templates ───────────────────────────────────────────── */
const ideaTemplates: Omit<IdeaCandidate, "id">[] = [
  {
    title: "The 5-Second Glow Test",
    hook: "I timed how fast this serum makes your skin glow. The answer broke me.",
    angle: "Speed/proof challenge — satisfying visual payoff",
    tags: ["challenge", "satisfying", "proof"],
    viralScore: 92,
  },
  {
    title: "Dermatologist Reacts to Ingredients",
    hook: "A derm breaks down why this formula shouldn't work... but it does.",
    angle: "Expert authority + surprise reversal",
    tags: ["expert", "science", "surprise"],
    viralScore: 87,
  },
  {
    title: "Morning Routine Transformation",
    hook: "My 60-second morning routine that replaced 4 products.",
    angle: "Simplification narrative — relatable time-saving",
    tags: ["routine", "minimal", "relatable"],
    viralScore: 84,
  },
  {
    title: "What $40 Gets You vs $200",
    hook: "I compared this $40 serum to a $200 luxury brand. Watch what happened.",
    angle: "Price comparison — underdog wins",
    tags: ["comparison", "value", "surprising"],
    viralScore: 89,
  },
  {
    title: "The Ingredient They Don't Want You to Know",
    hook: "Big skincare brands are hiding this combination. Here's why.",
    angle: "Insider secret + conspiracy lite",
    tags: ["secret", "ingredients", "exposé"],
    viralScore: 91,
  },
  {
    title: "Glow Check: 7 Days Later",
    hook: "I used this serum every day for a week. Day 7 was unreal.",
    angle: "Journey/transformation — daily documentation",
    tags: ["journey", "transformation", "daily"],
    viralScore: 86,
  },
];

/* ─── Script Generation Templates ─────────────────────────────────────────── */
function generateScriptFromIdea(idea: IdeaCandidate, brief: BriefData): ScriptData {
  const scriptId = nextId("script");
  return {
    id: scriptId,
    versionLabel: "v1 — generated",
    approvalState: "draft",
    lastEdited: new Date().toISOString(),
    totalWords: 186,
    readingTimeLabel: "~74s at natural pace",
    fullText: `[Opening — 0:00-0:05]\n${idea.hook}\n\n[Problem — 0:05-0:15]\nMost serums promise glowing skin. But here's the truth — 90% of them don't have the right vitamin C concentration to actually penetrate your skin barrier.\n\n[Solution — 0:15-0:30]\nAurora Serum uses a 15% L-Ascorbic Acid formula combined with Niacinamide. That's the exact ratio dermatologists recommend for visible results.\n\n[Proof — 0:30-0:45]\nWatch this — I'm applying it right now. Five seconds. That's all it takes. See that glow? That's not a filter. That's real skin doing what healthy skin does.\n\n[Social Proof — 0:45-0:55]\nOver 12,000 people joined the waitlist before launch day. The reviews are already flooding in.\n\n[CTA — 0:55-1:05]\n${brief.callToAction}\n\n[Closer — 1:05-1:12]\nYour skin deserves this. Trust the science. Trust the glow.`,
    lines: [
      { id: `${scriptId}_L1`, sceneId: "S01", beat: "Hook", narration: idea.hook, caption: "HOOK", durationSec: 5, status: "draft", visualDirection: "Close-up product reveal with dramatic lighting", voicePacing: "Punchy, confident" },
      { id: `${scriptId}_L2`, sceneId: "S02", beat: "Problem", narration: "Most serums promise glowing skin. But 90% don't have the right vitamin C concentration.", caption: "PROBLEM", durationSec: 10, status: "draft", visualDirection: "Split screen: generic products vs microscope view", voicePacing: "Measured, authoritative" },
      { id: `${scriptId}_L3`, sceneId: "S03", beat: "Solution", narration: "Aurora Serum uses 15% L-Ascorbic Acid combined with Niacinamide — the exact ratio dermatologists recommend.", caption: "SOLUTION", durationSec: 15, status: "draft", visualDirection: "Ingredient visualization, molecular close-up", voicePacing: "Clear, educational" },
      { id: `${scriptId}_L4`, sceneId: "S04", beat: "Proof", narration: "Five seconds. That's all it takes. See that glow? Not a filter. Real skin.", caption: "PROOF", durationSec: 15, status: "draft", visualDirection: "Real-time application with timer overlay", voicePacing: "Excited, building" },
      { id: `${scriptId}_L5`, sceneId: "S05", beat: "Social proof", narration: "Over 12,000 people joined the waitlist. Reviews are flooding in.", caption: "SOCIAL PROOF", durationSec: 10, status: "draft", visualDirection: "Testimonial montage, notification pings", voicePacing: "Warm, communal" },
      { id: `${scriptId}_L6`, sceneId: "S06", beat: "CTA", narration: brief.callToAction, caption: "CTA", durationSec: 10, status: "draft", visualDirection: "Product beauty shot with price overlay", voicePacing: "Urgent, direct" },
      { id: `${scriptId}_L7`, sceneId: "S07", beat: "Closer", narration: "Your skin deserves this. Trust the science. Trust the glow.", caption: "CLOSER", durationSec: 7, status: "draft", visualDirection: "Fade to brand logo on luminous background", voicePacing: "Soft, confident landing" },
    ],
  };
}

/* ─── Auth API ────────────────────────────────────────────────────────────── */
export async function mockLogin(credentials: LoginCredentials): Promise<AuthSession> {
  if (!isMockMode()) {
    return liveLogin(credentials);
  }
  await randomDelay(400, 1000);

  if (credentials.email === "alex@studio.io" && credentials.password === "password123") {
    state.isAuthenticated = true;
    return { user: state.user, workspaceId: state.activeWorkspaceId };
  }

  throw new Error("Invalid email or password");
}

export async function mockLogout(): Promise<void> {
  if (!isMockMode()) {
    return liveLogout();
  }
  await randomDelay(200, 400);
  state.isAuthenticated = false;
}

export async function mockGetSession(): Promise<AuthSession | null> {
  if (!isMockMode()) {
    return liveGetSession();
  }
  await delay(100);
  if (!state.isAuthenticated) return null;
  return { user: state.user, workspaceId: state.activeWorkspaceId };
}

/* ─── Project API ─────────────────────────────────────────────────────────── */
export async function mockGetProjects(): Promise<ProjectSummary[]> {
  if (!isMockMode()) {
    return liveGetProjects();
  }
  await randomDelay();
  return Array.from(state.projects.values());
}

export async function mockGetProject(projectId: string): Promise<ProjectSummary> {
  if (!isMockMode()) {
    return liveGetProject(projectId);
  }
  await randomDelay(100, 300);
  const project = state.projects.get(projectId);
  if (!project) throw new Error(`Project ${projectId} not found`);
  return project;
}

export async function mockGetProjectBundle(projectId: string): Promise<ProjectBundle> {
  if (!isMockMode()) {
    return liveGetProjectBundle(projectId);
  }
  await randomDelay(250, 450);

  const project = state.projects.get(projectId);
  if (!project) {
    throw new Error("Project not found");
  }

  const brief = state.briefs.get(projectId) ?? {
    objective: "",
    hook: "",
    targetAudience: "",
    callToAction: "",
    brandNorthStar: "",
    guardrails: [],
    mustInclude: [],
    approvalSteps: [],
  };
  const script = state.scripts.get(projectId) ?? {
    id: `script_${projectId}_empty`,
    versionLabel: "v0",
    approvalState: "draft",
    lastEdited: new Date().toISOString(),
    totalWords: 0,
    readingTimeLabel: "0s",
    fullText: "",
    lines: [],
  };
  const scenePlanSet = state.scenePlanSets.get(projectId) ?? {
    id: `scene_plan_${projectId}_empty`,
    projectId,
    status: "idle",
    approvalState: "draft",
    approvedAt: null,
    scenes: [],
    segments: [],
    totalDurationSec: 0,
    warningsCount: 0,
    visualPresetId: null,
    voicePresetId: null,
  };
  const renderJobs = state.renderJobs.get(projectId) ? [state.renderJobs.get(projectId)!] : [];
  const exports = state.exports.get(projectId) ?? [];

  return {
    project,
    brief,
    script,
    scenes: scenePlanSet.scenes,
    renderJobs,
    exports,
  };
}

export async function mockCreateProject(payload: CreateProjectPayload): Promise<ProjectSummary> {
  if (!isMockMode()) {
    return liveCreateProject(payload);
  }
  await randomDelay(300, 600);
  const id = nextId("project");
  const project: ProjectSummary = {
    ...makeSeedProject(id, payload.title, "brief"),
    client: payload.client,
    objective: "",
    nextMilestone: "Fill out the creative brief",
  };
  state.projects.set(id, project);
  state.briefs.set(id, {
    objective: "",
    hook: "",
    targetAudience: "",
    callToAction: "",
    brandNorthStar: "",
    guardrails: [],
    mustInclude: [],
    approvalSteps: ["Script review", "Visual sign-off", "Final export approval"],
  });
  return project;
}

/* ─── Brief API ───────────────────────────────────────────────────────────── */
const quickCreateStepOrder = [
  "brief_generation",
  "idea_generation",
  "script_generation",
  "scene_plan_generation",
  "prompt_pair_generation",
] as const;

function quickCreateFailureRecoveryPath(projectId: string, stepKind: string | null): string {
  if (stepKind === "idea_generation") return `/app/projects/${projectId}/ideas`;
  if (stepKind === "script_generation") return `/app/projects/${projectId}/script`;
  if (stepKind === "scene_plan_generation" || stepKind === "prompt_pair_generation") {
    return `/app/projects/${projectId}/scenes`;
  }
  return `/app/projects/${projectId}/brief`;
}

function fallbackProjectTitleFromIdea(ideaPrompt: string): string {
  const cleaned = ideaPrompt.trim().replace(/\s+/g, " ");
  if (!cleaned) {
    return "Untitled Project";
  }
  return cleaned
    .split(" ")
    .slice(0, 7)
    .join(" ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function synthesizeQuickCreateBrief(
  ideaPrompt: string,
  starterLabel: string,
): { title: string; brief: BriefData } {
  const normalized = ideaPrompt.trim();
  const shortIdea = normalized.length > 120 ? `${normalized.slice(0, 117)}...` : normalized;
  return {
    title: fallbackProjectTitleFromIdea(normalized),
    brief: {
      objective: `Create a high-performing short-form video about ${shortIdea}.`,
      hook: normalized,
      targetAudience: "Short-form viewers likely to engage with a clear, emotionally resonant concept.",
      callToAction: "Prompt the viewer to take the next obvious step after watching.",
      brandNorthStar:
        starterLabel === "Studio Default"
          ? "Confident, premium, conversion-minded storytelling."
          : `Use ${starterLabel} as the creative starting frame while tailoring the story to the new concept.`,
      guardrails: [
        "Keep the message specific and easy to understand in the first few seconds.",
        "Avoid cluttered visuals or claims that cannot be supported.",
        "Preserve a clear narrative arc from hook to CTA.",
      ],
      mustInclude: [
        "A strong first-frame visual hook",
        "One memorable proof point or transformation beat",
        "A clear final CTA",
      ],
      approvalSteps: ["Script review", "Visual sign-off", "Final export approval"],
    },
  };
}

function buildMockQuickCreateStatus(projectId: string): QuickCreateStatus {
  const existing = state.quickCreateStatuses.get(projectId);
  if (existing) {
    return existing;
  }
  const project = state.projects.get(projectId);
  if (!project) {
    throw new Error(`Project ${projectId} not found`);
  }
  return {
    projectId,
    projectTitle: project.title,
    projectStage: project.stage,
    job: {
      id: nextId("quickstart"),
      jobKind: "project_bootstrap",
      status: "queued",
      errorCode: null,
      errorMessage: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      completedAt: null,
    },
    steps: quickCreateStepOrder.map((stepKind, index) => ({
      stepKind,
      stepIndex: index + 1,
      status: "queued",
      errorCode: null,
      errorMessage: null,
      startedAt: null,
      completedAt: null,
    })),
    currentStep: quickCreateStepOrder[0],
    completedSteps: [],
    redirectPath: `/app/projects/${projectId}/scenes`,
    recoveryPath: `/app/projects/${projectId}/brief`,
    isActive: true,
    isCompleted: false,
    hasFailed: false,
  };
}

function updateMockQuickCreateStatus(
  projectId: string,
  mutate: (status: QuickCreateStatus) => QuickCreateStatus,
): QuickCreateStatus {
  const status = mutate(buildMockQuickCreateStatus(projectId));
  state.quickCreateStatuses.set(projectId, status);
  return status;
}

async function runMockQuickCreate(
  projectId: string,
  payload: QuickCreateProjectPayload,
  starterLabel: string,
): Promise<void> {
  const runStep = async (
    stepKind: (typeof quickCreateStepOrder)[number],
    action: () => Promise<void>,
  ) => {
    updateMockQuickCreateStatus(projectId, (current) => ({
      ...current,
      projectTitle: state.projects.get(projectId)?.title ?? current.projectTitle,
      projectStage: state.projects.get(projectId)?.stage ?? current.projectStage,
      job: {
        ...current.job,
        status: "running",
        updatedAt: new Date().toISOString(),
      },
      currentStep: stepKind,
      recoveryPath: quickCreateFailureRecoveryPath(projectId, stepKind),
      steps: current.steps.map((step) =>
        step.stepKind === stepKind
          ? {
              ...step,
              status: "running",
              startedAt: step.startedAt ?? new Date().toISOString(),
              errorCode: null,
              errorMessage: null,
            }
          : step,
      ),
      isActive: true,
      isCompleted: false,
      hasFailed: false,
    }));

    try {
      await action();
      updateMockQuickCreateStatus(projectId, (current) => ({
        ...current,
        projectTitle: state.projects.get(projectId)?.title ?? current.projectTitle,
        projectStage: state.projects.get(projectId)?.stage ?? current.projectStage,
        currentStep:
          quickCreateStepOrder[quickCreateStepOrder.indexOf(stepKind) + 1] ?? null,
        completedSteps: current.completedSteps.includes(stepKind)
          ? current.completedSteps
          : [...current.completedSteps, stepKind],
        steps: current.steps.map((step) =>
          step.stepKind === stepKind
            ? {
                ...step,
                status: "completed",
                completedAt: new Date().toISOString(),
              }
            : step,
        ),
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Quick-create failed.";
      updateMockQuickCreateStatus(projectId, (current) => ({
        ...current,
        projectTitle: state.projects.get(projectId)?.title ?? current.projectTitle,
        projectStage: state.projects.get(projectId)?.stage ?? current.projectStage,
        job: {
          ...current.job,
          status: "failed",
          errorCode: "mock_quick_create_failed",
          errorMessage: message,
          updatedAt: new Date().toISOString(),
        },
        currentStep: stepKind,
        recoveryPath: quickCreateFailureRecoveryPath(projectId, stepKind),
        steps: current.steps.map((step) =>
          step.stepKind === stepKind
            ? {
                ...step,
                status: "failed",
                errorCode: "mock_quick_create_failed",
                errorMessage: message,
                completedAt: new Date().toISOString(),
              }
            : step,
        ),
        isActive: false,
        isCompleted: false,
        hasFailed: true,
      }));
      throw error;
    }
  };

  try {
    await runStep("brief_generation", async () => {
      const synthesized = synthesizeQuickCreateBrief(payload.ideaPrompt, starterLabel);
      await mockUpdateBrief(projectId, synthesized.brief);
      const project = state.projects.get(projectId);
      if (project) {
        project.title = synthesized.title;
        project.nextMilestone = "Generating ranked ideas from the synthesized brief";
        project.updatedAt = new Date().toISOString();
        state.projects.set(projectId, project);
      }
    });

    await runStep("idea_generation", async () => {
      const ideaSet = await mockGenerateIdeas(projectId);
      const selectedIdea = ideaSet.ideas[0];
      if (selectedIdea) {
        await mockSelectIdea(projectId, selectedIdea.id);
      }
    });

    await runStep("script_generation", async () => {
      await mockGenerateScript(projectId);
      await mockApproveScript(projectId);
    });

    await runStep("scene_plan_generation", async () => {
      await mockGenerateScenePlan(projectId);
    });

    await runStep("prompt_pair_generation", async () => {
      const planSet = state.scenePlanSets.get(projectId);
      if (!planSet) {
        throw new Error("Scene plan missing during quick-create.");
      }
      for (const scene of planSet.scenes) {
        await mockGeneratePromptPairs(projectId, scene.id);
      }
      await mockApproveScenePlan(projectId);
    });

    updateMockQuickCreateStatus(projectId, (current) => ({
      ...current,
      projectTitle: state.projects.get(projectId)?.title ?? current.projectTitle,
      projectStage: state.projects.get(projectId)?.stage ?? current.projectStage,
      job: {
        ...current.job,
        status: "completed",
        errorCode: null,
        errorMessage: null,
        updatedAt: new Date().toISOString(),
        completedAt: new Date().toISOString(),
      },
      currentStep: null,
      recoveryPath: current.redirectPath,
      isActive: false,
      isCompleted: true,
      hasFailed: false,
    }));
  } catch {
    return;
  }
}

export async function mockQuickCreateProject(
  payload: QuickCreateProjectPayload,
): Promise<QuickCreateProjectResponse> {
  if (!isMockMode()) {
    return liveQuickCreateProject(payload);
  }

  const starterTemplate = payload.templateId
    ? state.templates.find((template) => template.id === payload.templateId)
    : null;
  const starterLabel = starterTemplate?.name ?? "Studio Default";
  const created = await mockCreateProject({
    title: fallbackProjectTitleFromIdea(payload.ideaPrompt),
    client: "",
  });

  if (starterTemplate) {
    created.tags = Array.from(new Set([...created.tags, starterTemplate.style.toLowerCase()]));
    created.nextMilestone = `Applying ${starterTemplate.name} starter defaults`;
    created.updatedAt = new Date().toISOString();
    state.projects.set(created.id, created);
  }

  const queued = updateMockQuickCreateStatus(created.id, (current) => current);
  void runMockQuickCreate(created.id, payload, starterLabel);

  return {
    projectId: created.id,
    projectTitle: created.title,
    redirectPath: `/app/projects/${created.id}/quick-start`,
    job: queued.job,
  };
}

export async function mockGetQuickCreateStatus(projectId: string): Promise<QuickCreateStatus> {
  if (!isMockMode()) {
    return liveGetQuickCreateStatus(projectId);
  }
  await randomDelay(120, 240);
  const status = state.quickCreateStatuses.get(projectId);
  if (!status) {
    throw new Error("No quick-create job exists for this project.");
  }
  return {
    ...status,
    projectTitle: state.projects.get(projectId)?.title ?? status.projectTitle,
    projectStage: state.projects.get(projectId)?.stage ?? status.projectStage,
  };
}

export async function mockGetBrief(projectId: string): Promise<BriefData> {
  if (!isMockMode()) {
    return liveGetBrief(projectId);
  }
  await randomDelay(100, 300);
  const brief = state.briefs.get(projectId);
  if (!brief) throw new Error(`Brief for ${projectId} not found`);
  return brief;
}

export async function mockUpdateBrief(projectId: string, data: Partial<BriefData>): Promise<BriefData> {
  if (!isMockMode()) {
    return liveUpdateBrief(projectId, data);
  }
  await randomDelay(200, 400);
  const existing = state.briefs.get(projectId);
  if (!existing) throw new Error(`Brief for ${projectId} not found`);
  const updated = { ...existing, ...data };
  state.briefs.set(projectId, updated);

  // Update project hook/objective from brief
  const project = state.projects.get(projectId);
  if (project) {
    if (data.hook) project.hook = data.hook;
    if (data.objective) project.objective = data.objective;
    project.updatedAt = new Date().toISOString();
    state.projects.set(projectId, project);
  }

  return updated;
}

/* ─── Ideas API ───────────────────────────────────────────────────────────── */
export async function mockGetIdeas(projectId: string): Promise<IdeaSet | null> {
  if (!isMockMode()) {
    return liveGetIdeas(projectId);
  }
  await randomDelay(100, 200);
  return state.ideaSets.get(projectId) ?? null;
}

export async function mockGenerateIdeas(projectId: string): Promise<IdeaSet> {
  if (!isMockMode()) {
    return liveGenerateIdeas(projectId);
  }
  // Mark as generating
  const pendingSet: IdeaSet = {
    id: nextId("ideaset"),
    projectId,
    status: "running",
    ideas: [],
    generatedAt: null,
  };
  state.ideaSets.set(projectId, pendingSet);

  // Simulate generation delay
  await delay(2000 + Math.random() * 1500);

  // Pick 5-6 random ideas from templates
  const count = 5 + Math.floor(Math.random() * 2);
  const shuffled = [...ideaTemplates].sort(() => Math.random() - 0.5);
  const ideas: IdeaCandidate[] = shuffled.slice(0, count).map((template) => ({
    ...template,
    id: nextId("idea"),
  }));

  const completedSet: IdeaSet = {
    ...pendingSet,
    status: "completed",
    ideas,
    generatedAt: new Date().toISOString(),
  };
  state.ideaSets.set(projectId, completedSet);

  // Update project stage
  const project = state.projects.get(projectId);
  if (project) {
    project.stage = "ideas";
    project.nextMilestone = "Select a viral idea";
    project.updatedAt = new Date().toISOString();
    state.projects.set(projectId, project);
  }

  return completedSet;
}

export async function mockSelectIdea(projectId: string, ideaId: string): Promise<ProjectSummary> {
  if (!isMockMode()) {
    return liveSelectIdea(projectId, ideaId);
  }
  await randomDelay(200, 400);
  const project = state.projects.get(projectId);
  if (!project) throw new Error(`Project ${projectId} not found`);

  const ideaSet = state.ideaSets.get(projectId);
  if (!ideaSet) throw new Error("No ideas generated yet");

  const idea = ideaSet.ideas.find((i) => i.id === ideaId);
  if (!idea) throw new Error(`Idea ${ideaId} not found`);

  project.selectedIdeaId = ideaId;
  project.hook = idea.hook;
  project.nextMilestone = "Generate script from selected idea";
  project.updatedAt = new Date().toISOString();
  state.projects.set(projectId, project);

  return project;
}

/* ─── Script API ──────────────────────────────────────────────────────────── */
export async function mockGetScript(projectId: string): Promise<ScriptData | null> {
  if (!isMockMode()) {
    return liveGetScript(projectId);
  }
  await randomDelay(100, 200);
  return state.scripts.get(projectId) ?? null;
}

export async function mockGenerateScript(projectId: string): Promise<ScriptData> {
  if (!isMockMode()) {
    return liveGenerateScript(projectId);
  }
  await delay(2500 + Math.random() * 2000);

  const project = state.projects.get(projectId);
  if (!project) throw new Error(`Project ${projectId} not found`);

  const ideaSet = state.ideaSets.get(projectId);
  if (!ideaSet || !project.selectedIdeaId) throw new Error("No idea selected");

  const idea = ideaSet.ideas.find((i) => i.id === project.selectedIdeaId);
  if (!idea) throw new Error("Selected idea not found");

  const brief = state.briefs.get(projectId);
  if (!brief) throw new Error("Brief not found");

  const script = generateScriptFromIdea(idea, brief);
  state.scripts.set(projectId, script);

  project.stage = "script";
  project.sceneCount = script.lines.length;
  project.durationSec = script.lines.reduce((sum, l) => sum + l.durationSec, 0);
  project.nextMilestone = "Review and approve script";
  project.updatedAt = new Date().toISOString();
  state.projects.set(projectId, project);

  return script;
}

export async function mockUpdateScript(projectId: string, updates: Partial<ScriptData>): Promise<ScriptData> {
  if (!isMockMode()) {
    return liveUpdateScript(projectId, updates);
  }
  await randomDelay(200, 400);
  const existing = state.scripts.get(projectId);
  if (!existing) throw new Error("No script to update");

  const updated: ScriptData = {
    ...existing,
    ...updates,
    lastEdited: new Date().toISOString(),
    versionLabel: existing.versionLabel.replace("generated", "edited"),
  };
  state.scripts.set(projectId, updated);
  return updated;
}

export async function mockApproveScript(projectId: string): Promise<ScriptData> {
  if (!isMockMode()) {
    return liveApproveScript(projectId);
  }
  await randomDelay(200, 400);
  const existing = state.scripts.get(projectId);
  if (!existing) throw new Error("No script to approve");

  const updated: ScriptData = {
    ...existing,
    approvalState: "approved",
    lastEdited: new Date().toISOString(),
  };
  state.scripts.set(projectId, updated);

  const project = state.projects.get(projectId);
  if (project) {
    project.nextMilestone = "Proceed to scene planning";
    project.updatedAt = new Date().toISOString();
    state.projects.set(projectId, project);
  }

  return updated;
}

/* ─── Shell / Dashboard (reuse existing static data shape) ────────────────── */
export async function mockGetShellData(): Promise<ShellData> {
  if (!isMockMode()) {
    return liveGetShellData();
  }
  await randomDelay(100, 300);
  return {
    user: state.user,
    workspaces: state.workspaces,
    projects: Array.from(state.projects.values()),
    alerts: [
      { id: "a1", label: "Queue healthy", detail: "All workers responsive, no stuck jobs", tone: "success" },
      { id: "a2", label: "Credits at 70%", detail: `${state.workspaces[0].creditsRemaining} credits remaining this cycle`, tone: "warning" },
    ],
  };
}

export async function mockGetDashboardData(): Promise<DashboardData> {
  if (!isMockMode()) {
    return liveGetDashboardData();
  }
  await randomDelay(200, 500);
  const projects = Array.from(state.projects.values());
  const focusProject = projects[0] ?? makeSeedProject("empty", "No projects yet", "brief");

  return {
    focusProject,
    metrics: [
      { label: "Active projects", value: String(projects.length), detail: "In this workspace", tone: "primary" },
      { label: "Credits remaining", value: String(state.workspaces[0].creditsRemaining), detail: `of ${state.workspaces[0].creditsTotal} total`, tone: "success" },
      { label: "Queue depth", value: String(state.workspaces[0].queueCount), detail: "Jobs in pipeline", tone: "neutral" },
      { label: "Workspace plan", value: state.workspaces[0].plan, detail: `${state.workspaces[0].seats} seats`, tone: "primary" },
    ],
    notifications: [
      { id: "n1", label: "Queue healthy", detail: "All workers responding", tone: "success" },
    ],
    queueOverview: [
      { label: "Planning", value: "0", detail: "Idea + script generation", tone: "neutral" },
      { label: "Render", value: "0", detail: "Image + video generation", tone: "neutral" },
    ],
    compositionRules: [
      { id: "c1", label: "Source audio policy", status: "pass", detail: "Strip provider audio before composition" },
      { id: "c2", label: "Loudness target", status: "pass", detail: "-14 LUFS integrated" },
      { id: "c3", label: "Duration bounds", status: "pass", detail: "60-120 second target range" },
    ],
    recentProjects: projects.slice(0, 5),
  };
}

/* ─── Stub APIs for pages not yet interactive ─────────────────────────────── */
export async function mockGetBillingData(): Promise<BillingData> {
  if (!isMockMode()) {
    return liveGetBillingData();
  }
  await randomDelay();
  return {
    planName: "Pro",
    cycleLabel: "March 2026",
    creditsRemaining: 842,
    creditsTotal: 1200,
    projectedSpend: "$380",
    usageBreakdown: [
      { category: "Image generation", usage: "124 pairs", unitCost: "10 credits", total: "1,240 credits" },
      { category: "Video generation", usage: "62 clips", unitCost: "20 credits", total: "1,240 credits" },
    ],
    invoices: [
      { id: "inv_1", label: "March 2026", amount: "$49.00", date: "2026-03-01", status: "paid" },
    ],
  };
}

export async function mockGetPresets(): Promise<PresetCard[]> {
  if (!isMockMode()) {
    return liveGetPresets();
  }
  await randomDelay();
  return [
    { id: "vp_1", name: "Warm Cinematic", category: "visual", description: "Golden hour tones with filmic grain", tags: ["warm", "cinematic"], status: "active" },
    { id: "vp_2", name: "Confident Narrator", category: "voice", description: "Clear, authoritative male voice at natural pace", tags: ["male", "confident"], status: "active", voice: "en-US-Guy" },
  ];
}

// Replaced by global template library

export async function mockGetSettings(): Promise<SettingsSection[]> {
  if (!isMockMode()) {
    return liveGetSettings();
  }
  await randomDelay();
  return [
    { title: "Workspace", description: "General workspace configuration", items: [{ label: "Name", value: "North Star Studio" }, { label: "Plan", value: "Pro" }] },
  ];
}

/* ─── Scene Planning API (Phase 2) ────────────────────────────────────────── */

const WORDS_PER_SECOND = 2.4; // natural reading pace
const MAX_SEGMENT_DURATION = 8;
const MIN_TOTAL_DURATION = 60;
const MAX_TOTAL_DURATION = 120;

function estimateDuration(wordCount: number): number {
  return Math.round((wordCount / WORDS_PER_SECOND) * 10) / 10;
}

function durationWarning(durationSec: number, totalDuration?: number): string | null {
  if (durationSec > MAX_SEGMENT_DURATION) return `Segment exceeds ${MAX_SEGMENT_DURATION}s (est. ${durationSec}s)`;
  if (totalDuration !== undefined) {
    if (totalDuration < MIN_TOTAL_DURATION) return `Total duration ${totalDuration}s is below ${MIN_TOTAL_DURATION}s minimum`;
    if (totalDuration > MAX_TOTAL_DURATION) return `Total duration ${totalDuration}s exceeds ${MAX_TOTAL_DURATION}s maximum`;
  }
  return null;
}

export async function mockGetScenePlan(projectId: string): Promise<ScenePlanSet | null> {
  if (!isMockMode()) {
    return liveGetScenePlan(projectId);
  }
  await randomDelay(100, 200);
  return state.scenePlanSets.get(projectId) ?? null;
}

export async function mockSegmentScript(projectId: string): Promise<SceneSegment[]> {
  await delay(1500 + Math.random() * 1000);

  const script = state.scripts.get(projectId);
  if (!script) throw new Error("No script to segment");

  // Group script lines into 5-8 second segments
  const segments: SceneSegment[] = script.lines.map((line, index) => {
    const wordCount = line.narration.split(/\s+/).length;
    const estDuration = estimateDuration(wordCount);
    return {
      id: nextId("seg"),
      index: index + 1,
      narration: line.narration,
      caption: line.caption,
      estimatedDurationSec: estDuration,
      estimatedWordCount: wordCount,
      durationWarning: durationWarning(estDuration),
      sourceLineIds: [line.id],
    };
  });

  return segments;
}

const sceneGenerationData = [
  { shotType: "Macro hero", motion: "Slow push-in", palette: "Frosted cobalt / ivory", audioCue: "Music enters, narration ducks" },
  { shotType: "Editorial tabletop", motion: "Parallax drift", palette: "Pale steel / powder blue", audioCue: "Narration drives, music ducks" },
  { shotType: "Split-screen compare", motion: "Horizontal wipe", palette: "Warm amber / cool blue", audioCue: "Rhythmic transitions on beat" },
  { shotType: "Real-time demo", motion: "Handheld track", palette: "Natural daylight / warm", audioCue: "Energy builds with voice" },
  { shotType: "Testimonial montage", motion: "Quick cuts", palette: "Warm neutrals", audioCue: "Warm bed, subtle builds" },
  { shotType: "Product beauty shot", motion: "Slow dolly", palette: "Gradient glow / dark", audioCue: "Urgent CTA rhythm" },
  { shotType: "Brand slate", motion: "Static settle", palette: "Brand palette / clean", audioCue: "Music tail sustains" },
  { shotType: "Overhead vanity", motion: "Top-down glide", palette: "Fog white / soft cobalt", audioCue: "Ambient pause" },
];

const gradients = [
  "linear-gradient(145deg, #edf4ff 0%, #c9d8ff 40%, #fdfdff 100%)",
  "linear-gradient(145deg, #f4f8ff 0%, #d7e2ff 48%, #f7fbff 100%)",
  "linear-gradient(145deg, #eef5ff 0%, #cfdcff 46%, #ffffff 100%)",
  "linear-gradient(145deg, #f7faff 0%, #dde8ff 42%, #ffffff 100%)",
  "linear-gradient(145deg, #fff8f0 0%, #ffe8d0 44%, #fff 100%)",
  "linear-gradient(145deg, #f0f6ff 0%, #dce7ff 40%, #eef2ff 100%)",
  "linear-gradient(145deg, #ffffff 0%, #dbe6ff 44%, #f3f7ff 100%)",
  "linear-gradient(145deg, #eef6ff 0%, #d7e5ff 44%, #f8fbff 100%)",
];

export async function mockGenerateScenePlan(projectId: string): Promise<ScenePlanSet> {
  if (!isMockMode()) {
    return liveGenerateScenePlan(projectId);
  }
  await delay(2000 + Math.random() * 1500);

  const script = state.scripts.get(projectId);
  if (!script) throw new Error("No script found");
  const brief = state.briefs.get(projectId);

  // Get or create segments
  let existingPlan = state.scenePlanSets.get(projectId);
  let segments = existingPlan?.segments;
  if (!segments || segments.length === 0) {
    segments = await mockSegmentScript(projectId);
  }

  const scenes: ScenePlan[] = segments.map((seg, index) => {
    const meta = sceneGenerationData[index % sceneGenerationData.length];
    const beatTitle = script.lines[index]?.beat ?? `Scene ${index + 1}`;
    return {
      id: nextId("scene"),
      index: index + 1,
      title: beatTitle,
      beat: seg.narration.substring(0, 60) + (seg.narration.length > 60 ? "…" : ""),
      shotType: meta.shotType,
      motion: meta.motion,
      prompt: `${meta.shotType} shot: ${seg.narration.substring(0, 80)}`,
      startImagePrompt: `Opening frame — ${meta.shotType.toLowerCase()}, ${state.brandKits[0]?.brandNorthStar ?? brief?.brandNorthStar ?? "premium editorial"}, establishing the scene for: ${seg.narration.substring(0, 50)}`,
      endImagePrompt: `Closing frame — ${meta.motion.toLowerCase()} completing, transitional composition ready for next scene, ${seg.narration.substring(0, 50)}`,
      continuityScore: 85 + Math.floor(Math.random() * 15),
      durationSec: seg.estimatedDurationSec,
      estimatedWordCount: seg.estimatedWordCount,
      durationWarning: seg.durationWarning,
      transitionMode: index === 0 ? "hard_cut" : "crossfade",
      status: "draft",
      keyframeStatus: "Awaiting generation",
      notes: [],
      promptHistory: [],
      palette: state.brandKits[0]?.primaryPalette ?? meta.palette,
      audioCue: meta.audioCue,
      thumbnailLabel: beatTitle.substring(0, 16),
      gradient: gradients[index % gradients.length],
      subtitleStatus: "Draft",
      narration: seg.narration,
      caption: seg.caption,
      visualDirection: script.lines[index]?.visualDirection ?? "",
      voicePacing: script.lines[index]?.voicePacing ?? "",
      version: 1,
    };
  });

  const totalDuration = scenes.reduce((sum, s) => sum + s.durationSec, 0);
  const warningsCount = scenes.filter((s) => s.durationWarning).length;

  // Check total duration warning
  const totalWarning = durationWarning(0, totalDuration);
  if (totalWarning) {
    scenes[scenes.length - 1].durationWarning = totalWarning;
  }

  const planSet: ScenePlanSet = {
    id: nextId("sceneplan"),
    projectId,
    status: "completed",
    approvalState: "draft",
    approvedAt: null,
    scenes,
    segments,
    totalDurationSec: totalDuration,
    warningsCount: warningsCount + (totalWarning ? 1 : 0),
    visualPresetId: null,
    voicePresetId: null,
  };

  state.scenePlanSets.set(projectId, planSet);

  const project = state.projects.get(projectId);
  if (project) {
    project.stage = "scenes";
    project.sceneCount = scenes.length;
    project.durationSec = totalDuration;
    project.nextMilestone = "Review and approve scene plan";
    project.updatedAt = new Date().toISOString();
    state.projects.set(projectId, project);
  }

  return planSet;
}

export async function mockGeneratePromptPairs(projectId: string, sceneId: string): Promise<ScenePlan> {
  if (!isMockMode()) {
    return liveGeneratePromptPairs(projectId, sceneId);
  }
  await delay(1200 + Math.random() * 800);

  const planSet = state.scenePlanSets.get(projectId);
  if (!planSet) throw new Error("No scene plan found");

  const scene = planSet.scenes.find((s) => s.id === sceneId);
  if (!scene) throw new Error(`Scene ${sceneId} not found`);

  // History tracking for Phase 5 lineage
  if (scene.startImagePrompt || scene.endImagePrompt) {
    if (!scene.promptHistory) scene.promptHistory = [];
    scene.promptHistory.unshift(`[${new Date().toLocaleTimeString()}] Start: ${scene.startImagePrompt.substring(0, 40)}... | End: ${scene.endImagePrompt.substring(0, 40)}...`);
  }

  const brief = state.briefs.get(projectId);
  scene.startImagePrompt = `Opening frame — ${scene.shotType.toLowerCase()}, ${state.brandKits[0]?.brandNorthStar ?? brief?.brandNorthStar ?? "premium editorial"}, setting up: ${scene.narration.substring(0, 60)}`;
  scene.endImagePrompt = `Closing frame — ${scene.motion.toLowerCase()} completing, ${state.brandKits[0]?.primaryPalette ?? scene.palette}, transition-ready: ${scene.narration.substring(0, 60)}`;
  scene.status = "review";
  scene.keyframeStatus = "Prompts generated";

  state.scenePlanSets.set(projectId, planSet);
  return scene;
}

export async function mockUpdateScene(projectId: string, sceneId: string, updates: Partial<ScenePlan>): Promise<ScenePlan> {
  if (!isMockMode()) {
    return liveUpdateScene(projectId, sceneId, updates);
  }
  await randomDelay(200, 400);

  const planSet = state.scenePlanSets.get(projectId);
  if (!planSet) throw new Error("No scene plan found");

  const sceneIndex = planSet.scenes.findIndex((s) => s.id === sceneId);
  if (sceneIndex === -1) throw new Error(`Scene ${sceneId} not found`);

  const currentScene = planSet.scenes[sceneIndex];

  // Phase 6: Optimistic Locking simulation
  if (updates.version !== undefined && updates.version < currentScene.version) {
    const error: any = new Error("Conflict: The scene has been modified by someone else.");
    error.status = 409;
    error.currentVersion = currentScene; // Attach current version to error for diffing
    throw error;
  }

  const updated = { ...currentScene, ...updates, version: currentScene.version + 1 };

  // Recalculate duration warning if duration changed
  if (updates.durationSec !== undefined) {
    updated.durationWarning = durationWarning(updates.durationSec);
  }

  planSet.scenes[sceneIndex] = updated;
  planSet.totalDurationSec = planSet.scenes.reduce((sum, s) => sum + s.durationSec, 0);
  planSet.warningsCount = planSet.scenes.filter((s) => s.durationWarning).length;

  state.scenePlanSets.set(projectId, planSet);
  return updated;
}

export async function mockApproveScenePlan(projectId: string): Promise<ScenePlanSet> {
  if (!isMockMode()) {
    return liveApproveScenePlan(projectId);
  }
  await randomDelay(300, 600);

  const planSet = state.scenePlanSets.get(projectId);
  if (!planSet) throw new Error("No scene plan found");

  planSet.approvalState = "approved";
  planSet.approvedAt = new Date().toISOString();
  planSet.scenes.forEach((s) => { s.status = "approved"; });

  state.scenePlanSets.set(projectId, planSet);

  const project = state.projects.get(projectId);
  if (project) {
    project.stage = "renders";
    project.nextMilestone = "Begin render generation";
    project.updatedAt = new Date().toISOString();
    state.projects.set(projectId, project);
  }

  return planSet;
}

/* ─── Preset API (Phase 2) ────────────────────────────────────────────────── */
export async function mockGetVisualPresets(): Promise<VisualPreset[]> {
  if (!isMockMode()) {
    return liveGetVisualPresets();
  }
  await randomDelay(100, 200);
  return [...state.visualPresets];
}

export async function mockGetVoicePresets(): Promise<VoicePreset[]> {
  if (!isMockMode()) {
    return liveGetVoicePresets();
  }
  await randomDelay(100, 200);
  return [...state.voicePresets];
}

export async function mockCreateVisualPreset(preset: Omit<VisualPreset, "id">): Promise<VisualPreset> {
  if (!isMockMode()) {
    return liveCreateVisualPreset(preset);
  }
  await randomDelay(200, 400);
  const created: VisualPreset = { ...preset, id: nextId("vp") };
  state.visualPresets.push(created);
  return created;
}

export async function mockCreateVoicePreset(preset: Omit<VoicePreset, "id">): Promise<VoicePreset> {
  if (!isMockMode()) {
    return liveCreateVoicePreset(preset);
  }
  await randomDelay(200, 400);
  const created: VoicePreset = { ...preset, id: nextId("voicep") };
  state.voicePresets.push(created);
  return created;
}

export async function mockSetScenePlanPreset(
  projectId: string,
  type: "visual" | "voice",
  presetId: string,
): Promise<ScenePlanSet> {
  if (!isMockMode()) {
    return liveSetScenePlanPreset(projectId, type, presetId);
  }
  await randomDelay(100, 200);
  const planSet = state.scenePlanSets.get(projectId);
  if (!planSet) throw new Error("No scene plan found");

  if (type === "visual") planSet.visualPresetId = presetId;
  else planSet.voicePresetId = presetId;

  state.scenePlanSets.set(projectId, planSet);
  return planSet;
}

/* ─── Render MVP Simulator (Phase 3) ──────────────────────────────────────── */

export async function mockGetRenders(projectId: string): Promise<RenderJob[]> {
  if (!isMockMode()) {
    return liveGetRenders(projectId);
  }
  await randomDelay(100, 200);
  // Using the active one mapped to this projectId (we use single job per project in mock)
  const job = state.renderJobs.get(projectId);
  return job ? [job] : [];
}

export async function mockGetExports(projectId: string): Promise<ExportArtifact[]> {
  if (!isMockMode()) {
    return liveGetExports(projectId);
  }
  await randomDelay(100, 200);
  return state.exports.get(projectId) || [];
}

export async function mockCancelRender(projectId: string): Promise<void> {
  if (!isMockMode()) {
    return liveCancelRender(projectId);
  }
  await randomDelay(100, 200);
  const job = state.renderJobs.get(projectId);
  if (job && job.status === "running") {
    job.status = "failed";
    job.sseState = "Cancelled";
    job.nextAction = "Render was cancelled by user.";
    job.events.push({ id: nextId("evt"), time: new Date().toLocaleTimeString(), label: "Cancelled", detail: "Job cancelled by user override", tone: "error" });
    state.renderJobs.set(projectId, job);
  }
}

export async function mockRetryRenderStep(projectId: string, stepId: string): Promise<RenderJob> {
  if (!isMockMode()) {
    return liveRetryRenderStep(projectId, stepId);
  }
  await randomDelay(200, 400);
  const job = state.renderJobs.get(projectId);
  if (!job) throw new Error("Render job not found");

  const step = job.steps.find((s) => s.id === stepId);
  if (!step) throw new Error("Step not found");

  step.status = "running";
  step.clipStatus = "Retrying";
  step.nextAction = "Waiting for generation";
  
  // Also clear job error if it was blocked
  job.status = "running";
  job.sseState = "Live SSE connected";
  job.nextAction = "Processing retried step";
  job.events.push({ id: nextId("evt"), time: new Date().toLocaleTimeString(), label: "Step Retried", detail: `User requested retry for step ${step.name}`, tone: "warning" });
  state.renderJobs.set(projectId, job);

  // Resume simulator loop if it was blocked
  void renderSimulatorLoop(projectId);

  return job;
}

// Spawns the SSE Simulator
export async function mockStartRender(
  projectId: string,
  settings?: { subtitleStyle?: string; musicDucking?: string; musicTrack?: string; animationEffect?: string }
): Promise<RenderJob> {
  if (!isMockMode()) {
    return liveStartRender(projectId, settings as { subtitleStyle: string; musicDucking: string; musicTrack: string; animationEffect: string } | undefined);
  }
  await randomDelay(300, 600);
  const planSet = state.scenePlanSets.get(projectId);
  const project = state.projects.get(projectId);
  if (!planSet || !project) throw new Error("Invalid project or scene plan");

  project.stage = "renders";
  state.projects.set(projectId, project);

  const steps: RenderStep[] = planSet.scenes.map((scene, i) => ({
    id: nextId("step"),
    sceneId: `Scene ${i + 1}`,
    name: scene.shotType || "Shot",
    status: "draft",
    durationDeltaSec: 0,
    clipStatus: "Queued",
    narrationStatus: "Queued",
    consistency: "Pending",
    nextAction: "Waiting for queue",
  }));

  const job: RenderJob = {
    id: `render_${projectId}`,
    label: `Render ${Math.floor(Math.random() * 100)} · Master vertical export`,
    status: "running",
    progress: 0,
    createdAt: new Date().toLocaleTimeString(),
    updatedAt: new Date().toLocaleTimeString(),
    durationSec: planSet.totalDurationSec,
    transitionMode: "crossfade",
    voicePreset: "Ava Editorial",
    consistencyPackSnapshotId: `cps_${projectId}_${Date.now()}`,
    sseState: "Live SSE connected",
    nextAction: "Initializing pipelines...",
    musicTrack: settings?.musicTrack || "Ambient Corporate 1",
    allowExportWithoutMusic: false,
    exportUrl: null,
    checks: [
      { id: "c1", label: "Consistency pack provenance", status: "pass", detail: "All clips reference locked snapshot." },
    ],
    steps,
    events: [
      { id: nextId("evt"), time: new Date().toLocaleTimeString(), label: "Job Created", detail: "Render job queued for execution", tone: "neutral" }
    ],
    metrics: { 
      lufsTarget: "-14 LUFS", 
      truePeak: "-1.0 dBTP", 
      musicDucking: settings?.musicDucking || "-12 dB", 
      subtitleState: "Burned",
      subtitleStyle: settings?.subtitleStyle || "Default"
    }
  };

  state.renderJobs.set(projectId, job);

  // Fire and forget simulator loop
  void renderSimulatorLoop(projectId);
  
  return job;
}

// Background simulator loop mutating the state dynamically.
// This mocks SSE stream architecture.
export async function renderSimulatorLoop(projectId: string) {
  const job = state.renderJobs.get(projectId);
  if (!job) return;

  const pushEvent = (label: string, detail: string, tone: "neutral"| "success"| "warning"| "error") => {
    job.events.unshift({ id: nextId("evt"), time: new Date().toLocaleTimeString(), label, detail, tone });
    if (job.events.length > 5) job.events.pop();
  };

  pushEvent("Pipeline Started", "Orchestrator resolving consistency pack", "neutral");
  job.nextAction = "Generating scene frames";
  state.renderJobs.set(projectId, { ...job });

  const totalSteps = job.steps.length;
  // 3 phases per step: Prompts -> Audio -> Clip -> Done
  const TICK_MS = 1500;
  
  for (let i = 0; i < totalSteps; i++) {
    const step = job.steps[i];
    
    if (job.status !== "running") return; // Cancelled
    
    // 1. Image Generation
    await new Promise(r => setTimeout(r, TICK_MS));
    if (job.status !== "running") return;
    step.status = "running";
    step.clipStatus = "Generating frames...";
    step.nextAction = "Awaiting image pair";
    job.progress = Math.floor((i / totalSteps) * 100) + 5;
    state.renderJobs.set(projectId, { ...job });

    // 2. Audio Generation
    await new Promise(r => setTimeout(r, TICK_MS));
    if (job.status !== "running") return;
    step.narrationStatus = "Synthesizing";
    step.nextAction = "Generating video clip";
    job.progress = Math.floor((i / totalSteps) * 100) + 10;
    state.renderJobs.set(projectId, { ...job });

    // 3. Render Clip
    await new Promise(r => setTimeout(r, TICK_MS));
    if (job.status !== "running") return;
    
    // Simulate Moderation Block (random high chance on first step for testing)
    if (i === 0 && !step.name.includes("Fixed") && Math.random() > 0.5) {
      step.status = "blocked";
      step.clipStatus = "Flagged";
      step.narrationStatus = "Generated";
      step.name += " (Blocked)";
      step.nextAction = "Awaiting manual operator review";
      
      job.status = "blocked";
      job.sseState = "Halted on moderation block";
      job.nextAction = "Admin review required for flagged content.";
      pushEvent("Moderation Block", `Scene ${i+1} flagged by trust and safety heuristics`, "warning");
      state.renderJobs.set(projectId, { ...job });
      return; 
    }

    // Random intermittent failure check
    // If it's the second scene and we haven't failed yet, fail it manually
    if (i === 1 && !step.name.includes("Fixed")) {
      step.status = "failed";
      step.clipStatus = "Failed";
      step.narrationStatus = "Generated";
      step.name += " (Failed)";
      step.nextAction = "Click retry to rerun clip pipeline";
      
      job.status = "failed";
      job.sseState = "Halted on scene error";
      job.nextAction = `Review Scene ${i+1} and retry.`;
      pushEvent("Pipeline Fault", `Scene ${i+1} semantic collision in transition`, "error");
      state.renderJobs.set(projectId, { ...job });
      
      // Stop the loop completely, UI must call retry!
      return; 
    }

    // Success path for step
    step.name = step.name.replace(" (Failed)", " (Fixed)").replace(" (Blocked)", " (Fixed)"); 
    step.status = "completed";
    step.clipStatus = "Rendered";
    step.narrationStatus = "Aligned";
    step.consistency = "Matched";
    step.nextAction = "Complete";
    job.progress = Math.floor(((i + 1) / totalSteps) * 100) - 2;
    pushEvent("Scene Completed", `Frames and clip encoded for Scene ${i+1}`, "success");

    // Deduct Cost 
    const cost = step.creditCost || 5;
    const ws = state.workspaces.find(w => w.id === state.activeWorkspaceId);
    if (ws) {
      ws.creditsRemaining -= cost;
      state.usageRecords.push({
        id: nextId("usr"),
        projectId,
        description: `Scene ${i+1} compute`,
        credits: cost,
        timestamp: new Date().toLocaleTimeString()
      });
    }

    state.renderJobs.set(projectId, { ...job });
  }

  // 4. Composition (FFmpeg)
  await new Promise(r => setTimeout(r, TICK_MS * 2));
  if (job.status !== "running") return;
  
  job.nextAction = "Composing master audio bed...";
  job.progress = 95;
  pushEvent("Composition Pipeline", "Normalizing audio and adding background tracks", "neutral");
  state.renderJobs.set(projectId, { ...job });

  await new Promise(r => setTimeout(r, TICK_MS * 2));
  if (job.status !== "running") return;
  job.progress = 100;
  job.status = "completed";
  job.sseState = "Disconnected (Clean close)";
  job.nextAction = "Export complete.";
  pushEvent("Job Complete", "Master vertical export wrapped successfully", "success");
  
  // Push an export artifact
  const newExport: ExportArtifact = {
    id: nextId("exp"),
    name: "Master HD Export",
    createdAt: new Date().toLocaleDateString(),
    status: "ready",
    durationSec: job.durationSec,
    sizeMb: 14.5,
    format: "MP4 / H.264",
    ratio: "9:16",
    destination: "Local File System",
    downloadUrl: null,
    integratedLufs: -14.2,
    truePeak: -1.0,
    subtitles: true,
    musicBed: true,
    gradient: "linear-gradient(135deg, #101014 0%, #151520 100%)"
  };
  const exps = state.exports.get(projectId) || [];
  exps.unshift(newExport);
  state.exports.set(projectId, exps);
  
  state.renderJobs.set(projectId, { ...job });
}


/* ─── Phase 4: Billing & Admin API Exports ────────────────────────────────── */

export async function mockGetBilling(): Promise<BillingData> {
  if (!isMockMode()) {
    return liveGetBilling();
  }
  await delay(400);
  const ws = state.workspaces.find(w => w.id === state.activeWorkspaceId)!;
  const totalUsage = state.usageRecords.reduce((sum, rec) => sum + rec.credits, 0);

  return {
    planName: ws.plan,
    cycleLabel: "Mar 1 - Mar 31",
    creditsRemaining: ws.creditsRemaining,
    creditsTotal: ws.creditsTotal,
    projectedSpend: "$" + ((totalUsage / 100) * 1.5).toFixed(2), // purely mock math
    usageBreakdown: [
      { category: "Hosted Generation", usage: `${state.usageRecords.length} calls`, unitCost: "5 credits", total: `${totalUsage} credits` },
      { category: "BYO Key (API Call)", usage: "12 calls", unitCost: "1 credit", total: "12 credits" },
      { category: "Local Worker (Edge)", usage: "85 tasks", unitCost: "0 credits", total: "0 credits" },
    ],
    invoices: state.invoices,
  };
}

export async function mockGetAdminQueue(): Promise<AdminQueueItem[]> {
  if (!isMockMode()) {
    return liveGetAdminQueue();
  }
  await delay(300);
  const queue: AdminQueueItem[] = [];
  for (const [projectId, job] of state.renderJobs.entries()) {
    if (job.status === "failed" || job.status === "blocked") {
      const failingStep = job.steps.find(s => s.status === "failed" || s.status === "blocked");
      queue.push({
        id: job.id,
        workspace: "North Star Studio",
        project: projectId,
        step: failingStep?.name || "Pipeline",
        status: job.status,
        retries: failingStep?.name.includes("Fixed") ? 1 : 0,
        owner: "System",
        age: "2m",
        provider: "Kling / ElevenLabs",
      });
    }
  }
  return queue;
}

export async function mockApproveQueueItem(jobId: string): Promise<void> {
  if (!isMockMode()) {
    return liveApproveQueueItem(jobId);
  }
  await delay(400);
  for (const [projectId, job] of state.renderJobs.entries()) {
    if (job.id === jobId) {
      const blockedStep = job.steps.find(s => s.status === "blocked");
      if (blockedStep) {
        blockedStep.status = "running";
        blockedStep.clipStatus = "Generating frames...";
        blockedStep.nextAction = "Resuming from moderation";
      }
      job.status = "running";
      job.sseState = "Operator forced release";
      job.nextAction = "Resuming from checkpoint.";
      state.renderJobs.set(projectId, { ...job });
      
      void renderSimulatorLoop(projectId);
      break;
    }
  }
}

export async function mockRejectQueueItem(jobId: string): Promise<void> {
  if (!isMockMode()) {
    return liveRejectQueueItem(jobId);
  }
  await delay(400);
  for (const [projectId, job] of state.renderJobs.entries()) {
    if (job.id === jobId) {
      job.status = "failed";
      job.sseState = "Operator rejected content";
      job.nextAction = "Job permanently halted due to policy violation.";
      state.renderJobs.set(projectId, { ...job });
      break;
    }
  }
}

export async function mockGetAdminWorkspaces(): Promise<AdminWorkspaceRow[]> {
  if (!isMockMode()) {
    return liveGetAdminWorkspaces();
  }
  await delay(300);
  return state.workspaces.map(ws => ({
    id: ws.id,
    name: ws.name,
    plan: ws.plan,
    seats: ws.seats,
    creditsRemaining: ws.creditsRemaining.toString(),
    renderLoad: "Normal",
    health: "Healthy",
    renewalDate: "2026-04-01"
  }));
}

export async function mockGetAdminRenders(): Promise<AdminRenderRow[]> {
  if (!isMockMode()) {
    return liveGetAdminRenders();
  }
  await delay(300);
  const renders: AdminRenderRow[] = [];
  for (const [projectId, job] of state.renderJobs.entries()) {
     renders.push({
       id: job.id,
       project: projectId,
       workspace: "North Star",
       status: job.status,
       provider: "Kling",
       cost: (job.progress > 0 ? "15 credits" : "0 credits"),
       stuckFor: (job.status === "failed" || job.status === "blocked") ? "2m" : "-",
       issue: job.sseState,
       snapshot: job.consistencyPackSnapshotId,
     });
  }
  return renders;
}

/* ─── Phase 5: Polish & Ecosystem ─────────────────────────────────────────── */

export async function mockGetAssets(): Promise<AssetRecord[]> {
  if (!isMockMode()) {
    return liveGetAssets();
  }
  await randomDelay(300, 500);
  return state.assets;
}

export async function mockGetTemplates(): Promise<TemplateCard[]> {
  if (!isMockMode()) {
    return liveGetTemplates();
  }
  await randomDelay(300, 500);
  return state.templates;
}

export async function mockCloneTemplate(templateId: string): Promise<string> {
  if (!isMockMode()) {
    return liveCloneTemplate(templateId);
  }
  await randomDelay(800, 1200);
  const template = state.templates.find(t => t.id === templateId);
  if (!template) throw new Error("Template not found");

  const newProjectId = nextId("project_cloned");
  const newProject = makeSeedProject(newProjectId, `Copy of ${template.name}`, "brief");
  
  // Clone brief structure
  const clonedBrief = { ...seedBrief };
  clonedBrief.objective = `Based on ${template.name}`;
  
  state.projects.set(newProjectId, newProject);
  state.briefs.set(newProjectId, clonedBrief);
  
  return newProjectId;
}

/* ─── Phase 6: Collaboration & Studio ─────────────────────────────────────── */

export async function mockGetBrandKits(): Promise<BrandKit[]> {
  if (!isMockMode()) {
    return liveGetBrandKits();
  }
  await randomDelay(300, 500);
  return state.brandKits;
}

export async function mockSaveBrandKit(kit: BrandKit): Promise<BrandKit> {
  if (!isMockMode()) {
    return liveSaveBrandKit(kit);
  }
  await randomDelay(400, 800);
  const existing = state.brandKits.findIndex((b) => b.id === kit.id);
  if (existing >= 0) {
    state.brandKits[existing] = kit;
  } else {
    kit.id = nextId("bk");
    state.brandKits.push(kit);
  }
  return kit;
}

export async function mockGetComments(
  targetId: string,
  options: { projectId?: string; targetType?: string } = {},
): Promise<Comment[]> {
  if (!isMockMode()) {
    return liveGetComments(targetId, options);
  }
  await randomDelay(200, 400);
  return state.comments.filter((c) => c.targetId === targetId);
}

export async function mockAddComment(
  targetId: string,
  text: string,
  options: { projectId?: string; targetType?: string } = {},
): Promise<Comment> {
  if (!isMockMode()) {
    return liveAddComment(targetId, text, options);
  }
  await randomDelay(300, 600);
  const newComment: Comment = {
    id: nextId("comment"),
    targetId,
    authorName: state.user.name,
    text,
    timestamp: new Date().toISOString(),
    resolved: false,
  };
  state.comments.push(newComment);
  return newComment;
}

export async function mockResolveComment(commentId: string): Promise<void> {
  if (!isMockMode()) {
    return liveResolveComment(commentId);
  }
  await randomDelay(200, 400);
  const comment = state.comments.find((c) => c.id === commentId);
  if (comment) {
    comment.resolved = true;
  }
}

/* ─── Phase 7: Local & BYO ────────────────────────────────────────────────── */

function legacyProviderFamily(providerKey: string): ProviderKey["provider"] {
  if (providerKey.includes("eleven")) return "elevenlabs";
  if (providerKey.includes("stability")) return "stability";
  if (providerKey.includes("runway") || providerKey.includes("kling") || providerKey.includes("veo")) {
    return "runway";
  }
  return "openai";
}

function defaultMockRoute(modality: ProviderModality): WorkspaceExecutionPolicy[ProviderModality] {
  return {
    ...mockExecutionDefaults[modality],
  };
}

function syncMockProviderCredentialState(): void {
  state.providerCredentials = state.providerCredentials.map((credential) => {
    const activeRoute = state.executionPolicy[credential.modality];
    const isActive = activeRoute.credentialId === credential.id;
    return {
      ...credential,
      isActive,
      activeMode: isActive ? activeRoute.mode : null,
    };
  });
}

function applyMockExecutionRoute(
  modality: ProviderModality,
  providerKey: string,
  credentialId: string | null,
  mode: "hosted" | "byo" | "local",
): WorkspaceExecutionPolicy {
  state.executionPolicy = {
    ...state.executionPolicy,
    [modality]: {
      mode,
      providerKey,
      providerLabel: providerLabelFromKey(providerKey),
      credentialId,
      generationType: generationTypeFromModality(modality),
    },
  };
  syncMockProviderCredentialState();
  return state.executionPolicy;
}

export async function mockGetExecutionPolicy(): Promise<WorkspaceExecutionPolicy> {
  if (!isMockMode()) {
    return liveGetExecutionPolicy();
  }
  await randomDelay(150, 250);
  return { ...state.executionPolicy };
}

export async function mockUpdateExecutionPolicyRoute(
  modality: ProviderModality,
  providerKey: string,
  credentialId: string | null,
  mode: "hosted" | "byo" | "local",
): Promise<WorkspaceExecutionPolicy> {
  if (!isMockMode()) {
    return liveUpdateExecutionPolicyRoute(modality, providerKey, credentialId, mode);
  }
  await randomDelay(150, 250);
  return applyMockExecutionRoute(modality, providerKey, credentialId, mode);
}

export async function mockGetProviderCredentials(): Promise<ProviderCredentialRecord[]> {
  if (!isMockMode()) {
    return liveGetProviderCredentials();
  }
  await randomDelay(200, 400);
  syncMockProviderCredentialState();
  return [...state.providerCredentials];
}

export async function mockCreateProviderCredential(
  input: ProviderCredentialInput,
): Promise<ProviderCredentialRecord> {
  if (!isMockMode()) {
    return liveCreateProviderCredential(input);
  }
  await randomDelay(400, 700);
  const option = getProviderCatalogOption(input.providerKey);
  const created: ProviderCredentialRecord = {
    id: nextId("cred"),
    name: input.name.trim(),
    modality: input.modality,
    generationType: generationTypeFromModality(input.modality),
    providerKey: input.providerKey,
    providerLabel: option?.providerLabel ?? providerLabelFromKey(input.providerKey),
    supportsActivation: option?.supportsActivation ?? false,
    endpoint: input.endpoint?.trim() ?? "",
    apiVersion: input.apiVersion?.trim() ?? "",
    deployment: input.deployment?.trim() ?? "",
    modelName: input.modelName?.trim() ?? "",
    voice: input.voice?.trim() ?? "",
    secretConfigured: Boolean(input.apiKey?.trim()),
    isActive: false,
    activeMode: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    lastUsedAt: null,
    revokedAt: null,
    validationStatus: "not_validated",
    lastValidatedAt: null,
    validationError: null,
  };
  state.providerCredentials = [created, ...state.providerCredentials];
  if (input.setAsActiveRoute && created.supportsActivation) {
    applyMockExecutionRoute(input.modality, input.providerKey, created.id, "byo");
  } else {
    syncMockProviderCredentialState();
  }
  return state.providerCredentials.find((credential) => credential.id === created.id) ?? created;
}

export async function mockUpdateProviderCredential(
  credentialId: string,
  input: ProviderCredentialInput,
): Promise<ProviderCredentialRecord> {
  if (!isMockMode()) {
    return liveUpdateProviderCredential(credentialId, input);
  }
  await randomDelay(300, 600);
  const option = getProviderCatalogOption(input.providerKey);
  state.providerCredentials = state.providerCredentials.map((credential) => {
    if (credential.id !== credentialId) {
      return credential;
    }
    return {
      ...credential,
      name: input.name.trim(),
      modality: input.modality,
      generationType: generationTypeFromModality(input.modality),
      providerKey: input.providerKey,
      providerLabel: option?.providerLabel ?? providerLabelFromKey(input.providerKey),
      supportsActivation: option?.supportsActivation ?? false,
      endpoint: input.endpoint?.trim() ?? "",
      apiVersion: input.apiVersion?.trim() ?? "",
      deployment: input.deployment?.trim() ?? "",
      modelName: input.modelName?.trim() ?? "",
      voice: input.voice?.trim() ?? "",
      secretConfigured: credential.secretConfigured || Boolean(input.apiKey?.trim()),
      updatedAt: new Date().toISOString(),
      validationStatus: "not_validated",
      lastValidatedAt: null,
      validationError: null,
    };
  });
  if (input.setAsActiveRoute && (option?.supportsActivation ?? false)) {
    applyMockExecutionRoute(input.modality, input.providerKey, credentialId, "byo");
  } else {
    syncMockProviderCredentialState();
  }
  const updated = state.providerCredentials.find((credential) => credential.id === credentialId);
  if (!updated) {
    throw new Error("Provider credential not found");
  }
  return updated;
}

export async function mockDeleteProviderCredential(id: string): Promise<void> {
  if (!isMockMode()) {
    return liveDeleteProviderCredential(id);
  }
  await randomDelay(300, 600);
  const credential = state.providerCredentials.find((entry) => entry.id === id);
  state.providerCredentials = state.providerCredentials.filter((entry) => entry.id !== id);
  if (credential && state.executionPolicy[credential.modality].credentialId === id) {
    state.executionPolicy = {
      ...state.executionPolicy,
      [credential.modality]: defaultMockRoute(credential.modality),
    };
  }
  syncMockProviderCredentialState();
}

export async function mockValidateProviderCredential(
  credentialId: string,
): Promise<ProviderCredentialRecord> {
  if (!isMockMode()) {
    return liveValidateProviderCredential(credentialId);
  }
  await randomDelay(250, 400);
  const validationTime = new Date().toISOString();
  state.providerCredentials = state.providerCredentials.map((credential) =>
    credential.id === credentialId
      ? {
          ...credential,
          validationStatus: credential.secretConfigured ? "valid" : "invalid",
          lastValidatedAt: validationTime,
          validationError: credential.secretConfigured ? null : "API key is missing.",
        }
      : credential,
  );
  const updated = state.providerCredentials.find((credential) => credential.id === credentialId);
  if (!updated) {
    throw new Error("Provider credential not found");
  }
  return updated;
}

export async function mockGetProviderKeys(): Promise<ProviderKey[]> {
  if (!isMockMode()) {
    return liveGetProviderKeys();
  }
  await randomDelay(200, 400);
  return state.providerCredentials.map((credential) => ({
    id: credential.id,
    provider: legacyProviderFamily(credential.providerKey),
    keyPrefix: credential.providerKey,
    createdAt: credential.createdAt,
  }));
}

export async function mockAddProviderKey(provider: ProviderKey["provider"], key: string): Promise<ProviderKey> {
  if (!isMockMode()) {
    return liveAddProviderKey(provider, key);
  }
  const created = await mockCreateProviderCredential({
    name: `${provider} credential`,
    modality:
      provider === "openai"
        ? "text"
        : provider === "stability"
          ? "image"
          : provider === "elevenlabs"
            ? "speech"
            : "video",
    providerKey:
      provider === "openai"
        ? "azure_openai_text"
        : provider === "stability"
          ? "stability_image"
          : provider === "elevenlabs"
            ? "elevenlabs_speech"
            : "runway_video",
    apiKey: key,
  });
  return {
    id: created.id,
    provider: legacyProviderFamily(created.providerKey),
    keyPrefix: created.providerKey,
    createdAt: created.createdAt,
  };
}

export async function mockDeleteProviderKey(id: string): Promise<void> {
  if (!isMockMode()) {
    return liveDeleteProviderKey(id);
  }
  await mockDeleteProviderCredential(id);
}

export async function mockGetLocalWorkers(): Promise<LocalWorker[]> {
  if (!isMockMode()) {
    return liveGetLocalWorkers();
  }
  await randomDelay(200, 400);
  return state.localWorkers;
}
