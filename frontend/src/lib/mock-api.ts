import type {
  AdminQueueItem,
  AdminRenderRow,
  AdminWorkspaceRow,
  AlertItem,
  BillingData,
  DashboardData,
  ExportArtifact,
  PresetCard,
  ProjectBundle,
  ProjectSummary,
  RenderJob,
  SettingsSection,
  ShellData,
  TemplateCard,
  WorkspaceSummary,
  UserProfile,
} from "../types/domain";

const mockDelay = (duration = 180) =>
  new Promise((resolve) => window.setTimeout(resolve, duration));

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export const defaultProjectId = "project_aurora_serum";

const currentUser: UserProfile = {
  id: "user_md",
  name: "M. Rahmatullah",
  role: "Creative Director",
  avatarInitials: "MR",
};

const workspaces: WorkspaceSummary[] = [
  {
    id: "workspace_north_star",
    name: "North Star Studio",
    plan: "Pro Studio",
    seats: 8,
    creditsRemaining: 1480,
    creditsTotal: 2500,
    monthlyBudget: 8900,
    queueCount: 4,
    notifications: 3,
  },
];

const shellAlerts: AlertItem[] = [
  {
    id: "alert_timing",
    label: "Scene 3 needs a timing review",
    detail: "Narration runs 1.2 seconds long, so the composition worker is preparing a freeze-frame pad.",
    tone: "warning",
  },
  {
    id: "alert_export",
    label: "Two exports are ready for approval",
    detail: "Aurora Serum has fresh TikTok and Reels masters with loudness data attached.",
    tone: "success",
  },
  {
    id: "alert_provider",
    label: "Video provider latency is climbing",
    detail: "Kling queue times are up 18% in the last hour, but no jobs are blocked yet.",
    tone: "primary",
  },
];

const auroraProject: ProjectSummary = {
  id: "project_aurora_serum",
  title: "Aurora Serum Launch",
  client: "North Star Studio",
  stage: "renders",
  renderStatus: "running",
  updatedAt: "6 min ago",
  aspectRatio: "9:16",
  sceneCount: 5,
  durationSec: 34,
  tags: ["beauty", "launch", "education"],
  hook: "Cold open on a laboratory-grade serum texture with a science-backed promise in the first three seconds.",
  palette: "Frosted cobalt",
  voicePreset: "Ava Editorial",
  objective: "Turn a clinical skincare claim into a premium, scroll-stopping short-form launch asset.",
  nextMilestone: "Approve the master export and social cutdowns.",
};

const opsProject: ProjectSummary = {
  id: "project_ops_playbook",
  title: "Creator Ops Playbook",
  client: "North Star Studio",
  stage: "script",
  renderStatus: "review",
  updatedAt: "42 min ago",
  aspectRatio: "9:16",
  sceneCount: 4,
  durationSec: 29,
  tags: ["b2b", "ops", "thought leadership"],
  hook: "A sharp creator-economy explainer that visualizes chaos turning into a repeatable system.",
  palette: "Slate cyan",
  voicePreset: "Noah Systems",
  objective: "Explain creator operations workflow clearly enough for agency leads to book a strategy call.",
  nextMilestone: "Lock the final script and promote the keyframe plan.",
};

const midnightProject: ProjectSummary = {
  id: "project_midnight_capsules",
  title: "Midnight Capsules",
  client: "North Star Studio",
  stage: "brief",
  renderStatus: "draft",
  updatedAt: "2 hrs ago",
  aspectRatio: "9:16",
  sceneCount: 6,
  durationSec: 41,
  tags: ["supplement", "wellness", "ugc"],
  hook: "Late-night relief with cinematic moonlit product photography and whispered confidence.",
  palette: "Ink ivory",
  voicePreset: "Sera Calm",
  objective: "Frame the supplement as a ritual product with a premium but accessible emotional tone.",
  nextMilestone: "Approve the brief guardrails before script generation.",
};

