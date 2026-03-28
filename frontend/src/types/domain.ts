export type HealthTone = "neutral" | "primary" | "success" | "warning" | "error";

export type WorkflowStage =
  | "brief"
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

export interface UserProfile {
  id: string;
  name: string;
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
}

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
  versionLabel: string;
  approvalState: string;
  lastEdited: string;
  totalWords: number;
  readingTimeLabel: string;
  lines: ScriptLine[];
}

export interface ScenePlan {
  id: string;
  index: number;
  title: string;
  beat: string;
  shotType: string;
  motion: string;
  prompt: string;
  continuityScore: number;
  durationSec: number;
  transitionMode: "hard_cut" | "crossfade";
  status: WorkflowStatus;
  keyframeStatus: string;
  notes: string[];
  palette: string;
  audioCue: string;
  thumbnailLabel: string;
  gradient: string;
  subtitleStatus: string;
}

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
  };
}

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

export interface SettingsSection {
  title: string;
  description: string;
  items: Array<{
    label: string;
    value: string;
    status?: string;
  }>;
}

export interface AlertItem {
  id: string;
  label: string;
  detail: string;
  tone: HealthTone;
}

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
