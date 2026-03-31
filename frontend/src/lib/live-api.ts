import { api, ApiError } from "./api-client";
import {
  generationTypeFromModality,
  getProviderCatalogOption,
  providerLabelFromKey,
} from "./provider-catalog";
import type {
  AdminQueueItem,
  AdminRenderRow,
  AdminWorkspaceRow,
  AlertItem,
  AssetRecord,
  AuthSession,
  BrandKit,
  BillingData,
  BriefData,
  Comment,
  CreateProjectPayload,
  DashboardData,
  ExportArtifact,
  IdeaCandidate,
  IdeaSet,
  LocalWorker,
  LoginCredentials,
  PresetCard,
  ProjectBundle,
  ProjectSummary,
  ProviderCredentialInput,
  ProviderCredentialRecord,
  ProviderExecutionRoute,
  ProviderKey,
  ProviderModality,
  ProviderValidationStatus,
  QuickCreateProjectPayload,
  QuickCreateProjectResponse,
  QuickCreateStatus,
  QuickCreateStepStatus,
  QuickCreateJobSummary,
  RenderCheck,
  RenderEvent,
  RenderJob,
  RenderStep,
  ScenePlan,
  ScenePlanSet,
  SceneSegment,
  ScriptData,
  ScriptLine,
  SettingsSection,
  ShellData,
  TemplateCard,
  UserProfile,
  VisualPreset,
  VoicePreset,
  WorkspaceExecutionPolicy,
  WorkspaceSummary,
} from "../types/domain";

type BackendSession = {
  user: {
    id: string;
    email: string;
    full_name: string;
    is_admin: boolean;
  };
  workspaces: Array<{
    member_id: string | null;
    workspace_id: string;
    workspace_name: string;
    role: string;
    is_default: boolean;
    plan_name: string;
  }>;
  active_workspace_id: string;
  active_role: string;
};

type BackendProject = {
  id: string;
  title: string;
  client: string | null;
  aspect_ratio: string;
  duration_target_sec: number;
  stage: string;
  selected_idea_id: string | null;
  updated_at: string;
};

type BackendProjectResponse = {
  id: string;
  workspace_id: string;
  owner_user_id: string;
  source_template_version_id: string | null;
  brand_kit_id: string | null;
  title: string;
  client: string | null;
  aspect_ratio: string;
  duration_target_sec: number;
  subtitle_style_profile: Record<string, unknown>;
  export_profile: Record<string, unknown>;
  audio_mix_profile: Record<string, unknown>;
  stage: string;
  active_brief_id: string | null;
  selected_idea_id: string | null;
  active_script_version_id: string | null;
  active_scene_plan_id: string | null;
  default_visual_preset_id: string | null;
  default_voice_preset_id: string | null;
  archived_at: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
};

type BackendBrief = {
  objective: string;
  hook: string;
  target_audience: string;
  call_to_action: string;
  brand_north_star: string;
  guardrails: string[];
  must_include: string[];
  approval_steps: string[];
};

type BackendIdeaCandidate = {
  id: string;
  title: string;
  hook: string;
  summary: string;
  tags: string[];
  order_index: number;
};

type BackendIdeaSet = {
  id: string;
  project_id: string;
  created_at: string;
  candidates: BackendIdeaCandidate[];
};

type BackendScript = {
  id: string;
  version_number: number;
  version: number;
  approval_state: string;
  total_words: number;
  estimated_duration_seconds: number;
  reading_time_label: string;
  created_at: string;
  lines: Array<{
    id: string;
    scene_id: string;
    beat: string;
    narration: string;
    caption: string;
    duration_sec: number;
    status: string;
    visual_direction: string;
    voice_pacing: string;
  }>;
};

type BackendSceneSegment = {
  id: string;
  scene_index: number;
  source_line_ids: string[];
  title: string;
  beat: string;
  narration_text: string;
  caption_text: string;
  visual_direction: string;
  shot_type: string;
  motion: string;
  target_duration_seconds: number;
  estimated_voice_duration_seconds: number;
  visual_prompt: string;
  start_image_prompt: string;
  end_image_prompt: string;
  transition_mode: "hard_cut" | "crossfade" | string;
  notes: string[];
  validation_warnings: Array<{ message?: string }>;
};

type BackendScenePlan = {
  id: string;
  visual_preset_id: string | null;
  voice_preset_id: string | null;
  version: number;
  version_number: number;
  approval_state: string;
  total_estimated_duration_seconds: number;
  scene_count: number;
  validation_warnings: Array<{ message?: string }>;
  segments: BackendSceneSegment[];
  updated_at: string;
};

type BackendRenderEvent = {
  sequence_number: number;
  at: string;
  event_type: string;
  payload: Record<string, unknown>;
};

type BackendRenderStep = {
  id: string;
  scene_segment_id: string | null;
  step_kind: string;
  status: string;
  output_payload: Record<string, unknown> | null;
  error_code?: string | null;
  error_message?: string | null;
};

type BackendRenderAsset = {
  id: string;
  scene_segment_id: string | null;
  asset_role: string;
  download_url: string | null;
};

type BackendExport = {
  id: string;
  file_name: string;
  status: string;
  format: string;
  object_name: string;
  duration_ms: number | null;
  availability_status: string;
  subtitle_style_profile: Record<string, unknown>;
  audio_mix_profile: Record<string, unknown>;
  download_url: string | null;
  created_at: string;
};

type BackendRender = {
  id: string;
  status: string;
  payload: Record<string, unknown>;
  allow_export_without_music: boolean;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  scene_plan_id: string | null;
  consistency_pack_id: string | null;
  voice_preset_id: string | null;
  steps: BackendRenderStep[];
  assets: BackendRenderAsset[];
  exports: BackendExport[];
};

type BackendNotification = {
  id: string;
  title: string;
  body: string;
  read_at: string | null;
};

type BackendUsageSummary = {
  plan_name: string;
  credits_remaining: number;
  credits_total: number;
  monthly_budget_cents: number;
  current_period_end_at: string | null;
  month_provider_cost_cents: number;
  month_credits_used: number;
  month_export_count: number;
  month_provider_run_count: number;
};

type BackendSubscription = {
  plan_name: string;
  current_period_end_at: string | null;
};

type BackendVisualPreset = {
  id: string;
  name: string;
  description: string;
  style_descriptor: string;
  color_palette: string;
  camera_defaults: string;
};

type BackendVoicePreset = {
  id: string;
  name: string;
  description: string;
  tone_descriptor: string;
  provider_voice: string;
  language_code: string;
};

type BackendTemplate = {
  id: string;
  name: string;
  description: string;
  latest_version: {
    snapshot_payload: Record<string, unknown>;
  } | null;
};

type BackendAsset = {
  id: string;
  asset_type: "image" | "video" | "audio" | string;
  project_id: string | null;
  scene_segment_id: string | null;
  file_name: string;
  download_url: string | null;
  library_label: string | null;
  metadata_payload: Record<string, unknown>;
  created_at: string;
};

type BackendBrandKit = {
  id: string;
  name: string;
  description: string;
  version: number;
  brand_rules: Record<string, unknown>;
};

type BackendComment = {
  id: string;
  project_id: string | null;
  target_type: string;
  target_id: string;
  author_name: string | null;
  body: string;
  resolved_at: string | null;
  created_at: string;
};

type BackendProviderCredential = {
  id: string;
  name: string;
  modality: string;
  provider_key: string;
  public_config: Record<string, unknown>;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
  updated_at: string;
  secret_configured: boolean;
  validation_status: ProviderValidationStatus | null;
  last_validated_at: string | null;
  last_validation_error: string | null;
};

type BackendAdminModerationItem = {
  id: string;
  project_id: string | null;
  target_type: string;
  review_status: string;
  provider_name: string;
  blocked_message: string | null;
  created_at: string;
};

type BackendAdminRenderSummary = {
  id: string;
  workspace_id: string;
  project_id: string;
  status: string;
  queue_name: string;
  retry_count: number;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  step_count: number;
  failed_step_count: number;
  blocked_step_count: number;
  latest_step_kind: string | null;
  latest_provider_cost_cents: number;
  provider_run_count: number;
};

type BackendLocalWorker = {
  id: string;
  name: string;
  status: string;
  supports_ordered_reference_images: boolean;
  supports_first_last_frame_video: boolean;
  supports_tts: boolean;
  last_heartbeat_at: string | null;
};

