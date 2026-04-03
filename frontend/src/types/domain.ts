export type HealthTone = "neutral" | "primary" | "success" | "warning" | "error";

export type WorkflowStage =
  | "brief"
  | "ideas"
  | "script"
  | "scenes"
  | "frames"
  | "renders"
  | "exports";

export type WorkflowStatus =
  | "draft"
  | "queued"
  | "running"
  | "review"
  | "approved"
  | "completed"
  | "blocked"
  | "failed"
  | "cancelled";

export type GenerationStatus = "idle" | "queued" | "running" | "completed" | "failed";

/* ─── Auth ────────────────────────────────────────────────────────────────── */
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthSession {
  user: UserProfile;
  workspaceId: string;
}

/* ─── User & Workspace ────────────────────────────────────────────────────── */
export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  avatarInitials: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  plan: string;
  seats: number;
  creditsRemaining: number;
  creditsTotal: number;
  monthlyBudget: number;
  queueCount: number;
  notifications: number;
}

/* ─── Projects ────────────────────────────────────────────────────────────── */
export interface CreateProjectPayload {
  title: string;
  client: string;
}

export type QuickCreateStarterMode = "studio_default" | "template";

export interface QuickCreateProjectPayload {
  ideaPrompt: string;
  starterMode: QuickCreateStarterMode;
  templateId?: string | null;
  captionStyle?: string | null;
}

export interface QuickCreateJobSummary {
  id: string;
  jobKind: string;
  status: "queued" | "running" | "completed" | "failed";
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
}

