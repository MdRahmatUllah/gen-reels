export type HealthTone = "neutral" | "primary" | "success" | "warning" | "error";

export type WorkflowStage =
  | "brief"
  | "ideas"
  | "script"
  | "scenes"
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
  | "failed";

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
  checks: RenderCheck[];
  steps: RenderStep[];
  events: RenderEvent[];
  metrics: {
    lufsTarget: string;
    truePeak: string;
    musicDucking: string;
    subtitleState: string;
    subtitleStyle?: string; // Phase 5 Custom style
  };
}

/* ─── Exports ─────────────────────────────────────────────────────────────── */
export interface ExportArtifact {
  id: string;
  name: string;
  status: "ready" | "processing";
  format: string;
  destination: string;
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

export interface DashboardData {
  focusProject: ProjectSummary;
  metrics: DashboardMetric[];
  notifications: AlertItem[];
  queueOverview: DashboardMetric[];
  compositionRules: RenderCheck[];
  recentProjects: ProjectSummary[];
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