type BackendProjectDetail = {
  project: BackendProject;
  active_brief: BackendBrief | null;
  selected_idea: BackendIdeaCandidate | null;
  latest_idea_set: BackendIdeaSet | null;
  active_script_version: BackendScript | null;
  active_scene_plan: BackendScenePlan | null;
  recent_jobs: Array<{ status: string }>;
};

type BackendExecutionPolicyRoute = {
  mode: "hosted" | "byo" | "local";
  provider_key: string;
  credential_id: string | null;
};

type BackendExecutionPolicy = {
  text: BackendExecutionPolicyRoute;
  moderation: BackendExecutionPolicyRoute;
  image: BackendExecutionPolicyRoute;
  video: BackendExecutionPolicyRoute;
  speech: BackendExecutionPolicyRoute;
};

type BackendQuickStartJob = {
  id: string;
  job_kind: string;
  status: "queued" | "running" | "completed" | "failed";
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

type BackendQuickStartStep = {
  step_kind: string;
  step_index: number;
  status: "queued" | "running" | "completed" | "failed";
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
};

type BackendQuickStartCreateResponse = {
  project: BackendProjectResponse;
  job: BackendQuickStartJob;
  redirect_path: string;
};

type BackendQuickStartStatusResponse = {
  project: BackendProjectResponse;
  job: BackendQuickStartJob;
  steps: BackendQuickStartStep[];
  current_step: string | null;
  completed_steps: string[];
  redirect_path: string;
  recovery_path: string;
};

const sceneGradients = [
  "linear-gradient(135deg, #0f172a 0%, #1d4ed8 50%, #38bdf8 100%)",
  "linear-gradient(135deg, #1f2937 0%, #0f766e 45%, #67e8f9 100%)",
  "linear-gradient(135deg, #3f3f46 0%, #7c3aed 40%, #f59e0b 100%)",
  "linear-gradient(135deg, #111827 0%, #9333ea 45%, #fb7185 100%)",
];

function avatarInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function titleize(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function configValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function providerFamilyFromKey(providerKey: string): ProviderKey["provider"] {
  if (providerKey.includes("eleven")) return "elevenlabs";
  if (providerKey.includes("stability")) return "stability";
  if (providerKey.includes("runway") || providerKey.includes("veo") || providerKey.includes("kling")) {
    return "runway";
  }
  return "openai";
}

function timeAgo(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  const diffMs = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(diffMs)) {
    return "Unknown";
  }
  const diffMinutes = Math.max(0, Math.round(diffMs / 60000));
  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes}m`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d`;
}

function mapExecutionRoute(
  modality: ProviderModality,
  route: BackendExecutionPolicyRoute,
): ProviderExecutionRoute {
  return {
    mode: route.mode,
    providerKey: route.provider_key,
    providerLabel: providerLabelFromKey(route.provider_key),
    credentialId: route.credential_id,
    generationType: generationTypeFromModality(modality),
  };
}

function mapExecutionPolicy(policy: BackendExecutionPolicy): WorkspaceExecutionPolicy {
  return {
    text: mapExecutionRoute("text", policy.text),
    moderation: mapExecutionRoute("moderation", policy.moderation),
    image: mapExecutionRoute("image", policy.image),
    video: mapExecutionRoute("video", policy.video),
    speech: mapExecutionRoute("speech", policy.speech),
  };
}

function mapProviderCredential(
  credential: BackendProviderCredential,
  policy: WorkspaceExecutionPolicy | null,
): ProviderCredentialRecord {
  const modality = credential.modality as ProviderModality;
  const route = policy?.[modality] ?? null;
  const option = getProviderCatalogOption(credential.provider_key);

  return {
    id: credential.id,
    name: credential.name,
    modality,
    generationType: generationTypeFromModality(modality),
    providerKey: credential.provider_key,
    providerLabel: option?.providerLabel ?? providerLabelFromKey(credential.provider_key),
    supportsActivation: option?.supportsActivation ?? false,
    endpoint: configValue(credential.public_config.endpoint),
    apiVersion: configValue(credential.public_config.api_version),
    deployment: configValue(credential.public_config.deployment),
    modelName:
      configValue(credential.public_config.model_name) || configValue(credential.public_config.model),
    voice: configValue(credential.public_config.voice),
    secretConfigured: credential.secret_configured,
    isActive: route?.credentialId === credential.id,
    activeMode: route?.credentialId === credential.id ? route.mode : null,
    createdAt: credential.created_at,
    updatedAt: credential.updated_at,
    lastUsedAt: credential.last_used_at,
    revokedAt: credential.revoked_at,
    validationStatus: credential.validation_status ?? "not_validated",
    lastValidatedAt: credential.last_validated_at,
    validationError: credential.last_validation_error,
  };
}

function mapBrandKit(brandKit: BackendBrandKit): BrandKit {
  return {
    id: brandKit.id,
    version: brandKit.version,
    name: brandKit.name,
    brandNorthStar:
      configValue(brandKit.brand_rules.north_star) ||
      configValue(brandKit.brand_rules.brand_north_star) ||
      brandKit.description,
    primaryPalette: configValue(brandKit.brand_rules.primary_palette),
    fontFamily: configValue(brandKit.brand_rules.font_family),
  };
}

function mapComment(comment: BackendComment): Comment {
  return {
    id: comment.id,
    targetId: comment.target_id,
    authorName: comment.author_name ?? "Workspace user",
    text: comment.body,
    timestamp: comment.created_at,
    resolved: comment.resolved_at !== null,
  };
}

function buildProviderCredentialPayload(input: ProviderCredentialInput): {
  name: string;
  modality: ProviderModality;
  provider_key: string;
  public_config: Record<string, string>;
  secret_config?: { api_key: string };
} {
  const apiVersion =
    input.apiVersion?.trim() ||
    (input.providerKey === "azure_openai_image" ? "2024-02-01" : "");
  const publicConfig = {
    ...(input.endpoint?.trim() ? { endpoint: input.endpoint.trim() } : {}),
    ...(apiVersion ? { api_version: apiVersion } : {}),
    ...(input.deployment?.trim() ? { deployment: input.deployment.trim() } : {}),
    ...(input.modelName?.trim() ? { model_name: input.modelName.trim() } : {}),
    ...(input.voice?.trim() ? { voice: input.voice.trim() } : {}),
  };

  return {
    name: input.name.trim(),
    modality: input.modality,
    provider_key: input.providerKey,
    public_config: publicConfig,
    ...(input.apiKey?.trim() ? { secret_config: { api_key: input.apiKey.trim() } } : {}),
  };
}

function workflowStatus(value: string | null | undefined): ProjectSummary["renderStatus"] {
  switch ((value ?? "").toLowerCase()) {
    case "completed":
    case "approved":
      return "completed";
    case "running":
      return "running";
    case "queued":
      return "queued";
    case "failed":
      return "failed";
    case "blocked":
      return "blocked";
    case "review":
      return "review";
    default:
      return "draft";
  }
}

function stageFromProject(project: BackendProject): ProjectSummary["stage"] {
  const candidate = project.stage as ProjectSummary["stage"];
  return ["brief", "ideas", "script", "scenes", "frames", "renders", "exports"].includes(candidate)
    ? candidate
    : "brief";
}

function mapUser(session: BackendSession): UserProfile {
  return {
    id: session.user.id,
    name: session.user.full_name,
    email: session.user.email,
    role: session.active_role === "admin" || session.user.is_admin ? "Admin" : titleize(session.active_role),
    avatarInitials: avatarInitials(session.user.full_name),
  };
}

function mapAuthSession(session: BackendSession): AuthSession {
  return {
    user: mapUser(session),
    workspaceId: session.active_workspace_id,
  };
}

function mapBrief(brief: BackendBrief): BriefData {
  return {
    objective: brief.objective,
    hook: brief.hook,
    targetAudience: brief.target_audience,
    callToAction: brief.call_to_action,
    brandNorthStar: brief.brand_north_star,
    guardrails: brief.guardrails,
    mustInclude: brief.must_include,
    approvalSteps: brief.approval_steps,
  };
}

function emptyBrief(): BriefData {
  return {
    objective: "",
    hook: "",
    targetAudience: "",
    callToAction: "",
    brandNorthStar: "",
    guardrails: [],
    mustInclude: [],
    approvalSteps: [],
  };
}

function mapIdeaCandidate(candidate: BackendIdeaCandidate): IdeaCandidate {
  return {
    id: candidate.id,
    title: candidate.title,
    hook: candidate.hook,
    angle: candidate.summary,
    tags: candidate.tags,
    viralScore: Math.max(70, 98 - candidate.order_index * 4),
  };
}