export interface QuickCreateStepStatus {
  stepKind: string;
  stepIndex: number;
  status: "queued" | "running" | "completed" | "failed";
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface QuickCreateProjectResponse {
  projectId: string;
  projectTitle: string;
  redirectPath: string;
  job: QuickCreateJobSummary;
}

export interface QuickCreateStatus {
  projectId: string;
  projectTitle: string;
  projectStage: WorkflowStage;
  job: QuickCreateJobSummary;
  steps: QuickCreateStepStatus[];
  currentStep: string | null;
  completedSteps: string[];
  redirectPath: string;
  recoveryPath: string;
  isActive: boolean;
  isCompleted: boolean;
  hasFailed: boolean;
}

export interface ProjectSummary {
  id: string;
  title: string;
  client: string;
  stage: WorkflowStage;
  renderStatus: WorkflowStatus;
  updatedAt: string;
  aspectRatio: string;
  sceneCount: number;
  durationSec: number;
  tags: string[];
  hook: string;
  palette: string;
  voicePreset: string;
  objective: string;
  nextMilestone: string;
  selectedIdeaId: string | null;
}

/* ─── Briefs ──────────────────────────────────────────────────────────────── */
export interface BriefData {
  objective: string;
  hook: string;
  targetAudience: string;
  callToAction: string;
  brandNorthStar: string;
  guardrails: string[];
  mustInclude: string[];
  approvalSteps: string[];
}

/* ─── Ideas ───────────────────────────────────────────────────────────────── */
export interface IdeaCandidate {
  id: string;
  title: string;
  hook: string;
  angle: string;
  tags: string[];
  viralScore: number;
}

export interface IdeaSet {
  id: string;
  projectId: string;
  status: GenerationStatus;
  ideas: IdeaCandidate[];
  generatedAt: string | null;
}

/* Series */
export type SeriesContentMode = "preset" | "custom";
export type SeriesMusicMode = "none" | "preset";
export type SeriesPrimaryCta = "start_series" | "create_video";
export type SeriesApprovalState = "needs_review" | "approved" | "rejected" | "superseded";
export type SeriesVideoPhase =
  | "queued"
  | "preparing_project"
  | "generating_scenes"
  | "generating_frames"
  | "generating_voiceover"
  | "rendering"
  | "completed"
  | "failed";

export interface SeriesCatalogOption {
  key: string;
  label: string;
  description: string;
  gender?: string | null;
  badge?: string | null;
}

export interface SeriesCatalog {
  contentPresets: SeriesCatalogOption[];
  languages: SeriesCatalogOption[];
  voices: SeriesCatalogOption[];
  music: SeriesCatalogOption[];
  artStyles: SeriesCatalogOption[];
  captionStyles: SeriesCatalogOption[];
  effects: SeriesCatalogOption[];
}

export interface SeriesInput {
  title: string;
  description: string;
  contentMode: SeriesContentMode;
  presetKey: string | null;
  customTopic: string;
  customExampleScript: string;
  languageKey: string;
  voiceKey: string;
  musicMode: SeriesMusicMode;
  musicKeys: string[];
  artStyleKey: string;
  captionStyleKey: string;
  effectKeys: string[];
}

export interface SeriesSummary extends SeriesInput {
  id: string;
  workspaceId: string;
  ownerUserId: string;
  totalScriptCount: number;
  scriptsAwaitingReviewCount: number;
  approvedScriptCount: number;
  completedVideoCount: number;
  latestRunId: string | null;
  latestRunStatus: WorkflowStatus | null;
  activeRunId: string | null;
  activeRunStatus: WorkflowStatus | null;
  activeVideoRunId: string | null;
  activeVideoRunStatus: WorkflowStatus | null;
  primaryCta: SeriesPrimaryCta;
  canEdit: boolean;
  lastActivityAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface SeriesDetail extends SeriesSummary {}

export interface SeriesRevisionSummary {
  id: string;
  seriesScriptId: string;
  revisionNumber: number;
  approvalState: SeriesApprovalState;
  title: string;
  summary: string;
  estimatedDurationSeconds: number;
  readingTimeLabel: string;
  totalWords: number;
  lines: ScriptLine[];
  videoTitle: string;
  videoDescription: string;
  createdAt: string;
  updatedAt: string;
}

export interface SeriesPublishedVideo {
  projectId: string | null;
  renderJobId: string | null;
  exportId: string | null;
  downloadUrl: string | null;
  title: string;
  description: string;
  completedAt: string | null;
}

export interface SeriesScript {
  id: string;
  seriesId: string;
  seriesRunId: string;
  createdByUserId: string | null;
  sequenceNumber: number;
  title: string;
  summary: string;
  estimatedDurationSeconds: number;
  readingTimeLabel: string;
  totalWords: number;
  lines: ScriptLine[];
  approvalState: SeriesApprovalState;
  videoStatus: WorkflowStatus | null;
  videoPhase: SeriesVideoPhase | "completed" | null;
  videoCurrentSceneIndex: number | null;
  videoCurrentSceneCount: number | null;
  videoRenderJobId: string | null;
  videoHiddenProjectId: string | null;
  currentRevision: SeriesRevisionSummary | null;
  approvedRevision: SeriesRevisionSummary | null;
  publishedRevision: SeriesRevisionSummary | null;
  publishedVideo: SeriesPublishedVideo | null;
  canApprove: boolean;
  canReject: boolean;
  canRegenerate: boolean;
  canCreateVideo: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SeriesSceneAsset {
  assetId: string;
  downloadUrl: string | null;
}

export interface SeriesScenePreview {
  sceneSegmentId: string;
  sceneIndex: number;
  title: string;
  beat: string;
  narrationText: string;
  captionText: string;
  targetDurationSeconds: number;
  visualPrompt: string;
  startImagePrompt: string;
  endImagePrompt: string;
  startFrameAsset: SeriesSceneAsset | null;
  endFrameAsset: SeriesSceneAsset | null;
  narrationAsset: SeriesSceneAsset | null;
  slideAsset: SeriesSceneAsset | null;
}

export interface SeriesScriptDetail {
  script: SeriesScript;
  revisions: SeriesRevisionSummary[];
  scenes: SeriesScenePreview[];
  latestRenderJobId: string | null;
  latestRenderStatus: WorkflowStatus | null;
  latestScenePlanId: string | null;
}

export interface SeriesRunStep {
  id: string;
  seriesRunId: string;
  seriesId: string;
  seriesScriptId: string | null;
  stepIndex: number;
  sequenceNumber: number;
  status: WorkflowStatus;
  inputPayload: Record<string, unknown>;
  outputPayload: Record<string, unknown> | null;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SeriesRun {
  id: string;
  seriesId: string;
  workspaceId: string;
  createdByUserId: string;
  status: WorkflowStatus;
  requestedScriptCount: number;
  completedScriptCount: number;
  failedScriptCount: number;
  idempotencyKey: string;
  requestHash: string;
  payload: Record<string, unknown>;
  errorCode: string | null;
  errorMessage: string | null;
  retryCount: number;
  startedAt: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  createdAt: string;
  updatedAt: string;
  steps: SeriesRunStep[];
  currentStep: number | null;
}

export interface SeriesVideoRunStep {
  id: string;
  seriesVideoRunId: string;
  seriesId: string;
  seriesScriptId: string;
  seriesScriptRevisionId: string;
  stepIndex: number;
  sequenceNumber: number;
  status: WorkflowStatus;
  phase: SeriesVideoPhase;
  hiddenProjectId: string | null;
  renderJobId: string | null;
  lastRenderEventSequence: number;
  currentSceneIndex: number | null;
  currentSceneCount: number | null;
  inputPayload: Record<string, unknown>;
  outputPayload: Record<string, unknown> | null;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SeriesVideoRun {
  id: string;
  seriesId: string;
  workspaceId: string;
  createdByUserId: string;
  status: WorkflowStatus;
  requestedVideoCount: number;
  completedVideoCount: number;
  failedVideoCount: number;
  idempotencyKey: string;
  requestHash: string;
  payload: Record<string, unknown>;
  errorCode: string | null;
  errorMessage: string | null;
  retryCount: number;
  startedAt: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  createdAt: string;
  updatedAt: string;
  steps: SeriesVideoRunStep[];
  currentStep: number | null;
}

/* ─── Scripts ─────────────────────────────────────────────────────────────── */
export interface ScriptLine {
  id: string;
  sceneId: string;
  beat: string;
  narration: string;
  caption: string;
  durationSec: number;
  status: WorkflowStatus;
  visualDirection: string;
  voicePacing: string;
}

export interface ScriptData {
  id: string;
  versionLabel: string;
  approvalState: string;
  lastEdited: string;
  totalWords: number;
  readingTimeLabel: string;
  fullText: string;
  lines: ScriptLine[];
}

/* ─── Scenes ──────────────────────────────────────────────────────────────── */
export interface SceneSegment {
  id: string;
  index: number;
  narration: string;
  caption: string;
  estimatedDurationSec: number;
  estimatedWordCount: number;
  durationWarning: string | null;
  sourceLineIds: string[];
}

export interface ScenePlan {
  id: string;
  index: number;
  title: string;
  beat: string;
  shotType: string;
  motion: string;
  prompt: string;
  startImagePrompt: string;
  endImagePrompt: string;
  continuityScore: number;
  durationSec: number;
  estimatedWordCount: number;
  durationWarning: string | null;
  transitionMode: "hard_cut" | "crossfade";
  status: WorkflowStatus;
  keyframeStatus: string;
  notes: string[];
  promptHistory: string[]; // Phase 5 lineage tracking
  palette: string;
  audioCue: string;
  thumbnailLabel: string;
  gradient: string;
  subtitleStatus: string;
  narration: string;
  caption: string;
  visualDirection: string;
  voicePacing: string;
  version: number;
}

export type ScenePlanApprovalState = "draft" | "pending" | "approved";

export interface ScenePlanSet {
  id: string;
  projectId: string;
  status: GenerationStatus;
  approvalState: ScenePlanApprovalState;
  approvedAt: string | null;
  scenes: ScenePlan[];
  segments: SceneSegment[];
  totalDurationSec: number;
  warningsCount: number;
  visualPresetId: string | null;
  voicePresetId: string | null;
}

export interface VisualPreset {
  id: string;
  name: string;
  description: string;
  category: string;
  style: string;
  palette: string;
  lighting: string;
}

export interface VoicePreset {
  id: string;
  name: string;
  description: string;
  tone: string;
  pacing: string;
  accent: string;
}

/* ─── Renders ─────────────────────────────────────────────────────────────── */
export interface RenderCheck {
  id: string;
  label: string;
  status: "pass" | "warning" | "fail";
  detail: string;
}

export interface RenderStep {
  id: string;
  sceneId: string;
  name: string;
  status: WorkflowStatus;
  /** Backend step_index (e.g. 100 + scene_index for frame pairs) */
  stepIndex?: number;
  /** Backend step_kind, e.g. frame_pair_generation */
  stepKind?: string;
  /** Raw API status before workflowStatus mapping */
  backendStatus?: string;
  /** Present when the step failed */
  errorCode?: string | null;
  errorMessage?: string | null;
  durationDeltaSec: number;
  clipStatus: string;
  narrationStatus: string;
  consistency: string;
  nextAction: string;
  creditCost?: number;
}

export interface RenderEvent {
  id: string;
  time: string;
  label: string;
  detail: string;
  tone: HealthTone;
}

export interface RenderFrameAssetRef {
  id: string;
  sceneSegmentId: string | null;
  assetRole: string;
  downloadUrl: string | null;
}

export interface RenderJob {
  id: string;
  label: string;
  status: WorkflowStatus;
  progress: number;
  createdAt: string;
  updatedAt: string;
  durationSec: number;
  transitionMode: "hard_cut" | "crossfade";
  voicePreset: string;
  consistencyPackSnapshotId: string;
  sseState: string;
  nextAction: string;
  musicTrack: string;
  allowExportWithoutMusic: boolean;
  /** Scene plan this render was created from, when present */
  scenePlanId?: string | null;
  /** Set when the render job failed */
  errorCode?: string | null;
  errorMessage?: string | null;
  /** Presigned download URL for the final export MP4, when render is completed */
  exportUrl: string | null;
  frameAssets?: RenderFrameAssetRef[];
  checks: RenderCheck[];
  steps: RenderStep[];
  events: RenderEvent[];
  metrics: {
    lufsTarget: string;
    truePeak: string;
    musicDucking: string;
    subtitleState: string;
    subtitleStyle?: string;
  };
  /** True when this render was initiated as a final video generation (with render settings), not just keyframe generation */
  isVideoGeneration?: boolean;
  /** Video effects applied during this render */
  videoEffects?: VideoEffectsProfile;
}

/* ─── Exports ─────────────────────────────────────────────────────────────── */
export interface ExportArtifact {
  id: string;
  name: string;
  status: "ready" | "processing";
  format: string;
  destination: string;
  downloadUrl: string | null;
  durationSec: number;
  sizeMb: number;
  integratedLufs: number;
  truePeak: number;
  subtitles: boolean;
  musicBed: boolean;
  createdAt: string;
  gradient: string;
  ratio: string;
}

/* ─── Assets Library (Phase 5) ───────────────────────────────────────────── */
export interface AssetRecord {
  id: string;
  type: "image" | "video" | "audio";
  sourceProjectId: string | null;
  sourceSceneId: string | null;
  thumbnailUrl: string;
  url: string;
  prompt: string;
  tags: string[];
  createdAt: string;
}

/* ─── Presets ─────────────────────────────────────────────────────────────── */
export interface PresetCard {
  id: string;
  name: string;
  category: "visual" | "voice" | "music" | "subtitle";
  description: string;
  tags: string[];
  status: string;
  transitionMode?: string;
  voice?: string;
  look?: string;
}

/* ─── Render Presets ──────────────────────────────────────────────────────── */
export type RenderPresetCategory =
  | "social"
  | "corporate"
  | "cinematic"
  | "minimal"
  | "custom";

export interface RenderPresetSettings {
  animationEffect: string;
  subtitleStyle: string;
  musicTrack: string;
  musicDucking: string;
  transitionMode: "hard_cut" | "crossfade";
  videoEffects: VideoEffectsProfile;
}

export interface RenderPreset {
  id: string;
  name: string;
  description: string;
  category: RenderPresetCategory;
  gradient: string;
  icon: string;
  settings: RenderPresetSettings;
  tags: string[];
  recommended?: boolean;
}

/* ─── Video Effects ──────────────────────────────────────────────────────── */
export type ColorFilterType =
  | "none"
  | "warm"
  | "cool"
  | "sepia"
  | "grayscale"
  | "vintage"
  | "vibrant"
  | "moody";

export interface VideoEffectsProfile {
  brightness: number;
  contrast: number;
  saturation: number;
  speed: number;
  fadeInSec: number;
  fadeOutSec: number;
  colorFilter: ColorFilterType;
  vignetteStrength: number;
}

export const DEFAULT_VIDEO_EFFECTS: VideoEffectsProfile = {
  brightness: 0,
  contrast: 0,
  saturation: 0,
  speed: 1.0,
  fadeInSec: 0,
  fadeOutSec: 0,
  colorFilter: "none",
  vignetteStrength: 0,
};

/* ─── Editor Settings ────────────────────────────────────────────────────── */
export interface EditorSettings {
  subtitleEnabled: boolean;
  subtitleStyle: string;
  subtitleFont: string;
  subtitlePosition: "top" | "center" | "bottom";
  subtitleColor: string;
  musicEnabled: boolean;
  musicTrack: string;
  musicVolume: number;
  musicDucking: string;
  musicFadeIn: number;
  musicFadeOut: number;
  videoEffects: VideoEffectsProfile;
  animationEffect: string;
  transitionMode: "hard_cut" | "crossfade";
}

export interface TemplateCard {
  id: string;
  name: string;
  description: string;
  duration: string;
  scenes: number;
  style: string;
}

/* ─── Billing ─────────────────────────────────────────────────────────────── */
export interface BillingBreakdown {
  category: string;
  usage: string;
  unitCost: string;
  total: string;
}

export interface InvoiceItem {
  id: string;
  label: string;
  amount: string;
  date: string;
  status: string;
}

export interface UsageRecord {
  id: string;
  projectId: string;
  description: string;
  credits: number;
  timestamp: string;
}

/* ─── Settings ────────────────────────────────────────────────────────────── */
export interface SettingsSection {
  title: string;
  description: string;
  items: Array<{
    label: string;
    value: string;
    status?: string;
  }>;
}

/* ─── Alerts ──────────────────────────────────────────────────────────────── */
export interface AlertItem {
  id: string;
  label: string;
  detail: string;
  tone: HealthTone;
}

/* ─── Dashboard ───────────────────────────────────────────────────────────── */
export interface DashboardMetric {
  label: string;
  value: string;
  detail: string;
  tone: HealthTone;
}

export interface DashboardVideo {
  id: string;
  projectId: string;
  projectTitle: string;
  name: string;
  status: "ready" | "processing";
  downloadUrl: string | null;
  durationSec: number;
  createdAt: string;
  format: string;
  gradient: string;
}

export interface DashboardData {
  focusProject: ProjectSummary;
  metrics: DashboardMetric[];
  notifications: AlertItem[];
  queueOverview: DashboardMetric[];
  compositionRules: RenderCheck[];
  recentProjects: ProjectSummary[];
  recentVideos: DashboardVideo[];
}

/* ─── Bundles ─────────────────────────────────────────────────────────────── */
export interface ProjectBundle {
  project: ProjectSummary;
  brief: BriefData;
  script: ScriptData;
  scenes: ScenePlan[];
  renderJobs: RenderJob[];
  exports: ExportArtifact[];
}

export interface ShellData {
  user: UserProfile;
  workspaces: WorkspaceSummary[];
  projects: ProjectSummary[];
  alerts: AlertItem[];
}

export interface BillingData {
  planName: string;
  cycleLabel: string;
  creditsRemaining: number;
  creditsTotal: number;
  projectedSpend: string;
  usageBreakdown: BillingBreakdown[];
  invoices: InvoiceItem[];
}

/* ─── Admin ───────────────────────────────────────────────────────────────── */
export interface AdminQueueItem {
  id: string;
  workspace: string;
  project: string;
  step: string;
  status: WorkflowStatus;
  retries: number;
  owner: string;
  age: string;
  provider: string;
}

export interface AdminWorkspaceRow {
  id: string;
  name: string;
  plan: string;
  seats: number;
  creditsRemaining: string;
  renderLoad: string;
  health: string;
  renewalDate: string;
}

/* ─── Phase 6: Collaboration & Studio ─────────────────────────────────────── */

export interface BrandKit {
  id: string;
  version?: number;
  name: string;
  brandNorthStar: string;
  primaryPalette: string;
  fontFamily: string;
}

export interface Comment {
  id: string;
  targetId: string;
  authorName: string;
  text: string;
  timestamp: string;
  resolved: boolean;
}

export interface AdminRenderRow {
  id: string;
  project: string;
  workspace: string;
  status: WorkflowStatus;
  provider: string;
  cost: string;
  stuckFor: string;
  issue: string;
  snapshot: string;
}

/* ─── Phase 7: Local & BYO ────────────────────────────────────────────────── */
export type ExecutionMode = "hosted" | "byo" | "local";
export type ProviderModality = "text" | "moderation" | "image" | "video" | "speech";
export type ProviderGenerationType = "text" | "moderation" | "image" | "video" | "audio";
export type ProviderValidationStatus =
  | "not_validated"
  | "valid"
  | "invalid"
  | "unsupported"
  | "unreachable";

export interface ProviderCatalogField {
  key: "endpoint" | "apiVersion" | "deployment" | "modelName" | "voice" | "apiKey";
  label: string;
  placeholder?: string;
  help?: string;
  required?: boolean;
  secret?: boolean;
}

export interface ProviderCatalogOption {
  providerKey: string;
  providerLabel: string;
  modality: ProviderModality;
  generationType: ProviderGenerationType;
  description: string;
  supportsActivation: boolean;
  fields: ProviderCatalogField[];
  /** Prefill form fields when this provider is selected (add-credential flow). */
  formDefaults?: Partial<
    Record<"endpoint" | "apiVersion" | "deployment" | "modelName" | "voice" | "apiKey", string>
  >;
}

export interface ProviderCredentialRecord {
  id: string;
  name: string;
  modality: ProviderModality;
  generationType: ProviderGenerationType;
  providerKey: string;
  providerLabel: string;
  supportsActivation: boolean;
  endpoint: string;
  apiVersion: string;
  deployment: string;
  modelName: string;
  voice: string;
  secretConfigured: boolean;
  isActive: boolean;
  activeMode: ExecutionMode | null;
  createdAt: string;
  updatedAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
  validationStatus: ProviderValidationStatus;
  lastValidatedAt: string | null;
  validationError: string | null;
}

export interface ProviderCredentialInput {
  name: string;
  modality: ProviderModality;
  providerKey: string;
  endpoint?: string;
  apiVersion?: string;
  deployment?: string;
  modelName?: string;
  voice?: string;
  apiKey?: string;
  setAsActiveRoute?: boolean;
}

export interface ProviderExecutionRoute {
  mode: ExecutionMode;
  providerKey: string;
  providerLabel: string;
  credentialId: string | null;
  generationType: ProviderGenerationType;
}

export interface WorkspaceExecutionPolicy {
  text: ProviderExecutionRoute;
  moderation: ProviderExecutionRoute;
  image: ProviderExecutionRoute;
  video: ProviderExecutionRoute;
  speech: ProviderExecutionRoute;
}

export interface ProviderKey {
  id: string;
  provider: "openai" | "stability" | "elevenlabs" | "runway";
  keyPrefix: string;
  createdAt: string;
}

export interface LocalWorker {
  id: string;
  name: string;
  status: "online" | "offline" | "busy";
  lastHeartbeat: string;
  capabilities: {
    orderedReferenceImages: boolean;
    localTTS: boolean;
    videoFrames: boolean;
  };
}

/* ─── Video Library ───────────────────────────────────────────────────────── */
export interface LocalFolderProject {
  id: string;
  workspace_id: string;
  name: string;
  path: string;
  created_at: string;
}

export interface VideoLibraryProject {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface LocalVideoFile {
  name: string;
  path: string;
  size_bytes: number;
  content_type: string;
}

export interface BrowseFolderResult {
  path: string;
  files: LocalVideoFile[];
}

export interface VideoLibraryItem {
  id: string;
  workspace_id: string;
  project_id: string | null;
  file_name: string;
  content_type: string;
  size_bytes: number;
  duration_ms: number | null;
  width: number | null;
  height: number | null;
  url: string;
  created_at: string;
  updated_at: string;
}

export interface UploadLocalFilePayload {
  local_path: string;
  project_id?: string | null;
}

/* ─── Remix ───────────────────────────────────────────────────────────────── */
export interface RemixProject {
  id: string;
  workspace_id: string;
  name: string;
  source_project_id: string | null;
  visual_effects: Record<string, unknown>;
  subtitle_config: Record<string, unknown>;
  target_duration_ms: number;
  clip_mode: "random" | "unique";
  output_project_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RemixAnalysis {
  possible_videos: number;
  total_clips: number;
  total_duration_ms: number;
  clips_with_duration: number;
}

export interface RemixVideo {
  id: string;
  job_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  clip_ids: string[];
  output_item_id: string | null;
  error_message: string | null;
  created_at: string;
}

export interface RemixJob {
  id: string;
  remix_project_id: string;
  workspace_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  total_videos: number;
  completed_videos: number;
  failed_videos: number;
  videos: RemixVideo[];
  created_at: string;
  updated_at: string;
}

export interface RemixProjectCreatePayload {
  name: string;
  source_project_id: string | null;
  visual_effects: Record<string, unknown>;
  subtitle_config: Record<string, unknown>;
  target_duration_ms: number;
  clip_mode: "random" | "unique";
}