const auroraRenderJobs: RenderJob[] = [
  {
    id: "render_018",
    label: "Render 18 · Master vertical export",
    status: "running",
    progress: 74,
    createdAt: "Today, 10:44 AM",
    updatedAt: "21 seconds ago",
    durationSec: 34,
    transitionMode: "crossfade",
    voicePreset: "Ava Editorial",
    consistencyPackSnapshotId: "cps_aurora_2026_03_20_v4",
    sseState: "Live SSE connected · polling fallback armed after 3 reconnects",
    nextAction: "Review Scene 3 timing once composition completes.",
    musicTrack: "Glass Current v2",
    allowExportWithoutMusic: false,
    checks: [
      {
        id: "check_provenance",
        label: "Consistency pack provenance",
        status: "pass",
        detail: "All scene clips reference snapshot cps_aurora_2026_03_20_v4.",
      },
      {
        id: "check_duration",
        label: "Duration verification",
        status: "warning",
        detail: "Scene 3 narration exceeds the clip by 1.2 seconds, so a freeze-frame pad is queued.",
      },
      {
        id: "check_stream",
        label: "Asset stream probe",
        status: "pass",
        detail: "Every clip matches the 1080x1920 export profile and stereo audio configuration.",
      },
      {
        id: "check_music",
        label: "Music underlay continuity",
        status: "pass",
        detail: "The bed loops once with a 2-second crossfade and a 1.5-second end fade.",
      },
    ],
    steps: [
      {
        id: "step_scene_01",
        sceneId: "scene_01",
        name: "Scene 1 A/V sync",
        status: "completed",
        durationDeltaSec: 0.2,
        clipStatus: "Clip approved",
        narrationStatus: "Voice aligned",
        consistency: "Snapshot pinned",
        nextAction: "No action needed",
      },
      {
        id: "step_scene_02",
        sceneId: "scene_02",
        name: "Scene 2 A/V sync",
        status: "completed",
        durationDeltaSec: -0.3,
        clipStatus: "Clip approved",
        narrationStatus: "Voice aligned",
        consistency: "Snapshot pinned",
        nextAction: "No action needed",
      },
      {
        id: "step_scene_03",
        sceneId: "scene_03",
        name: "Scene 3 duration pad",
        status: "running",
        durationDeltaSec: 1.2,
        clipStatus: "Freeze-frame pad in progress",
        narrationStatus: "Narration ready",
        consistency: "Snapshot pinned",
        nextAction: "Inspect the pad frame before approving composition",
      },
      {
        id: "step_scene_04",
        sceneId: "scene_04",
        name: "Scene 4 subtitle timing",
        status: "completed",
        durationDeltaSec: 0,
        clipStatus: "Clip approved",
        narrationStatus: "Voice aligned",
        consistency: "Snapshot pinned",
        nextAction: "No action needed",
      },
      {
        id: "step_comp",
        sceneId: "scene_05",
        name: "Composition and loudnorm",
        status: "queued",
        durationDeltaSec: 0,
        clipStatus: "Waiting on Scene 3",
        narrationStatus: "All narration cached",
        consistency: "Ready",
        nextAction: "Will start after pad render",
      },
    ],
    events: [
      {
        id: "event_01",
        time: "10:44:14",
        label: "Render job started",
        detail: "Provider manifests were frozen and the voice preset snapshot was sealed.",
        tone: "primary",
      },
      {
        id: "event_02",
        time: "10:45:11",
        label: "Scene 1 clip completed",
        detail: "Kling returned the shot with the correct serum reflection and palette.",
        tone: "success",
      },
      {
        id: "event_03",
        time: "10:46:39",
        label: "Duration mismatch detected",
        detail: "Scene 3 narration overshot the clip, so the FFmpeg worker queued a freeze-frame pad.",
        tone: "warning",
      },
      {
        id: "event_04",
        time: "10:47:02",
        label: "Subtitle pass cached",
        detail: "Scene 4 subtitles were aligned to narration timings for burn-in.",
        tone: "neutral",
      },
    ],
    metrics: {
      lufsTarget: "-14 LUFS integrated",
      truePeak: "-1.0 dBTP ceiling",
      musicDucking: "-12 dB under narration with 0.3s fades",
      subtitleState: "Burn-in enabled for master vertical export",
    },
  },
  {
    id: "render_017",
    label: "Render 17 · Approval preview",
    status: "completed",
    progress: 100,
    createdAt: "Yesterday, 4:12 PM",
    updatedAt: "Yesterday, 4:17 PM",
    durationSec: 33,
    transitionMode: "hard_cut",
    voicePreset: "Ava Editorial",
    consistencyPackSnapshotId: "cps_aurora_2026_03_19_v3",
    sseState: "Completed",
    nextAction: "Use as fallback if Render 18 timing changes feel too slow.",
    musicTrack: "Glass Current v1",
    allowExportWithoutMusic: false,
    checks: [
      {
        id: "check_prev_provenance",
        label: "Consistency pack provenance",
        status: "pass",
        detail: "All scenes share snapshot cps_aurora_2026_03_19_v3.",
      },
      {
        id: "check_prev_duration",
        label: "Duration verification",
        status: "pass",
        detail: "All narration clips stayed within tolerance.",
      },
      {
        id: "check_prev_stream",
        label: "Asset stream probe",
        status: "pass",
        detail: "The stream probe passed with uniform H.264 and AAC outputs.",
      },
      {
        id: "check_prev_music",
        label: "Music underlay continuity",
        status: "pass",
        detail: "Music looped once with no restart artifact.",
      },
    ],
    steps: [],
    events: [],
    metrics: {
      lufsTarget: "-14.1 LUFS achieved",
      truePeak: "-0.9 dBTP peak",
      musicDucking: "Continuous bed approved",
      subtitleState: "Burn-in complete",
    },
  },
];