function mapScriptLine(line: BackendScript["lines"][number]): ScriptLine {
  return {
    id: line.id,
    sceneId: line.scene_id,
    beat: line.beat,
    narration: line.narration,
    caption: line.caption,
    durationSec: line.duration_sec,
    status: workflowStatus(line.status),
    visualDirection: line.visual_direction,
    voicePacing: line.voice_pacing,
  };
}

function mapScript(script: BackendScript): ScriptData {
  const lines = script.lines.map(mapScriptLine);
  return {
    id: script.id,
    versionLabel: `v${script.version_number}`,
    approvalState: script.approval_state,
    lastEdited: script.created_at,
    totalWords: script.total_words,
    readingTimeLabel: script.reading_time_label,
    fullText: lines.map((line) => line.narration).join(" "),
    lines,
  };
}

function placeholderScript(projectId: string): ScriptData {
  return {
    id: `queued-${projectId}`,
    versionLabel: "Queued",
    approvalState: "queued",
    lastEdited: new Date().toISOString(),
    totalWords: 0,
    readingTimeLabel: "Pending",
    fullText: "",
    lines: [],
  };
}

function mapScene(segment: BackendSceneSegment, index: number): ScenePlan {
  const warning = segment.validation_warnings[0]?.message ?? null;
  const estimatedWordCount = Math.max(
    1,
    Math.round(segment.narration_text.split(/\s+/).filter(Boolean).length),
  );
  return {
    id: segment.id,
    index: segment.scene_index,
    title: segment.title || `Scene ${segment.scene_index}`,
    beat: segment.beat || segment.narration_text,
    shotType: segment.shot_type || "Storyboard shot",
    motion: segment.motion || "Static",
    prompt: segment.visual_prompt,
    startImagePrompt: segment.start_image_prompt,
    endImagePrompt: segment.end_image_prompt,
    continuityScore: Math.max(70, 96 - index * 3 - segment.validation_warnings.length * 6),
    durationSec: segment.target_duration_seconds,
    estimatedWordCount,
    durationWarning: warning,
    transitionMode: segment.transition_mode === "crossfade" ? "crossfade" : "hard_cut",
    status: segment.validation_warnings.length > 0 ? "review" : "draft",
    keyframeStatus:
      segment.start_image_prompt || segment.end_image_prompt ? "prompted" : "pending",
    notes:
      segment.notes.length > 0
        ? segment.notes
        : segment.validation_warnings.flatMap((entry) => (entry.message ? [entry.message] : [])),
    promptHistory: segment.visual_prompt ? [segment.visual_prompt] : [],
    palette: titleize(segment.visual_direction || "Studio default"),
    audioCue: segment.caption_text ? "Narration + subtitles" : "Narration only",
    thumbnailLabel: segment.title || `Scene ${segment.scene_index}`,
    gradient: sceneGradients[index % sceneGradients.length],
    subtitleStatus: segment.caption_text ? "ready" : "pending",
    narration: segment.narration_text,
    caption: segment.caption_text,
    visualDirection: segment.visual_direction,
    voicePacing: segment.target_duration_seconds <= 4 ? "fast" : "steady",
    version: 1,
  };
}

function mapScenePlan(projectId: string, plan: BackendScenePlan): ScenePlanSet {
  const scenes = plan.segments.map(mapScene);
  const segments: SceneSegment[] = plan.segments.map((segment) => ({
    id: segment.id,
    index: segment.scene_index,
    narration: segment.narration_text,
    caption: segment.caption_text,
    estimatedDurationSec: segment.target_duration_seconds,
    estimatedWordCount: Math.max(
      1,
      Math.round(segment.narration_text.split(/\s+/).filter(Boolean).length),
    ),
    durationWarning: segment.validation_warnings[0]?.message ?? null,
    sourceLineIds: segment.source_line_ids,
  }));
  return {
    id: plan.id,
    projectId,
    status: scenes.length > 0 ? "completed" : "idle",
    approvalState: plan.approval_state === "approved" ? "approved" : "draft",
    approvedAt: plan.approval_state === "approved" ? plan.updated_at : null,
    scenes,
    segments,
    totalDurationSec: plan.total_estimated_duration_seconds,
    warningsCount:
      plan.validation_warnings.length +
      plan.segments.reduce((count, segment) => count + segment.validation_warnings.length, 0),
    visualPresetId: plan.visual_preset_id,
    voicePresetId: plan.voice_preset_id,
  };
}

function placeholderScenePlan(projectId: string): ScenePlanSet {
  return {
    id: `queued-${projectId}`,
    projectId,
    status: "running",
    approvalState: "draft",
    approvedAt: null,
    scenes: [],
    segments: [],
    totalDurationSec: 0,
    warningsCount: 0,
    visualPresetId: null,
    voicePresetId: null,
  };
}

function mapRenderStep(step: BackendRenderStep): RenderStep {
  const rawStatus = step.status;
  const kind = step.step_kind;
  let nextAction = step.error_message ?? "Monitor";
  if (rawStatus === "failed") {
    nextAction = "Retry step";
  } else if (kind === "frame_pair_generation" && rawStatus === "review") {
    nextAction = "Approve or regenerate start/end frames";
  } else if (kind === "frame_pair_generation" && rawStatus === "approved") {
    nextAction = "Frame pair approved";
  }
  return {
    id: step.id,
    sceneId: step.scene_segment_id ?? step.id,
    name: titleize(kind.replace(/_/g, " ")),
    status: workflowStatus(rawStatus),
    stepKind: kind,
    backendStatus: rawStatus,
    errorCode: step.error_code ?? null,
    errorMessage: step.error_message ?? null,
    durationDeltaSec: 0,
    clipStatus: String(step.output_payload?.status ?? titleize(rawStatus)),
    narrationStatus: kind.includes("audio") ? titleize(rawStatus) : "N/A",
    consistency: step.error_message ? "needs review" : "stable",
    nextAction,
    creditCost: rawStatus === "completed" ? 5 : undefined,
  };
}

function mapRenderEvent(event: BackendRenderEvent): RenderEvent {
  const detail =
    typeof event.payload.message === "string"
      ? event.payload.message
      : titleize(event.event_type);
  return {
    id: `${event.sequence_number}`,
    time: new Date(event.at).toLocaleTimeString(),
    label: titleize(event.event_type),
    detail,
    tone:
      event.event_type.includes("failed")
        ? "error"
        : event.event_type.includes("completed")
          ? "success"
          : "primary",
  };
}

function renderChecks(render: BackendRender): RenderCheck[] {
  return [
    {
      id: `${render.id}-pipeline`,
      label: "Pipeline health",
      status:
        render.status === "failed"
          ? "fail"
          : render.status === "completed"
            ? "pass"
            : "warning",
      detail:
        render.status === "completed"
          ? "Render pipeline completed successfully."
          : render.status === "failed"
            ? "The render pipeline encountered a failure."
            : "The render is still moving through the pipeline.",
    },
    {
      id: `${render.id}-exports`,
      label: "Export readiness",
      status: render.exports.length > 0 ? "pass" : "warning",
      detail:
        render.exports.length > 0
          ? "At least one export artifact is available."
          : "Waiting for export artifacts.",
    },
  ];
}

function renderProgress(render: BackendRender): number {
  if (render.status === "completed") return 100;
  if (render.steps.length === 0) return render.status === "queued" ? 5 : 10;
  const completed = render.steps.filter((step) => step.status === "completed").length;
  return Math.max(5, Math.round((completed / render.steps.length) * 100));
}

