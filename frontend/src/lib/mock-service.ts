/**
 * Stateful mock service that simulates the backend API.
 * All data lives in-memory. Idea and script generation use realistic delays.
 * This replaces the old static mock-api.ts for Phase 1 interactive flows.
 */
import type {
  AuthSession,
  BriefData,
  CreateProjectPayload,
  DashboardData,
  IdeaCandidate,
  IdeaSet,
  LoginCredentials,
  ProjectBundle,
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
  SettingsSection,
} from "../types/domain";

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
}

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
  await randomDelay(400, 1000);

  if (credentials.email === "alex@studio.io" && credentials.password === "password123") {
    state.isAuthenticated = true;
    return { user: state.user, workspaceId: state.activeWorkspaceId };
  }

  throw new Error("Invalid email or password");
}

export async function mockLogout(): Promise<void> {
  await randomDelay(200, 400);
  state.isAuthenticated = false;
}

export async function mockGetSession(): Promise<AuthSession | null> {
  await delay(100);
  if (!state.isAuthenticated) return null;
  return { user: state.user, workspaceId: state.activeWorkspaceId };
}

/* ─── Project API ─────────────────────────────────────────────────────────── */
export async function mockGetProjects(): Promise<ProjectSummary[]> {
  await randomDelay();
  return Array.from(state.projects.values());
}

export async function mockGetProject(projectId: string): Promise<ProjectSummary> {
  await randomDelay(100, 300);
  const project = state.projects.get(projectId);
  if (!project) throw new Error(`Project ${projectId} not found`);
  return project;
}

export async function mockCreateProject(payload: CreateProjectPayload): Promise<ProjectSummary> {
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
export async function mockGetBrief(projectId: string): Promise<BriefData> {
  await randomDelay(100, 300);
  const brief = state.briefs.get(projectId);
  if (!brief) throw new Error(`Brief for ${projectId} not found`);
  return brief;
}

export async function mockUpdateBrief(projectId: string, data: Partial<BriefData>): Promise<BriefData> {
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
  await randomDelay(100, 200);
  return state.ideaSets.get(projectId) ?? null;
}

export async function mockGenerateIdeas(projectId: string): Promise<IdeaSet> {
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
  await randomDelay(100, 200);
  return state.scripts.get(projectId) ?? null;
}

export async function mockGenerateScript(projectId: string): Promise<ScriptData> {
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
  await randomDelay();
  return [
    { id: "vp_1", name: "Warm Cinematic", category: "visual", description: "Golden hour tones with filmic grain", tags: ["warm", "cinematic"], status: "active" },
    { id: "vp_2", name: "Confident Narrator", category: "voice", description: "Clear, authoritative male voice at natural pace", tags: ["male", "confident"], status: "active", voice: "en-US-Guy" },
  ];
}

export async function mockGetTemplates(): Promise<TemplateCard[]> {
  await randomDelay();
  return [
    { id: "tpl_1", name: "Product Launch 60s", description: "Hook → Problem → Solution → CTA", duration: "60s", scenes: 6, style: "Minimal" },
  ];
}

export async function mockGetSettings(): Promise<SettingsSection[]> {
  await randomDelay();
  return [
    { title: "Workspace", description: "General workspace configuration", items: [{ label: "Name", value: "North Star Studio" }, { label: "Plan", value: "Pro" }] },
  ];
}