const auroraExports: ExportArtifact[] = [
  {
    id: "export_master",
    name: "Aurora Serum Master",
    status: "ready",
    format: "MP4 / H.264",
    destination: "TikTok + Instagram Reels",
    durationSec: 34,
    sizeMb: 39.4,
    integratedLufs: -14.1,
    truePeak: -0.9,
    subtitles: true,
    musicBed: true,
    createdAt: "Today, 10:18 AM",
    gradient: "linear-gradient(145deg, #e6f0ff 0%, #c7d9ff 52%, #fdfdff 100%)",
    ratio: "9:16",
  },
  {
    id: "export_cutdown",
    name: "Aurora Serum 15s Cutdown",
    status: "processing",
    format: "MP4 / H.264",
    destination: "Stories",
    durationSec: 15,
    sizeMb: 15.8,
    integratedLufs: -14.0,
    truePeak: -1,
    subtitles: true,
    musicBed: true,
    createdAt: "Today, 10:49 AM",
    gradient: "linear-gradient(145deg, #f0f6ff 0%, #dce7ff 40%, #eef2ff 100%)",
    ratio: "9:16",
  },
];

const projectBundles: Record<string, ProjectBundle> = {
  [auroraProject.id]: {
    project: auroraProject,
    brief: {
      objective:
        "Sell the serum as a precise, clinically credible beauty upgrade without losing the softness expected from premium skincare creative.",
      hook: "Show the serum texture like a hero object, then land a fast clinical claim before the scroll breaks.",
      targetAudience:
        "Women 22-34 who save skincare routines and respond to ingredient-led creators on TikTok and Reels.",
      callToAction: "Tap through for the 14-day glow trial.",
      brandNorthStar:
        "A clean production studio mood: premium, scientific, calm, and materially precise.",
      guardrails: [
        "Avoid exaggerated medical language or before/after promises.",
        "Keep the product centered with negative space for subtitles.",
        "Use cool daylight palettes instead of warm beauty glam.",
      ],
      mustInclude: [
        "Peptide complex callout in scene two.",
        "Glass pipette hero shot within the opening five seconds.",
        "Visible CTA card in the closing scene.",
      ],
      approvalSteps: [
        "Client signs off on claims and CTA copy.",
        "Creative lead approves the scene progression and tone.",
        "Operations verifies platform-safe caption treatment.",
      ],
    },
    script: {
      versionLabel: "v12 approved",
      approvalState: "Approved for render",
      lastEdited: "Today, 10:22 AM",
      totalWords: 108,
      readingTimeLabel: "34s final narration",
      lines: [
        {
          id: "line_01",
          sceneId: "scene_01",
          beat: "Texture reveal",
          narration:
            "This is the serum creators reach for when they want glow that still feels clinically grounded.",
          caption: "Clinical glow, not guesswork.",
          durationSec: 7,
          status: "approved",
          visualDirection: "Macro glass, liquid movement, crisp white reflections",
          voicePacing: "Measured and calm",
        },
        {
          id: "line_02",
          sceneId: "scene_02",
          beat: "Ingredient proof",
          narration:
            "Peptides and barrier support work together here, so the result reads expensive before you even mention the price.",
          caption: "Peptides + barrier support",
          durationSec: 8,
          status: "approved",
          visualDirection: "Laboratory still-life with layered ingredient overlays",
          voicePacing: "Confident but not rushed",
        },
        {
          id: "line_03",
          sceneId: "scene_03",
          beat: "Benefit bridge",
          narration:
            "It sits beautifully under makeup, but the real win is how polished your skin looks on camera by day fourteen.",
          caption: "Camera-ready by day 14",
          durationSec: 7,
          status: "approved",
          visualDirection: "Mirror move with soft motion blur and cool daylight tones",
          voicePacing: "Slightly brighter emphasis on day fourteen",
        },
        {
          id: "line_04",
          sceneId: "scene_04",
          beat: "Ritual moment",
          narration:
            "That means your routine feels lighter, cleaner, and easier to keep consistent every single morning.",
          caption: "A lighter ritual you keep using",
          durationSec: 6,
          status: "approved",
          visualDirection: "Vanity composition, airy hand motion, gentle rack focus",
          voicePacing: "Warm and reassuring",
        },
        {
          id: "line_05",
          sceneId: "scene_05",
          beat: "CTA close",
          narration:
            "Try Aurora for fourteen days and see why the comment section keeps asking for the routine details.",
          caption: "Start the 14-day glow trial",
          durationSec: 6,
          status: "approved",
          visualDirection: "Product front-on with CTA slate and subtle glow sweep",
          voicePacing: "Direct, polished CTA",
        },
      ],
    },
    scenes: [
      {
        id: "scene_01",
        index: 1,
        title: "Macro serum reveal",
        beat: "Hook the scroll with material luxury.",
        shotType: "Macro hero",
        motion: "Slow push-in with liquid swirl",
        prompt:
          "Ultra-clean macro shot of a cobalt serum bottle with a glass pipette, cool daylight reflections, matte white surface, editorial beauty laboratory atmosphere.",
        continuityScore: 98,
        durationSec: 7,
        transitionMode: "crossfade",
        status: "approved",
        keyframeStatus: "Approved keyframe",
        notes: [
          "Keep the bottle centered for subtitle safety.",
          "Preserve matte surface reflections across frames.",
        ],
        palette: "Frosted cobalt / matte ivory",
        audioCue: "Music enters at full bed before narration ducks.",
        thumbnailLabel: "Glass + texture",
        gradient: "linear-gradient(145deg, #edf4ff 0%, #c9d8ff 40%, #fdfdff 100%)",
        subtitleStatus: "Timed",
      },
      {
        id: "scene_02",
        index: 2,
        title: "Ingredient proof stack",
        beat: "Validate the claim without feeling like a slide deck.",
        shotType: "Editorial tabletop",
        motion: "Parallax drift with ingredient callouts",
        prompt:
          "Premium lab tabletop with peptide molecules rendered as clean overlays, cool natural light, serum bottle and ingredient cards arranged with asymmetrical spacing.",
        continuityScore: 96,
        durationSec: 8,
        transitionMode: "crossfade",
        status: "approved",
        keyframeStatus: "Approved keyframe",
        notes: [
          "Hold the peptide callout for at least two subtitle beats.",
          "Maintain the cool tonal grade from scene one.",
        ],
        palette: "Pale steel / powder blue",
        audioCue: "Narration drives the beat, music ducks smoothly.",
        thumbnailLabel: "Ingredient deck",
        gradient: "linear-gradient(145deg, #f4f8ff 0%, #d7e2ff 48%, #f7fbff 100%)",
        subtitleStatus: "Timed",
      },
      {
        id: "scene_03",
        index: 3,
        title: "Mirror confidence pass",
        beat: "Show the day-fourteen payoff with restraint.",
        shotType: "Soft mirror portrait",
        motion: "Lateral drift with handheld softness",
        prompt:
          "Creator in cool daylight mirror shot, hydrated skin, clean editorial bathroom, premium but real, no glam sparkle, soft handheld motion.",
        continuityScore: 94,
        durationSec: 7,
        transitionMode: "crossfade",
        status: "running",
        keyframeStatus: "Pad render in progress",
        notes: [
          "Pad the end frame cleanly so the narration lands without a frozen facial expression.",
          "Avoid beauty-filter styling or warm highlights.",
        ],
        palette: "Cool porcelain / cloud blue",
        audioCue: "Ducking stays engaged until narration resolves.",
        thumbnailLabel: "Mirror motion",
        gradient: "linear-gradient(145deg, #eef5ff 0%, #cfdcff 46%, #ffffff 100%)",
        subtitleStatus: "Queued",
      },
      {
        id: "scene_04",
        index: 4,
        title: "Routine ease",
        beat: "Make consistency feel frictionless.",
        shotType: "Vanity overhead",
        motion: "Gentle top-down glide",
        prompt:
          "Overhead vanity scene with serum, towel, mirror, and hand motion, cool bright morning light, editorial spacing, premium household realism.",
        continuityScore: 97,
        durationSec: 6,
        transitionMode: "crossfade",
        status: "approved",
        keyframeStatus: "Approved keyframe",
        notes: [
          "Keep negative space open for caption treatment.",
          "Use the same towel texture established in scene two stills.",
        ],
        palette: "Fog white / soft cobalt",
        audioCue: "Bring music back up slightly in the pause after the line.",
        thumbnailLabel: "Routine topdown",
        gradient: "linear-gradient(145deg, #f7faff 0%, #dde8ff 42%, #ffffff 100%)",
        subtitleStatus: "Ready",
      },
      {
        id: "scene_05",
        index: 5,
        title: "CTA hero slate",
        beat: "Land the offer with polish and restraint.",
        shotType: "Front-facing product slate",
        motion: "Micro push with glow sweep",
        prompt:
          "Front-facing serum bottle on matte ivory plinth, soft glow sweep, strong negative space, editorial CTA typography zone, cool premium lighting.",
        continuityScore: 99,
        durationSec: 6,
        transitionMode: "crossfade",
        status: "approved",
        keyframeStatus: "Approved keyframe",
        notes: [
          "Ensure the CTA card remains readable after subtitle burn-in.",
          "Fade music into the final 1.5 second tail.",
        ],
        palette: "Ivory / cobalt edge light",
        audioCue: "Music tail sustains after narration finishes.",
        thumbnailLabel: "CTA slate",
        gradient: "linear-gradient(145deg, #ffffff 0%, #dbe6ff 44%, #f3f7ff 100%)",
        subtitleStatus: "Ready",
      },
    ],
    renderJobs: auroraRenderJobs,
    exports: auroraExports,
  },
  [opsProject.id]: {
    project: opsProject,
    brief: {
      objective:
        "Translate messy creator operations into a confident, premium B2B narrative with clear systems language and modern studio visuals.",
      hook: "Chaos becomes a repeatable machine in one visual move.",
      targetAudience:
        "Agency leads and in-house creator teams that need process credibility more than flashy visuals.",
      callToAction: "Book a workflow teardown.",
      brandNorthStar:
        "Operational editorial design: dense information, clean movement, and zero startup fluff.",
      guardrails: [
        "Avoid meme language or comedic pacing.",
        "Keep all diagrams readable in vertical mobile view.",
        "Use precise systems verbs instead of generic productivity claims.",
      ],
      mustInclude: [
        "Pipeline visual within scene one.",
        "Single-team dashboard motif across every scene.",
        "CTA on measurable throughput gains.",
      ],
      approvalSteps: [
        "Founder approves messaging accuracy.",
        "Ops lead signs off on dashboard metrics.",
        "Producer approves final pacing.",
      ],
    },
    script: {
      versionLabel: "v07 in review",
      approvalState: "Needs script approval",
      lastEdited: "Today, 9:08 AM",
      totalWords: 92,
      readingTimeLabel: "29s draft narration",
      lines: [
        {
          id: "ops_line_01",
          sceneId: "ops_scene_01",
          beat: "From chaos to pipeline",
          narration: "Most creator teams do not have a content problem, they have an operations visibility problem.",
          caption: "Your bottleneck is visibility.",
          durationSec: 7,
          status: "review",
          visualDirection: "UI dashboard fragments turning into one coherent board",
          voicePacing: "Firm and direct",
        },
        {
          id: "ops_line_02",
          sceneId: "ops_scene_02",
          beat: "System framing",
          narration: "Once briefs, scenes, and approvals live in one place, output stops depending on heroics.",
          caption: "Replace heroics with systems.",
          durationSec: 7,
          status: "review",
          visualDirection: "Card choreography, tidy queue metrics, no clutter",
          voicePacing: "Measured",
        },
        {
          id: "ops_line_03",
          sceneId: "ops_scene_03",
          beat: "Proof point",
          narration: "That is how one small team ships more content without creating more Slack noise or revision loops.",
          caption: "More content, less noise.",
          durationSec: 8,
          status: "review",
          visualDirection: "Single operator controlling multiple parallel renders",
          voicePacing: "Even and credible",
        },
        {
          id: "ops_line_04",
          sceneId: "ops_scene_04",
          beat: "CTA",
          narration: "If you want that operating model, book the teardown and we will map it to your production flow.",
          caption: "Book the teardown.",
          durationSec: 7,
          status: "review",
          visualDirection: "Dark-on-light editorial slate with concise CTA lockup",
          voicePacing: "Direct close",
        },
      ],
    },
    scenes: [
      {
        id: "ops_scene_01",
        index: 1,
        title: "Pipeline reveal",
        beat: "Anchor the idea in a visible workflow.",
        shotType: "Dashboard montage",
        motion: "Cards assembling into a system map",
        prompt:
          "Editorial UI dashboard fragments resolving into one production board, pale slate blues, premium no-border studio interface, layered depth.",
        continuityScore: 95,
        durationSec: 7,
        transitionMode: "hard_cut",
        status: "review",
        keyframeStatus: "Awaiting approval",
        notes: ["The board needs one bolder hierarchy move on the left rail."],
        palette: "Slate cyan / cloud",
        audioCue: "Minimal pulse with quick narration ducking.",
        thumbnailLabel: "Pipeline board",
        gradient: "linear-gradient(145deg, #eef6ff 0%, #d7e5ff 44%, #f8fbff 100%)",
        subtitleStatus: "Draft",
      },
      {
        id: "ops_scene_02",
        index: 2,
        title: "Brief to queue",
        beat: "Show the workflow becoming reliable.",
        shotType: "Operational split-screen",
        motion: "Horizontal sweep across task surfaces",
        prompt:
          "Vertical studio interface showing brief board, queue monitor, and approvals, no visible borders, matte surfaces, precise asymmetry.",
        continuityScore: 93,
        durationSec: 7,
        transitionMode: "hard_cut",
        status: "review",
        keyframeStatus: "Awaiting approval",
        notes: ["Tighten the hierarchy on the approvals panel."],
        palette: "Fog blue / graphite tint",
        audioCue: "Narration dominates, music stays understated.",
        thumbnailLabel: "Brief to queue",
        gradient: "linear-gradient(145deg, #f2f8ff 0%, #d6e3ff 40%, #ffffff 100%)",
        subtitleStatus: "Draft",
      },
      {
        id: "ops_scene_03",
        index: 3,
        title: "Throughput proof",
        beat: "Make scale feel effortless, not chaotic.",
        shotType: "Operator command view",
        motion: "Subtle zoom with animated queue activity",
        prompt:
          "Single operator in front of a polished production board, queue metrics and renders visible, calm high-end edit suite atmosphere.",
        continuityScore: 94,
        durationSec: 8,
        transitionMode: "hard_cut",
        status: "review",
        keyframeStatus: "Awaiting approval",
        notes: ["Add one more active render badge for scale."],
        palette: "Ink slate / pale cyan",
        audioCue: "Allow a short pause for the proof point line.",
        thumbnailLabel: "Throughput scene",
        gradient: "linear-gradient(145deg, #eef4ff 0%, #cfdcff 44%, #fcfdff 100%)",
        subtitleStatus: "Draft",
      },
      {
        id: "ops_scene_04",
        index: 4,
        title: "CTA board",
        beat: "Close with one elegant operating-system promise.",
        shotType: "Editorial CTA slate",
        motion: "Steady settle-in",
        prompt:
          "Minimal editorial CTA slate, operational data motifs, cool matte palette, clean typography zone for booking message.",
        continuityScore: 96,
        durationSec: 7,
        transitionMode: "hard_cut",
        status: "review",
        keyframeStatus: "Awaiting approval",
        notes: ["Keep the CTA large enough for mobile thumb speed."],
        palette: "Pale ice / graphite blue",
        audioCue: "Music ends on a clean accent, no tail needed.",
        thumbnailLabel: "CTA slate",
        gradient: "linear-gradient(145deg, #f7fbff 0%, #d9e5ff 44%, #f0f5ff 100%)",
        subtitleStatus: "Draft",
      },
    ],
    renderJobs: [
      {
        id: "render_ops_02",
        label: "Render 02 · Script review preview",
        status: "blocked",
        progress: 28,
        createdAt: "Today, 9:15 AM",
        updatedAt: "Today, 9:18 AM",
        durationSec: 29,
        transitionMode: "hard_cut",
        voicePreset: "Noah Systems",
        consistencyPackSnapshotId: "cps_ops_2026_03_21_v1",
        sseState: "Polling fallback active after repeated reconnect misses",
        nextAction: "Approve the keyframe pack to resume scene generation.",
        musicTrack: "Blueprint Pulse",
        allowExportWithoutMusic: true,
        checks: [
          {
            id: "ops_check_provenance",
            label: "Consistency pack provenance",
            status: "warning",
            detail: "The scene pack is ready, but the keyframe set is still pending approval.",
          },
          {
            id: "ops_check_duration",
            label: "Duration verification",
            status: "pass",
            detail: "Script timings stay within the current draft scene lengths.",
          },
          {
            id: "ops_check_stream",
            label: "Asset stream probe",
            status: "warning",
            detail: "Waiting on the first generated clip before stream validation can run.",
          },
          {
            id: "ops_check_music",
            label: "Music underlay continuity",
            status: "pass",
            detail: "Music is optional for this preview render, so the export can proceed without it.",
          },
        ],
        steps: [
          {
            id: "ops_step_01",
            sceneId: "ops_scene_01",
            name: "Keyframe approval gate",
            status: "blocked",
            durationDeltaSec: 0,
            clipStatus: "Waiting for approval",
            narrationStatus: "Draft narration ready",
            consistency: "Pack built",
            nextAction: "Approve keyframes",
          },
        ],
        events: [
          {
            id: "ops_event_01",
            time: "09:15:40",
            label: "Render created",
            detail: "The review preview render was queued with optional music fallback enabled.",
            tone: "primary",
          },
          {
            id: "ops_event_02",
            time: "09:16:02",
            label: "Approval gate engaged",
            detail: "Scene generation halted until the keyframe pack is approved.",
            tone: "warning",
          },
        ],
        metrics: {
          lufsTarget: "-14 LUFS planned",
          truePeak: "-1.0 dBTP planned",
          musicDucking: "-12 dB only if music is enabled",
          subtitleState: "Preview subtitle burn-in disabled",
        },
      },
    ],
    exports: [
      {
        id: "ops_export_storyboard",
        name: "Creator Ops Storyboard Reel",
        status: "processing",
        format: "Preview MP4",
        destination: "Internal review",
        durationSec: 29,
        sizeMb: 18.6,
        integratedLufs: -14,
        truePeak: -1,
        subtitles: false,
        musicBed: false,
        createdAt: "Today, 9:18 AM",
        gradient: "linear-gradient(145deg, #f4f8ff 0%, #d7e2ff 46%, #fcfdff 100%)",
        ratio: "9:16",
      },
    ],
  },
};