function mapRender(render: BackendRender, events: BackendRenderEvent[] = []): RenderJob {
  const assets = render.assets ?? [];
  return {
    id: render.id,
    label: `Render ${new Date(render.created_at).toLocaleString()}`,
    status: workflowStatus(render.status),
    progress: renderProgress(render),
    createdAt: render.created_at,
    updatedAt: render.updated_at,
    durationSec: (render.exports[0]?.duration_ms ?? 0) / 1000,
    scenePlanId: render.scene_plan_id ?? null,
    errorCode: render.error_code ?? null,
    errorMessage: render.error_message ?? null,
    exportUrl: render.exports[0]?.download_url ?? null,
    frameAssets: assets.map((a) => ({
      id: a.id,
      sceneSegmentId: a.scene_segment_id,
      assetRole: a.asset_role,
      downloadUrl: a.download_url,
    })),
    transitionMode:
      render.payload.transition_mode === "crossfade" ? "crossfade" : "hard_cut",
    voicePreset: render.voice_preset_id ?? "Workspace default",
    consistencyPackSnapshotId: render.consistency_pack_id ?? "pending",
    sseState: render.status === "running" ? "streaming" : render.status,
    nextAction:
      render.status === "failed"
        ? "Review the failed step."
        : render.status === "completed"
          ? "Review exports."
          : "Wait for pipeline completion.",
    musicTrack: String(
      (render.payload.audio_mix_profile as Record<string, unknown> | undefined)?.music_track_name ??
        "Auto soundtrack",
    ),
    allowExportWithoutMusic: render.allow_export_without_music,
    checks: renderChecks(render),
    steps: render.steps.map(mapRenderStep),
    events: events.map(mapRenderEvent),
    metrics: {
      lufsTarget: String(
        (render.payload.audio_mix_profile as Record<string, unknown> | undefined)?.lufs_target ??
          "-14 LUFS",
      ),
      truePeak: String(
        (render.payload.audio_mix_profile as Record<string, unknown> | undefined)?.true_peak_limit ??
          "-1 dBTP",
      ),
      musicDucking: String(
        (render.payload.audio_mix_profile as Record<string, unknown> | undefined)?.music_ducking ??
          "Auto",
      ),
      subtitleState: String(
        (render.payload.subtitle_style_profile as Record<string, unknown> | undefined)?.enabled ??
          "auto",
      ),
    },
  };
}

function mapExport(exportItem: BackendExport): ExportArtifact {
  return {
    id: exportItem.id,
    name: exportItem.file_name,
    status:
      exportItem.status === "completed" || exportItem.availability_status === "available"
        ? "ready"
        : "processing",
    format: exportItem.format.toUpperCase(),
    destination: exportItem.download_url ?? exportItem.object_name,
    durationSec: (exportItem.duration_ms ?? 0) / 1000,
    sizeMb: 0,
    integratedLufs: Number((exportItem.audio_mix_profile.integrated_lufs as number | undefined) ?? -14),
    truePeak: Number((exportItem.audio_mix_profile.true_peak as number | undefined) ?? -1),
    subtitles: Boolean(exportItem.subtitle_style_profile.enabled ?? true),
    musicBed: Boolean((exportItem.audio_mix_profile.music_enabled as boolean | undefined) ?? true),
    createdAt: exportItem.created_at,
    gradient: sceneGradients[0],
    ratio: "9:16",
  };
}

function mapProjectSummary(detail: BackendProjectDetail): ProjectSummary {
  const sceneCount =
    detail.active_scene_plan?.scene_count ?? detail.active_script_version?.lines.length ?? 0;
  const durationSec =
    detail.active_scene_plan?.total_estimated_duration_seconds ??
    detail.active_script_version?.estimated_duration_seconds ??
    detail.project.duration_target_sec;
  return {
    id: detail.project.id,
    title: detail.project.title,
    client: detail.project.client ?? "Untitled client",
    stage: stageFromProject(detail.project),
    renderStatus: workflowStatus(detail.recent_jobs[0]?.status ?? detail.project.stage),
    updatedAt: detail.project.updated_at,
    aspectRatio: detail.project.aspect_ratio,
    sceneCount,
    durationSec,
    tags: detail.selected_idea?.tags ?? [],
    hook: detail.active_brief?.hook ?? detail.selected_idea?.hook ?? "No hook yet.",
    palette: detail.active_scene_plan?.segments[0]?.visual_direction
      ? titleize(detail.active_scene_plan.segments[0].visual_direction)
      : "Studio default",
    voicePreset: detail.active_script_version ? "Project script voice" : "Workspace default",
    objective: detail.active_brief?.objective ?? "No objective yet.",
    nextMilestone: detail.active_scene_plan
      ? detail.active_scene_plan.approval_state === "approved"
        ? "Start or monitor render generation."
        : "Approve the scene plan."
      : detail.active_script_version
        ? detail.active_script_version.approval_state === "approved"
          ? "Generate a scene plan."
          : "Approve the active script."
        : detail.selected_idea
          ? "Generate a script draft."
          : detail.active_brief
            ? "Generate and select an idea."
            : "Complete the project brief.",
    selectedIdeaId: detail.project.selected_idea_id,
  };
}

function mapQuickCreateJob(job: BackendQuickStartJob): QuickCreateJobSummary {
  return {
    id: job.id,
    jobKind: job.job_kind,
    status: job.status,
    errorCode: job.error_code,
    errorMessage: job.error_message,
    createdAt: job.created_at,
    updatedAt: job.updated_at,
    completedAt: job.completed_at,
  };
}

function mapQuickCreateStep(step: BackendQuickStartStep): QuickCreateStepStatus {
  return {
    stepKind: step.step_kind,
    stepIndex: step.step_index,
    status: step.status,
    errorCode: step.error_code,
    errorMessage: step.error_message,
    startedAt: step.started_at,
    completedAt: step.completed_at,
  };
}

function mapQuickCreateStatus(response: BackendQuickStartStatusResponse): QuickCreateStatus {
  const steps = response.steps.map(mapQuickCreateStep);
  const job = mapQuickCreateJob(response.job);
  return {
    projectId: response.project.id,
    projectTitle: response.project.title,
    projectStage: stageFromProject({
      id: response.project.id,
      title: response.project.title,
      client: response.project.client,
      aspect_ratio: response.project.aspect_ratio,
      duration_target_sec: response.project.duration_target_sec,
      stage: response.project.stage,
      selected_idea_id: response.project.selected_idea_id,
      updated_at: response.project.updated_at,
    }),
    job,
    steps,
    currentStep: response.current_step,
    completedSteps: response.completed_steps,
    redirectPath: response.redirect_path,
    recoveryPath: response.recovery_path,
    isActive: job.status === "queued" || job.status === "running",
    isCompleted: job.status === "completed",
    hasFailed: job.status === "failed",
  };
}

function mapAlerts(notifications: BackendNotification[]): AlertItem[] {
  return notifications.slice(0, 6).map((notification) => ({
    id: notification.id,
    label: notification.title,
    detail: notification.body,
    tone: notification.read_at ? "neutral" : "primary",
  }));
}

function mapWorkspaceSummaries(
  session: BackendSession,
  usage: BackendUsageSummary | null,
  notifications: BackendNotification[],
  projects: ProjectSummary[],
): WorkspaceSummary[] {
  return session.workspaces.map((workspace) => {
    const isActive = workspace.workspace_id === session.active_workspace_id;
    return {
      id: workspace.workspace_id,
      name: workspace.workspace_name,
      plan: workspace.plan_name,
      seats: 1,
      creditsRemaining: isActive && usage ? usage.credits_remaining : 0,
      creditsTotal: isActive && usage ? usage.credits_total : 0,
      monthlyBudget: isActive && usage ? usage.monthly_budget_cents / 100 : 0,
      queueCount: isActive
        ? projects.filter((project) => ["queued", "running"].includes(project.renderStatus)).length
        : 0,
      notifications: isActive ? notifications.filter((notification) => !notification.read_at).length : 0,
    };
  });
}

function idempotencyHeaders(): Record<string, string> {
  return { "Idempotency-Key": crypto.randomUUID() };
}

async function getProjectDetail(projectId: string): Promise<BackendProjectDetail> {
  return api.get<BackendProjectDetail>(`/projects/${projectId}`);
}

async function getLatestIdeas(projectId: string): Promise<BackendIdeaSet | null> {
  const ideaSets = await api.get<BackendIdeaSet[]>(`/projects/${projectId}/ideas`);
  return ideaSets[0] ?? null;
}

async function getLatestScript(projectId: string): Promise<BackendScript | null> {
  const scripts = await api.get<BackendScript[]>(`/projects/${projectId}/scripts`);
  return scripts[0] ?? null;
}

async function getLatestScenePlan(projectId: string): Promise<BackendScenePlan | null> {
  const plans = await api.get<BackendScenePlan[]>(`/projects/${projectId}/scene-plans`);
  return plans[0] ?? null;
}

async function getProjectSummaries(): Promise<ProjectSummary[]> {
  const projects = await api.get<BackendProject[]>("/projects");
  const details = await Promise.all(projects.map((project) => getProjectDetail(project.id)));
  return details.map(mapProjectSummary);
}

export async function liveLogin(credentials: LoginCredentials): Promise<AuthSession> {
  const session = await api.post<BackendSession>("/auth/login", credentials);
  return mapAuthSession(session);
}