const allProjects: ProjectSummary[] = [auroraProject, opsProject, midnightProject];

const presetCards: PresetCard[] = [
  {
    id: "preset_visual_aurora",
    name: "Aurora Clinical Light",
    category: "visual",
    description: "Cool daylight beauty treatment with matte surfaces, asymmetrical still-life framing, and clean editorial depth.",
    tags: ["premium", "beauty", "cool"],
    status: "Active on 3 projects",
    transitionMode: "crossfade",
    look: "Frosted cobalt / matte ivory",
  },
  {
    id: "preset_voice_ava",
    name: "Ava Editorial",
    category: "voice",
    description: "Measured, premium narration tuned for calm authority and high subtitle readability.",
    tags: ["premium", "female", "steady"],
    status: "Default voice",
    voice: "stability 64 · pace 0.94x",
  },
  {
    id: "preset_music_glass",
    name: "Glass Current",
    category: "music",
    description: "Minimal electronic bed designed to duck smoothly under narration and sustain a polished tail.",
    tags: ["understated", "modern", "clean"],
    status: "Approved library",
  },
  {
    id: "preset_subtitle_clean",
    name: "Soft Caption Studio",
    category: "subtitle",
    description: "High-legibility subtitle system with compact rhythm and clean lower-third placement.",
    tags: ["subtitle", "accessibility", "clean"],
    status: "Approved library",
  },
];

const templateCards: TemplateCard[] = [
  {
    id: "template_launch",
    name: "Clinical Product Launch",
    description: "A five-scene launch arc for premium product drops with room for proof, ritual, and CTA.",
    duration: "30-35s",
    scenes: 5,
    style: "Editorial beauty",
  },
  {
    id: "template_explainer",
    name: "Operations Explainer",
    description: "A sharp system-oriented reel template designed for workflow clarity and measurable outcomes.",
    duration: "25-30s",
    scenes: 4,
    style: "Operational studio",
  },
  {
    id: "template_ugc",
    name: "Quiet UGC Ritual",
    description: "A softer six-scene format that uses consistent lighting and voice continuity to feel intimate.",
    duration: "35-45s",
    scenes: 6,
    style: "Warm ritual",
  },
];

const billingData: BillingData = {
  planName: "Pro Studio",
  cycleLabel: "Billing cycle renews on April 3, 2026",
  creditsRemaining: 1480,
  creditsTotal: 2500,
  projectedSpend: "$3,820 projected this cycle",
  usageBreakdown: [
    {
      category: "Video generation",
      usage: "118 clips",
      unitCost: "$0.48 avg / clip",
      total: "$56.64",
    },
    {
      category: "Image consistency",
      usage: "118 keyframes",
      unitCost: "$0.09 avg / image",
      total: "$10.62",
    },
    {
      category: "Narration + subtitles",
      usage: "31 exports",
      unitCost: "$0.34 avg / export",
      total: "$10.54",
    },
    {
      category: "Music generation",
      usage: "19 tracks",
      unitCost: "$0.22 avg / track",
      total: "$4.18",
    },
  ],
  invoices: [
    {
      id: "invoice_0315",
      label: "March platform usage",
      amount: "$1,980.00",
      date: "March 15, 2026",
      status: "Paid",
    },
    {
      id: "invoice_0301",
      label: "Platform subscription",
      amount: "$499.00",
      date: "March 1, 2026",
      status: "Paid",
    },
    {
      id: "invoice_0228",
      label: "Overage credits",
      amount: "$240.00",
      date: "February 28, 2026",
      status: "Pending review",
    },
  ],
};