export async function liveLogout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function liveGetSession(): Promise<AuthSession | null> {
  try {
    const session = await api.get<BackendSession>("/auth/session");
    return mapAuthSession(session);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export async function liveSelectWorkspace(workspaceId: string): Promise<AuthSession> {
  const session = await api.post<BackendSession>("/auth/workspace/select", {
    workspace_id: workspaceId,
  });
  return mapAuthSession(session);
}

export async function liveGetShellData(): Promise<ShellData> {
  const [session, projects, notifications, usage] = await Promise.all([
    api.get<BackendSession>("/auth/session"),
    getProjectSummaries(),
    api.get<BackendNotification[]>("/notifications").catch(() => []),
    api.get<BackendUsageSummary>("/usage").catch(() => null),
  ]);
  return {
    user: mapUser(session),
    workspaces: mapWorkspaceSummaries(session, usage, notifications, projects),
    projects,
    alerts: mapAlerts(notifications),
  };
}

export async function liveGetDashboardData(): Promise<DashboardData> {
  const [shellData, usage] = await Promise.all([
    liveGetShellData(),
    api.get<BackendUsageSummary>("/usage").catch(() => null),
  ]);
  const focusProject = shellData.projects[0];
  const renders = focusProject ? await liveGetRenders(focusProject.id).catch(() => []) : [];
  return {
    focusProject,
    metrics: [
      {
        label: "Credits Remaining",
        value: String(usage?.credits_remaining ?? 0),
        detail: usage ? `${usage.month_credits_used} credits used this cycle` : "Usage unavailable",
        tone: "primary",
      },
      {
        label: "Monthly Spend",
        value: `$${((usage?.month_provider_cost_cents ?? 0) / 100).toFixed(2)}`,
        detail: "Provider-side usage for the current billing period",
        tone: "neutral",
      },
      {
        label: "Exports",
        value: String(usage?.month_export_count ?? 0),
        detail: "Successful exports this cycle",
        tone: "success",
      },
    ],
    notifications: shellData.alerts,
    queueOverview: [
      {
        label: "Queued Projects",
        value: String(shellData.projects.filter((project) => project.renderStatus === "queued").length),
        detail: "Projects waiting on generation or render execution",
        tone: "warning",
      },
      {
        label: "Running Jobs",
        value: String(shellData.projects.filter((project) => project.renderStatus === "running").length),
        detail: "Projects with active background execution",
        tone: "primary",
      },
    ],
    compositionRules: renders[0]?.checks ?? [],
    recentProjects: shellData.projects.slice(0, 5),
  };
}

export async function liveGetProjects(): Promise<ProjectSummary[]> {
  return getProjectSummaries();
}

export async function liveGetProject(projectId: string): Promise<ProjectSummary> {
  return mapProjectSummary(await getProjectDetail(projectId));
}

export async function liveCreateProject(payload: CreateProjectPayload): Promise<ProjectSummary> {
  const project = await api.post<BackendProject>("/projects", {
    title: payload.title,
    client: payload.client,
  });
  return liveGetProject(project.id);
}

export async function liveQuickCreateProject(
  payload: QuickCreateProjectPayload,
): Promise<QuickCreateProjectResponse> {
  const created = await api.post<BackendQuickStartCreateResponse>(
    "/projects:quick-start",
    {
      idea_prompt: payload.ideaPrompt,
      starter_mode: payload.starterMode,
      ...(payload.templateId ? { template_id: payload.templateId } : {}),
    },
    idempotencyHeaders(),
  );
  return {
    projectId: created.project.id,
    projectTitle: created.project.title,
    redirectPath: created.redirect_path,
    job: mapQuickCreateJob(created.job),
  };
}

export async function liveGetQuickCreateStatus(projectId: string): Promise<QuickCreateStatus> {
  const status = await api.get<BackendQuickStartStatusResponse>(
    `/projects/${projectId}/quick-start-status`,
  );
  return mapQuickCreateStatus(status);
}

export async function liveGetProjectBundle(projectId: string): Promise<ProjectBundle> {
  const [detail, script, scenePlan, renderJobs, exportsData] = await Promise.all([
    getProjectDetail(projectId),
    liveGetScript(projectId).catch(() => null),
    liveGetScenePlan(projectId).catch(() => null),
    liveGetRenders(projectId).catch(() => []),
    liveGetExports(projectId).catch(() => []),
  ]);
  return {
    project: mapProjectSummary(detail),
    brief: detail.active_brief ? mapBrief(detail.active_brief) : emptyBrief(),
    script: script ?? placeholderScript(projectId),
    scenes: scenePlan?.scenes ?? [],
    renderJobs,
    exports: exportsData,
  };
}

export async function liveGetBrief(projectId: string): Promise<BriefData> {
  const detail = await getProjectDetail(projectId);
  return detail.active_brief ? mapBrief(detail.active_brief) : emptyBrief();
}

export async function liveUpdateBrief(projectId: string, data: Partial<BriefData>): Promise<BriefData> {
  const current = await liveGetBrief(projectId);
  const saved = await api.patch<BackendBrief>(`/projects/${projectId}/brief`, {
    objective: data.objective ?? current.objective,
    hook: data.hook ?? current.hook,
    target_audience: data.targetAudience ?? current.targetAudience,
    call_to_action: data.callToAction ?? current.callToAction,
    brand_north_star: data.brandNorthStar ?? current.brandNorthStar,
    guardrails: current.guardrails,
    must_include: current.mustInclude,
    approval_steps: current.approvalSteps,
  });
  return mapBrief(saved);
}

export async function liveGetIdeas(projectId: string): Promise<IdeaSet | null> {
  const ideaSet = await getLatestIdeas(projectId);
  return ideaSet
    ? {
        id: ideaSet.id,
        projectId: ideaSet.project_id,
        status: ideaSet.candidates.length > 0 ? "completed" : "queued",
        ideas: ideaSet.candidates.map(mapIdeaCandidate),
        generatedAt: ideaSet.created_at,
      }
    : null;
}

export async function liveGenerateIdeas(projectId: string): Promise<IdeaSet> {
  await api.post(`/projects/${projectId}/ideas:generate`, undefined, idempotencyHeaders());
  return {
    id: `queued-${projectId}`,
    projectId,
    status: "running",
    ideas: [],
    generatedAt: null,
  };
}

export async function liveSelectIdea(projectId: string, ideaId: string): Promise<ProjectSummary> {
  await api.post(`/projects/${projectId}/ideas/${ideaId}:select`);
  return liveGetProject(projectId);
}

export async function liveGetScript(projectId: string): Promise<ScriptData | null> {
  const script = await getLatestScript(projectId);
  return script ? mapScript(script) : null;
}

export async function liveGenerateScript(projectId: string): Promise<ScriptData> {
  await api.post(`/projects/${projectId}/scripts:generate`, undefined, idempotencyHeaders());
  return placeholderScript(projectId);
}

export async function liveUpdateScript(projectId: string, updates: Partial<ScriptData>): Promise<ScriptData> {
  const current = await getLatestScript(projectId);
  if (!current) {
    throw new Error("No script version exists for this project yet.");
  }
  const currentLines = current.lines.map(mapScriptLine);
  const saved = await api.patch<BackendScript>(
    `/projects/${projectId}/scripts/${current.id}`,
    {
      version: current.version,
      approval_state: updates.approvalState ?? current.approval_state,
      lines: (updates.lines ?? currentLines).map((line) => ({
        id: line.id,
        scene_id: line.sceneId,
        beat: line.beat,
        narration: line.narration,
        caption: line.caption,
        duration_sec: line.durationSec,
        status: line.status,
        visual_direction: line.visualDirection,
        voice_pacing: line.voicePacing,
      })),
      metadata: {},
    },
  );
  return mapScript(saved);
}

export async function liveApproveScript(projectId: string): Promise<ScriptData> {
  const current = await getLatestScript(projectId);
  if (!current) {
    throw new Error("No script version exists for this project yet.");
  }
  const approved = await api.post<BackendScript>(`/projects/${projectId}/scripts/${current.id}:approve`);
  return mapScript(approved);
}

export async function liveGetScenePlan(projectId: string): Promise<ScenePlanSet | null> {
  const plan = await getLatestScenePlan(projectId);
  return plan ? mapScenePlan(projectId, plan) : null;
}

export async function liveGenerateScenePlan(projectId: string): Promise<ScenePlanSet> {
  await api.post(`/projects/${projectId}/scene-plan:generate`, undefined, idempotencyHeaders());
  return placeholderScenePlan(projectId);
}

export async function liveGeneratePromptPairs(projectId: string, sceneId: string): Promise<ScenePlan> {
  const currentPlan = await getLatestScenePlan(projectId);
  if (!currentPlan) {
    throw new Error("No scene plan exists for this project yet.");
  }
  await api.post(
    `/projects/${projectId}/scene-plans/${currentPlan.id}:generate-prompt-pairs`,
    undefined,
    idempotencyHeaders(),
  );
  const scene = mapScenePlan(projectId, currentPlan).scenes.find((entry) => entry.id === sceneId);
  if (!scene) {
    throw new Error("Scene not found.");
  }
  return scene;
}

export async function liveUpdateScene(
  projectId: string,
  sceneId: string,
  updates: Partial<ScenePlan>,
): Promise<ScenePlan> {
  const currentPlan = await getLatestScenePlan(projectId);
  if (!currentPlan) {
    throw new Error("No scene plan exists for this project yet.");
  }
  const saved = await api.patch<BackendScenePlan>(`/projects/${projectId}/scene-plans/${currentPlan.id}`, {
    version: currentPlan.version,
    visual_preset_id: currentPlan.visual_preset_id,
    voice_preset_id: currentPlan.voice_preset_id,
    segments: currentPlan.segments.map((segment) => {
      const currentScene = mapScene(segment, segment.scene_index - 1);
      const merged = segment.id === sceneId ? { ...currentScene, ...updates } : currentScene;
      return {
        scene_index: merged.index,
        source_line_ids: segment.source_line_ids,
        title: merged.title,
        beat: merged.beat,
        narration_text: merged.narration,
        caption_text: merged.caption,
        visual_direction: merged.visualDirection,
        shot_type: merged.shotType,
        motion: merged.motion,
        target_duration_seconds: Math.max(1, Math.round(merged.durationSec)),
        estimated_voice_duration_seconds: Math.max(1, Math.round(merged.durationSec)),
        visual_prompt: merged.prompt,
        start_image_prompt: merged.startImagePrompt,
        end_image_prompt: merged.endImagePrompt,
        transition_mode: merged.transitionMode,
        notes: merged.notes,
      };
    }),
  });
  const scene = mapScenePlan(projectId, saved).scenes.find((entry) => entry.id === sceneId);
  if (!scene) {
    throw new Error("Scene not found.");
  }
  return scene;
}

export async function liveApproveScenePlan(projectId: string): Promise<ScenePlanSet> {
  const currentPlan = await getLatestScenePlan(projectId);
  if (!currentPlan) {
    throw new Error("No scene plan exists for this project yet.");
  }
  const approved = await api.post<BackendScenePlan>(
    `/projects/${projectId}/scene-plans/${currentPlan.id}:approve`,
  );
  return mapScenePlan(projectId, approved);
}

export async function liveGetVisualPresets(): Promise<VisualPreset[]> {
  const presets = await api.get<BackendVisualPreset[]>("/presets/visual");
  return presets.map((preset) => ({
    id: preset.id,
    name: preset.name,
    description: preset.description,
    category: "visual",
    style: preset.style_descriptor || "Custom",
    palette: preset.color_palette || "Studio palette",
    lighting: preset.camera_defaults || "Default lighting",
  }));
}

export async function liveGetVoicePresets(): Promise<VoicePreset[]> {
  const presets = await api.get<BackendVoicePreset[]>("/presets/voice");
  return presets.map((preset) => ({
    id: preset.id,
    name: preset.name,
    description: preset.description,
    tone: preset.tone_descriptor || "Balanced",
    pacing: preset.provider_voice || "Default voice",
    accent: preset.language_code,
  }));
}

export async function liveCreateVisualPreset(preset: Omit<VisualPreset, "id">): Promise<VisualPreset> {
  const created = await api.post<BackendVisualPreset>("/presets/visual", {
    name: preset.name,
    description: preset.description,
    prompt_prefix: "",
    style_descriptor: preset.style,
    negative_prompt: "",
    camera_defaults: preset.lighting,
    color_palette: preset.palette,
    reference_notes: preset.category,
  });
  return {
    id: created.id,
    name: created.name,
    description: created.description,
    category: "visual",
    style: created.style_descriptor || "Custom",
    palette: created.color_palette || "Studio palette",
    lighting: created.camera_defaults || "Default lighting",
  };
}

export async function liveCreateVoicePreset(preset: Omit<VoicePreset, "id">): Promise<VoicePreset> {
  const created = await api.post<BackendVoicePreset>("/presets/voice", {
    name: preset.name,
    description: preset.description,
    provider_voice: preset.pacing,
    tone_descriptor: preset.tone,
    language_code: preset.accent,
    pace_multiplier: 1,
  });
  return {
    id: created.id,
    name: created.name,
    description: created.description,
    tone: created.tone_descriptor || "Balanced",
    pacing: created.provider_voice || "Default voice",
    accent: created.language_code,
  };
}

export async function liveSetScenePlanPreset(
  projectId: string,
  type: "visual" | "voice",
  presetId: string,
): Promise<ScenePlanSet> {
  const currentPlan = await getLatestScenePlan(projectId);
  if (!currentPlan) {
    throw new Error("No scene plan exists for this project yet.");
  }
  const saved = await api.patch<BackendScenePlan>(`/projects/${projectId}/scene-plans/${currentPlan.id}`, {
    version: currentPlan.version,
    visual_preset_id: type === "visual" ? presetId : currentPlan.visual_preset_id,
    voice_preset_id: type === "voice" ? presetId : currentPlan.voice_preset_id,
    segments: currentPlan.segments.map((segment) => ({
      scene_index: segment.scene_index,
      source_line_ids: segment.source_line_ids,
      title: segment.title,
      beat: segment.beat,
      narration_text: segment.narration_text,
      caption_text: segment.caption_text,
      visual_direction: segment.visual_direction,
      shot_type: segment.shot_type,
      motion: segment.motion,
      target_duration_seconds: segment.target_duration_seconds,
      estimated_voice_duration_seconds: segment.estimated_voice_duration_seconds,
      visual_prompt: segment.visual_prompt,
      start_image_prompt: segment.start_image_prompt,
      end_image_prompt: segment.end_image_prompt,
      transition_mode: segment.transition_mode,
      notes: segment.notes,
    })),
  });
  return mapScenePlan(projectId, saved);
}

export async function liveGetRenders(projectId: string): Promise<RenderJob[]> {
  const renders = await api.get<BackendRender[]>(`/projects/${projectId}/renders`);
  return Promise.all(
    renders.map(async (render) => {
      const events = await api.get<BackendRenderEvent[]>(`/renders/${render.id}/events`).catch(() => []);
      return mapRender(render, events);
    }),
  );
}

export async function liveStartRender(
  projectId: string,
  settings?: { subtitleStyle: string; musicDucking: string; musicTrack: string; animationEffect: string },
): Promise<RenderJob> {
  await api.post(
    `/projects/${projectId}/renders`,
    {
      allow_export_without_music: true,
      render_mode: "slide",
      animation_profile: { effect: settings?.animationEffect ?? "ken_burns" },
      subtitle_style_profile: { style: settings?.subtitleStyle ?? "default" },
      audio_mix_profile: {
        music_ducking: settings?.musicDucking ?? "auto",
        music_track_name: settings?.musicTrack ?? "auto",
      },
    },
    idempotencyHeaders(),
  );
  return {
    id: `queued-${projectId}`,
    label: "Queued render",
    status: "queued",
    progress: 5,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    durationSec: 0,
    transitionMode: "hard_cut",
    voicePreset: "Workspace default",
    consistencyPackSnapshotId: "pending",
    sseState: "queued",
    nextAction: "Waiting for worker pickup.",
    musicTrack: settings?.musicTrack ?? "Auto soundtrack",
    allowExportWithoutMusic: true,
    exportUrl: null,
    checks: [],
    steps: [],
    events: [],
    metrics: {
      lufsTarget: "-14 LUFS",
      truePeak: "-1 dBTP",
      musicDucking: settings?.musicDucking ?? "auto",
      subtitleState: settings?.subtitleStyle ?? "default",
    },
  };
}

export async function liveCancelRender(projectId: string): Promise<void> {
  const renders = await liveGetRenders(projectId);
  const activeRender = renders.find((render) => !["completed", "failed"].includes(render.status));
  if (activeRender) {
    await api.post(`/renders/${activeRender.id}:cancel`);
  }
}

export async function liveRetryRenderStep(projectId: string, stepId: string): Promise<RenderJob> {
  const renders = await api.get<BackendRender[]>(`/projects/${projectId}/renders`);
  const owningRender = renders.find((render) => render.steps.some((step) => step.id === stepId));
  if (!owningRender) {
    throw new Error("Render step not found.");
  }
  const retried = await api.post<BackendRender>(`/renders/${owningRender.id}/steps/${stepId}:retry`);
  const events = await api.get<BackendRenderEvent[]>(`/renders/${retried.id}/events`).catch(() => []);
  return mapRender(retried, events);
}

export async function liveApproveFramePair(projectId: string, stepId: string): Promise<RenderJob> {
  const renders = await api.get<BackendRender[]>(`/projects/${projectId}/renders`);
  const owningRender = renders.find((render) => render.steps.some((step) => step.id === stepId));
  if (!owningRender) {
    throw new Error("Render step not found.");
  }
  const updated = await api.post<BackendRender>(
    `/renders/${owningRender.id}/steps/${stepId}:approve-frame-pair`,
  );
  const events = await api.get<BackendRenderEvent[]>(`/renders/${updated.id}/events`).catch(() => []);
  return mapRender(updated, events);
}

export async function liveRegenerateFramePair(projectId: string, stepId: string): Promise<RenderJob> {
  const renders = await api.get<BackendRender[]>(`/projects/${projectId}/renders`);
  const owningRender = renders.find((render) => render.steps.some((step) => step.id === stepId));
  if (!owningRender) {
    throw new Error("Render step not found.");
  }
  const updated = await api.post<BackendRender>(
    `/renders/${owningRender.id}/steps/${stepId}:regenerate-frame-pair`,
  );
  const events = await api.get<BackendRenderEvent[]>(`/renders/${updated.id}/events`).catch(() => []);
  return mapRender(updated, events);
}

export interface NarrationResult {
  assetId: string;
  downloadUrl: string | null;
  durationMs: number;
  voice: string;
}

export async function liveGenerateNarration(
  renderJobId: string,
  sceneSegmentId: string,
  voice?: string,
): Promise<NarrationResult> {
  const raw = await api.post<{
    asset_id: string;
    download_url: string | null;
    duration_ms: number;
    voice: string;
  }>(`/renders/${renderJobId}/scenes/${sceneSegmentId}:generate-narration`, { voice: voice || null });
  return {
    assetId: raw.asset_id,
    downloadUrl: raw.download_url,
    durationMs: raw.duration_ms,
    voice: raw.voice,
  };
}

export async function liveGetExports(projectId: string): Promise<ExportArtifact[]> {
  const exportsData = await api.get<BackendExport[]>(`/projects/${projectId}/exports`);
  return exportsData.map(mapExport);
}

export async function liveGetBillingData(): Promise<BillingData> {
  const [usage, subscription] = await Promise.all([
    api.get<BackendUsageSummary>("/usage"),
    api.get<BackendSubscription>("/billing/subscription").catch(() => null),
  ]);
  return {
    planName: subscription?.plan_name ?? usage.plan_name,
    cycleLabel: subscription?.current_period_end_at
      ? `Renews ${new Date(subscription.current_period_end_at).toLocaleDateString()}`
      : "Current billing cycle",
    creditsRemaining: usage.credits_remaining,
    creditsTotal: usage.credits_total,
    projectedSpend: `$${(usage.month_provider_cost_cents / 100).toFixed(2)}`,
    usageBreakdown: [
      { category: "Provider runs", usage: String(usage.month_provider_run_count), unitCost: "Metered", total: `${usage.month_credits_used} credits` },
      { category: "Exports", usage: String(usage.month_export_count), unitCost: "Included", total: String(usage.month_export_count) },
    ],
    invoices: [],
  };
}

export async function liveGetBilling(): Promise<BillingData> {
  return liveGetBillingData();
}

export async function liveGetPresets(): Promise<PresetCard[]> {
  const [visualPresets, voicePresets] = await Promise.all([
    liveGetVisualPresets(),
    liveGetVoicePresets(),
  ]);
  return [
    ...visualPresets.map((preset) => ({
      id: preset.id,
      name: preset.name,
      category: "visual" as const,
      description: preset.description,
      tags: [preset.style, preset.palette],
      status: "active",
      look: `${preset.style} · ${preset.lighting}`,
    })),
    ...voicePresets.map((preset) => ({
      id: preset.id,
      name: preset.name,
      category: "voice" as const,
      description: preset.description,
      tags: [preset.tone, preset.accent],
      status: "active",
      voice: `${preset.pacing} · ${preset.tone}`,
    })),
  ];
}

export async function liveGetTemplates(): Promise<TemplateCard[]> {
  const templates = await api.get<BackendTemplate[]>("/templates");
  return templates.map((template) => ({
    id: template.id,
    name: template.name,
    description: template.description,
    duration: String(template.latest_version?.snapshot_payload.duration_target_sec ?? "60-90s"),
    scenes: Number(template.latest_version?.snapshot_payload.scene_count ?? 0),
    style: String(template.latest_version?.snapshot_payload.style_descriptor ?? "Reusable production starter"),
  }));
}

export async function liveCloneTemplate(templateId: string): Promise<string> {
  const template = await api.get<BackendTemplate>(`/templates/${templateId}`);
  const created = await api.post<{ project: { id: string } }>(
    `/templates/${templateId}:create-project`,
    {
      title: `Copy of ${template.name}`,
      client: null,
    },
  );
  return created.project.id;
}

export async function liveGetAssets(): Promise<AssetRecord[]> {
  const assets = await api.get<BackendAsset[]>("/assets/library");
  return assets.map((asset) => ({
    id: asset.id,
    type: asset.asset_type === "video" || asset.asset_type === "audio" ? asset.asset_type : "image",
    sourceProjectId: asset.project_id,
    sourceSceneId: asset.scene_segment_id,
    thumbnailUrl: asset.download_url ?? "",
    url: asset.download_url ?? "",
    prompt: String(asset.metadata_payload.prompt ?? asset.library_label ?? asset.file_name),
    tags: [],
    createdAt: asset.created_at,
  }));
}

export async function liveGetBrandKits(): Promise<BrandKit[]> {
  const brandKits = await api.get<BackendBrandKit[]>("/brand-kits");
  return brandKits.map(mapBrandKit);
}

export async function liveSaveBrandKit(kit: BrandKit): Promise<BrandKit> {
  const payload = {
    name: kit.name,
    description: kit.brandNorthStar,
    brand_rules: {
      north_star: kit.brandNorthStar,
      primary_palette: kit.primaryPalette,
      font_family: kit.fontFamily,
    },
  };
  const saved = kit.id
    ? await api.patch<BackendBrandKit>(`/brand-kits/${kit.id}`, {
        version: kit.version,
        ...payload,
      })
    : await api.post<BackendBrandKit>("/brand-kits", payload);
  return mapBrandKit(saved);
}

export async function liveGetComments(
  targetId: string,
  options: { projectId?: string; targetType?: string } = {},
): Promise<Comment[]> {
  const params = new URLSearchParams({
    target_id: targetId,
    target_type: options.targetType ?? "scene_segment",
    ...(options.projectId ? { project_id: options.projectId } : {}),
  });
  const comments = await api.get<BackendComment[]>(`/comments?${params.toString()}`);
  return comments.map(mapComment);
}

export async function liveAddComment(
  targetId: string,
  text: string,
  options: { projectId?: string; targetType?: string } = {},
): Promise<Comment> {
  const created = await api.post<BackendComment>("/comments", {
    project_id: options.projectId,
    target_type: options.targetType ?? "scene_segment",
    target_id: targetId,
    body: text,
    metadata_payload: {},
  });
  return mapComment(created);
}

export async function liveResolveComment(commentId: string): Promise<void> {
  await api.post(`/comments/${commentId}:resolve`, {});
}

export async function liveGetExecutionPolicy(): Promise<WorkspaceExecutionPolicy> {
  const policy = await api.get<BackendExecutionPolicy>("/workspace/execution-policy");
  return mapExecutionPolicy(policy);
}

export async function liveUpdateExecutionPolicyRoute(
  modality: ProviderModality,
  providerKey: string,
  credentialId: string | null,
  mode: "hosted" | "byo" | "local",
): Promise<WorkspaceExecutionPolicy> {
  const updated = await api.put<BackendExecutionPolicy>("/workspace/execution-policy", {
    [modality]: {
      mode,
      provider_key: providerKey,
      credential_id: credentialId,
    },
  });
  return mapExecutionPolicy(updated);
}

export async function liveGetProviderCredentials(): Promise<ProviderCredentialRecord[]> {
  const [credentials, policy] = await Promise.all([
    api.get<BackendProviderCredential[]>("/workspace/provider-credentials"),
    liveGetExecutionPolicy().catch(() => null),
  ]);

  return credentials
    .filter((credential) => !credential.revoked_at)
    .map((credential) => mapProviderCredential(credential, policy));
}

export async function liveCreateProviderCredential(
  input: ProviderCredentialInput,
): Promise<ProviderCredentialRecord> {
  if (!input.apiKey?.trim()) {
    throw new ApiError(400, "provider_secret_required", "An API key is required.");
  }
  const created = await api.post<BackendProviderCredential>(
    "/workspace/provider-credentials",
    buildProviderCredentialPayload(input),
  );
  if (input.setAsActiveRoute) {
    await liveUpdateExecutionPolicyRoute(input.modality, created.provider_key, created.id, "byo");
  }
  const policy = await liveGetExecutionPolicy().catch(() => null);
  return mapProviderCredential(created, policy);
}

export async function liveUpdateProviderCredential(
  credentialId: string,
  input: ProviderCredentialInput,
): Promise<ProviderCredentialRecord> {
  const updated = await api.patch<BackendProviderCredential>(
    `/workspace/provider-credentials/${credentialId}`,
    buildProviderCredentialPayload(input),
  );
  if (input.setAsActiveRoute) {
    await liveUpdateExecutionPolicyRoute(input.modality, updated.provider_key, updated.id, "byo");
  }
  const policy = await liveGetExecutionPolicy().catch(() => null);
  return mapProviderCredential(updated, policy);
}

export async function liveValidateProviderCredential(
  credentialId: string,
): Promise<ProviderCredentialRecord> {
  const validated = await api.post<BackendProviderCredential>(
    `/workspace/provider-credentials/${credentialId}:validate`,
    {},
  );
  const policy = await liveGetExecutionPolicy().catch(() => null);
  return mapProviderCredential(validated, policy);
}

export async function liveDeleteProviderCredential(id: string): Promise<void> {
  await api.post(`/workspace/provider-credentials/${id}:revoke`);
}

export async function liveGetProviderKeys(): Promise<ProviderKey[]> {
  const credentials = await liveGetProviderCredentials();
  return credentials.map((credential) => ({
    id: credential.id,
    provider: providerFamilyFromKey(credential.providerKey),
    keyPrefix: credential.providerKey,
    createdAt: credential.createdAt,
  }));
}

export async function liveAddProviderKey(
  provider: ProviderKey["provider"],
  key: string,
): Promise<ProviderKey> {
  const created = await liveCreateProviderCredential({
    name: `${titleize(provider)} credential`,
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
    provider: providerFamilyFromKey(created.providerKey),
    keyPrefix: created.providerKey,
    createdAt: created.createdAt,
  };
}

export async function liveDeleteProviderKey(id: string): Promise<void> {
  await liveDeleteProviderCredential(id);
}

export async function liveGetLocalWorkers(): Promise<LocalWorker[]> {
  const workers = await api.get<BackendLocalWorker[]>("/workspace/local-workers");
  return workers.map((worker) => ({
    id: worker.id,
    name: worker.name,
    status: worker.status === "online" || worker.status === "busy" ? worker.status : "offline",
    lastHeartbeat: worker.last_heartbeat_at ?? new Date(0).toISOString(),
    capabilities: {
      orderedReferenceImages: worker.supports_ordered_reference_images,
      localTTS: worker.supports_tts,
      videoFrames: worker.supports_first_last_frame_video,
    },
  }));
}

export async function liveGetSettings(): Promise<SettingsSection[]> {
  const [providerCredentials, workers] = await Promise.all([
    liveGetProviderCredentials(),
    liveGetLocalWorkers(),
  ]);
  return [
    {
      title: "Execution Settings",
      description: "Live settings available from workspace APIs.",
      items: [
        { label: "Provider credentials", value: String(providerCredentials.length) },
        { label: "Local workers", value: String(workers.length) },
      ],
    },
  ];
}

export async function liveGetAdminQueue(): Promise<AdminQueueItem[]> {
  const [items, projects] = await Promise.all([
    api.get<BackendAdminModerationItem[]>("/admin/moderation?review_status=pending"),
    api.get<BackendProject[]>("/projects").catch(() => []),
  ]);
  const projectNameById = new Map(projects.map((project) => [project.id, project.title]));
  return items.map((item) => ({
    id: item.id,
    workspace: "Active workspace",
    project: item.project_id ? projectNameById.get(item.project_id) ?? item.project_id : "Workspace scope",
    step: item.blocked_message || titleize(item.target_type),
    status: "blocked",
    retries: 0,
    owner: "Moderation review",
    age: timeAgo(item.created_at),
    provider: item.provider_name || "Policy engine",
  }));
}

export async function liveApproveQueueItem(itemId: string): Promise<void> {
  await api.post(`/admin/moderation/${itemId}:release`, { notes: null });
}

export async function liveRejectQueueItem(itemId: string): Promise<void> {
  await api.post(`/admin/moderation/${itemId}:reject`, { notes: null });
}

export async function liveGetAdminRenders(): Promise<AdminRenderRow[]> {
  const [renders, projects, session] = await Promise.all([
    api.get<BackendAdminRenderSummary[]>("/admin/renders"),
    api.get<BackendProject[]>("/projects").catch(() => []),
    api.get<BackendSession>("/auth/session").catch(() => null),
  ]);
  const projectNameById = new Map(projects.map((project) => [project.id, project.title]));
  const activeWorkspaceName =
    session?.workspaces.find((workspace) => workspace.workspace_id === session.active_workspace_id)
      ?.workspace_name ?? "Active workspace";
  return renders.map((render) => ({
    id: render.id,
    project: projectNameById.get(render.project_id) ?? render.project_id,
    workspace: activeWorkspaceName,
    status: workflowStatus(render.status),
    provider: render.latest_step_kind ? titleize(render.latest_step_kind) : "Render pipeline",
    cost: `$${(render.latest_provider_cost_cents / 100).toFixed(2)}`,
    stuckFor:
      render.status === "failed" || render.status === "blocked"
        ? timeAgo(render.started_at ?? render.created_at)
        : "-",
    issue:
      render.error_message ||
      render.error_code ||
      (render.latest_step_kind ? `${titleize(render.latest_step_kind)} in progress` : "No issues"),
    snapshot: render.queue_name,
  }));
}

export async function liveGetAdminWorkspaces(): Promise<AdminWorkspaceRow[]> {
  const [session, usage, renders, members] = await Promise.all([
    api.get<BackendSession>("/auth/session"),
    api.get<BackendUsageSummary>("/usage").catch(() => null),
    api.get<BackendAdminRenderSummary[]>("/admin/renders").catch(() => []),
    liveGetWorkspaceMembers().catch(() => []),
  ]);
  const activeWorkspace =
    session.workspaces.find((workspace) => workspace.workspace_id === session.active_workspace_id) ??
    session.workspaces[0];
  if (!activeWorkspace) {
    return [];
  }
  const activeRenderCount = renders.filter((render) =>
    ["queued", "running", "review", "blocked"].includes(render.status),
  ).length;
  const needsAttention = renders.some((render) => render.status === "failed" || render.status === "blocked");
  return [
    {
      id: activeWorkspace.workspace_id,
      name: activeWorkspace.workspace_name,
      plan: usage?.plan_name ?? activeWorkspace.plan_name,
      seats: members.length,
      creditsRemaining: usage
        ? `${usage.credits_remaining} / ${usage.credits_total}`
        : "Usage unavailable",
      renderLoad: `${activeRenderCount} active`,
      health: needsAttention ? "Needs attention" : activeRenderCount > 5 ? "High load" : "Healthy",
      renewalDate: usage?.current_period_end_at
        ? new Date(usage.current_period_end_at).toLocaleDateString()
        : "Current cycle",
    },
  ];
}

export async function liveGetWorkspaceMembers(): Promise<
  Array<{
    id: string;
    userId: string;
    name: string;
    email: string;
    role: string;
    status: string;
  }>
> {
  const members = await api.get<
    Array<{ id: string; user_id: string; email: string; full_name: string; role: string }>
  >("/workspace/members");
  return members.map((member) => ({
    id: member.id,
    userId: member.user_id,
    name: member.full_name,
    email: member.email,
    role: titleize(member.role),
    status: "Active",
  }));
}