const settingsSections: SettingsSection[] = [
  {
    title: "Workspace defaults",
    description: "Shared rules that keep projects aligned before any generation starts.",
    items: [
      { label: "Default export profile", value: "1080x1920 · H.264 · AAC" },
      { label: "Fallback transition mode", value: "Hard cut", status: "Project presets can override" },
      { label: "Default subtitle treatment", value: "Soft Caption Studio" },
    ],
  },
  {
    title: "Approvals and moderation",
    description: "Guardrails that stop the pipeline before expensive or risky outputs ship.",
    items: [
      { label: "Script approval requirement", value: "Required before render" },
      { label: "Keyframe review gate", value: "Enabled", status: "Phase 3 policy" },
      { label: "Moderation hold on failed outputs", value: "Enabled" },
    ],
  },
  {
    title: "Notification routing",
    description: "Where the studio team receives progress and incident updates.",
    items: [
      { label: "Render failure alerts", value: "Slack + email" },
      { label: "Export ready alerts", value: "In-app + email" },
      { label: "Billing threshold warning", value: "90% of budget" },
    ],
  },
];

const adminQueue: AdminQueueItem[] = [
  {
    id: "queue_018",
    workspace: "North Star Studio",
    project: "Aurora Serum Launch",
    step: "Scene 3 duration pad",
    status: "running",
    retries: 0,
    owner: "ffmpeg-compose",
    age: "2m",
    provider: "FFmpeg",
  },
  {
    id: "queue_019",
    workspace: "North Star Studio",
    project: "Creator Ops Playbook",
    step: "Keyframe approval gate",
    status: "blocked",
    retries: 0,
    owner: "approval-orchestrator",
    age: "33m",
    provider: "Internal",
  },
  {
    id: "queue_020",
    workspace: "Studio Tide",
    project: "Meal Prep Sprint",
    step: "Scene 5 video generation",
    status: "queued",
    retries: 1,
    owner: "video-runner",
    age: "5m",
    provider: "Kling",
  },
];

const adminWorkspaces: AdminWorkspaceRow[] = [
  {
    id: "workspace_north_star",
    name: "North Star Studio",
    plan: "Pro Studio",
    seats: 8,
    creditsRemaining: "1,480 / 2,500",
    renderLoad: "4 active",
    health: "Healthy",
    renewalDate: "April 3, 2026",
  },
  {
    id: "workspace_tide",
    name: "Studio Tide",
    plan: "Growth",
    seats: 5,
    creditsRemaining: "620 / 1,200",
    renderLoad: "7 active",
    health: "High load",
    renewalDate: "April 11, 2026",
  },
  {
    id: "workspace_fable",
    name: "Fable Systems",
    plan: "Enterprise",
    seats: 18,
    creditsRemaining: "8,940 / 12,000",
    renderLoad: "2 active",
    health: "Healthy",
    renewalDate: "April 28, 2026",
  },
];

const adminRenders: AdminRenderRow[] = [
  {
    id: "render_018",
    project: "Aurora Serum Launch",
    workspace: "North Star Studio",
    status: "running",
    provider: "FFmpeg + Kling",
    cost: "$3.82",
    stuckFor: "0m",
    issue: "Scene 3 duration pad",
    snapshot: "cps_aurora_2026_03_20_v4",
  },
  {
    id: "render_ops_02",
    project: "Creator Ops Playbook",
    workspace: "North Star Studio",
    status: "blocked",
    provider: "Internal",
    cost: "$0.42",
    stuckFor: "33m",
    issue: "Waiting on keyframe approval",
    snapshot: "cps_ops_2026_03_21_v1",
  },
  {
    id: "render_009",
    project: "Meal Prep Sprint",
    workspace: "Studio Tide",
    status: "failed",
    provider: "Runway",
    cost: "$5.11",
    stuckFor: "14m",
    issue: "asset_stream_corrupt on scene 5",
    snapshot: "cps_mealprep_2026_03_20_v2",
  },
];

async function withLatency<T>(value: T): Promise<T> {
  await mockDelay();
  return clone(value);
}

export async function getShellData(): Promise<ShellData> {
  return withLatency({
    user: currentUser,
    workspaces,
    projects: allProjects,
    alerts: shellAlerts,
  });
}

export async function getDashboardData(): Promise<DashboardData> {
  return withLatency({
    focusProject: auroraProject,
    metrics: [
      {
        label: "Active renders",
        value: "4",
        detail: "2 compositions, 2 scene retries",
        tone: "primary",
      },
      {
        label: "Approved scripts",
        value: "6",
        detail: "2 awaiting project-level review",
        tone: "success",
      },
      {
        label: "Credits remaining",
        value: "1,480",
        detail: "59% of monthly pool",
        tone: "neutral",
      },
      {
        label: "A/V consistency",
        value: "97.2",
        detail: "Average continuity score this week",
        tone: "success",
      },
    ],
    notifications: shellAlerts,
    queueOverview: [
      {
        label: "Queue health",
        value: "Stable",
        detail: "No provider outage right now",
        tone: "success",
      },
      {
        label: "SSE streams",
        value: "3 live",
        detail: "1 route on polling fallback",
        tone: "primary",
      },
      {
        label: "Exports ready",
        value: "2",
        detail: "Aurora master and teaser cutdown",
        tone: "success",
      },
    ],
    compositionRules: auroraRenderJobs[0].checks,
    recentProjects: allProjects,
  });
}

export async function getProjects(): Promise<ProjectSummary[]> {
  return withLatency(allProjects);
}

export async function getProjectBundle(projectId: string): Promise<ProjectBundle> {
  const bundle = projectBundles[projectId] ?? projectBundles[defaultProjectId];
  return withLatency(bundle);
}

export async function getPresets(): Promise<PresetCard[]> {
  return withLatency(presetCards);
}

export async function getTemplates(): Promise<TemplateCard[]> {
  return withLatency(templateCards);
}

export async function getBillingData(): Promise<BillingData> {
  return withLatency(billingData);
}

export async function getSettingsSections(): Promise<SettingsSection[]> {
  return withLatency(settingsSections);
}

export async function getAdminQueue(): Promise<AdminQueueItem[]> {
  return withLatency(adminQueue);
}

export async function getAdminWorkspaces(): Promise<AdminWorkspaceRow[]> {
  return withLatency(adminWorkspaces);
}

export async function getAdminRenders(): Promise<AdminRenderRow[]> {
  return withLatency(adminRenders);
}

export function getWorkspaceById(workspaceId: string): WorkspaceSummary {
  return workspaces.find((workspace) => workspace.id === workspaceId) ?? workspaces[0];
}

