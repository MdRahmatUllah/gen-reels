import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  PageFrame,
  SectionCard,
  StatusBadge,
  EmptyState,
  LoadingPage,
} from "../../components/ui";
import { useProject } from "../../hooks/use-projects";
import { useRenders, useStartRender } from "../../hooks/use-renders";
import { mockGetScenePlan, mockGetRenderPresets } from "../../lib/mock-service";
import { isMockMode } from "../../lib/config";
import { liveGetScenePlan } from "../../lib/live-api";
import type {
  RenderJob,
  ScenePlan,
  ScenePlanSet,
  VideoEffectsProfile,
  ColorFilterType,
  RenderPreset,
} from "../../types/domain";
import { DEFAULT_VIDEO_EFFECTS } from "../../types/domain";

/* ─── Helpers ────────────────────────────────────────────────────────────── */

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

function buildCssFilter(effects: VideoEffectsProfile): string {
  const filters: string[] = [];
  if (effects.brightness !== 0)
    filters.push(`brightness(${1 + effects.brightness / 100})`);
  if (effects.contrast !== 0)
    filters.push(`contrast(${1 + effects.contrast / 100})`);
  if (effects.saturation !== 0)
    filters.push(`saturate(${1 + effects.saturation / 50})`);
  if (effects.colorFilter === "sepia") filters.push("sepia(0.8)");
  if (effects.colorFilter === "grayscale") filters.push("grayscale(1)");
  if (effects.colorFilter === "warm")
    filters.push("sepia(0.2) saturate(1.2)");
  if (effects.colorFilter === "cool")
    filters.push("hue-rotate(20deg) saturate(0.9)");
  if (effects.colorFilter === "vintage")
    filters.push("sepia(0.4) contrast(1.1) brightness(0.95)");
  if (effects.colorFilter === "vibrant")
    filters.push("saturate(1.5) contrast(1.05)");
  if (effects.colorFilter === "moody")
    filters.push("saturate(0.7) contrast(1.15) brightness(0.9)");
  return filters.join(" ") || "none";
}

function hasActiveEffects(effects: VideoEffectsProfile): boolean {
  return (
    effects.brightness !== 0 ||
    effects.contrast !== 0 ||
    effects.saturation !== 0 ||
    effects.vignetteStrength !== 0 ||
    effects.colorFilter !== "none" ||
    effects.speed !== 1 ||
    effects.fadeInSec !== 0 ||
    effects.fadeOutSec !== 0
  );
}

/* ─── Range Slider ───────────────────────────────────────────────────────── */

function RangeSlider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-muted">
          {label}
        </span>
        <span className="text-xs font-semibold text-primary tabular-nums">
          {value}{unit ?? ""}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[var(--accent)] h-1.5 rounded-full appearance-none bg-border-subtle cursor-pointer"
      />
    </div>
  );
}

/* ─── Toggle ─────────────────────────────────────────────────────────────── */

function Toggle({
  label,
  enabled,
  onToggle,
}: {
  label: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className="flex items-center justify-between w-full py-2"
      onClick={onToggle}
    >
      <span className="text-sm font-semibold text-primary">{label}</span>
      <div
        className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
          enabled ? "bg-accent" : "bg-border-subtle"
        }`}
      >
        <div
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
            enabled ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </div>
    </button>
  );
}

/* ─── Active Effects Pill Bar ────────────────────────────────────────────── */

function ActiveEffectsPills({ effects }: { effects: VideoEffectsProfile }) {
  const pills: string[] = [];
  if (effects.brightness !== 0) pills.push(`Brightness ${effects.brightness > 0 ? "+" : ""}${effects.brightness}`);
  if (effects.contrast !== 0) pills.push(`Contrast ${effects.contrast > 0 ? "+" : ""}${effects.contrast}`);
  if (effects.saturation !== 0) pills.push(`Saturation ${effects.saturation > 0 ? "+" : ""}${effects.saturation}`);
  if (effects.colorFilter !== "none") pills.push(effects.colorFilter.charAt(0).toUpperCase() + effects.colorFilter.slice(1));
  if (effects.vignetteStrength > 0) pills.push(`Vignette ${effects.vignetteStrength}%`);
  if (effects.speed !== 1) pills.push(`Speed ${effects.speed}x`);
  if (effects.fadeInSec > 0) pills.push(`Fade in ${effects.fadeInSec}s`);
  if (effects.fadeOutSec > 0) pills.push(`Fade out ${effects.fadeOutSec}s`);

  if (pills.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {pills.map((p) => (
        <span key={p} className="rounded-full bg-accent/15 border border-accent/30 px-2 py-0.5 text-[0.65rem] font-semibold text-accent-bright">
          {p}
        </span>
      ))}
    </div>
  );
}

/* ─── Scene Timeline Strip ───────────────────────────────────────────────── */

function SceneTimeline({
  scenes,
  activeIndex,
  onSelect,
  filterCss,
}: {
  scenes: ScenePlan[];
  activeIndex: number;
  onSelect: (i: number) => void;
  filterCss: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const active = el.children[activeIndex] as HTMLElement | undefined;
    active?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [activeIndex]);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-[0.7rem] font-bold uppercase tracking-wider text-muted">
          Scene Timeline
        </h3>
        <span className="text-[0.65rem] text-secondary">
          {scenes.length} scenes · {formatTime(scenes.reduce((s, sc) => s + sc.durationSec, 0))} total
        </span>
      </div>
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto pb-2 no-scrollbar"
      >
        {scenes.map((scene, i) => (
          <button
            key={scene.id}
            type="button"
            onClick={() => onSelect(i)}
            className={`flex-shrink-0 flex flex-col gap-1 rounded-lg border p-2 w-28 transition-all duration-200 cursor-pointer text-left ${
              i === activeIndex
                ? "border-accent bg-primary-bg shadow-sm"
                : "border-border-subtle bg-glass hover:border-border-active"
            }`}
          >
            <div
              className="h-14 w-full rounded-md transition-[filter] duration-300"
              style={{ background: scene.gradient, filter: filterCss }}
            />
            <span className="text-[0.6rem] font-bold uppercase tracking-wider text-muted">
              Scene {scene.index + 1}
            </span>
            <span className="text-[0.7rem] font-semibold text-primary leading-tight line-clamp-1">
              {scene.title}
            </span>
            <span className="text-[0.6rem] text-secondary">
              {scene.durationSec}s
            </span>
          </button>
        ))}
      </div>

      {/* Timeline bar */}
      <div className="relative h-2 w-full rounded-full bg-border-subtle overflow-hidden">
        {scenes.map((scene, i) => {
          const total = scenes.reduce((s, sc) => s + sc.durationSec, 0);
          const before = scenes.slice(0, i).reduce((s, sc) => s + sc.durationSec, 0);
          const pct = (scene.durationSec / total) * 100;
          const left = (before / total) * 100;
          return (
            <div
              key={scene.id}
              className={`absolute top-0 h-full transition-colors duration-200 ${
                i === activeIndex ? "bg-accent" : "bg-accent/30"
              }`}
              style={{ left: `${left}%`, width: `${pct}%` }}
            />
          );
        })}
      </div>
    </div>
  );
}

/* ─── Video Preview ──────────────────────────────────────────────────────── */

function VideoPreview({
  exportUrl,
  scenes,
  activeScene,
  effects,
  subtitleEnabled,
  subtitleStyle,
  subtitlePosition,
  musicEnabled,
  musicTrack,
}: {
  exportUrl: string | null;
  scenes: ScenePlan[];
  activeScene: ScenePlan | null;
  effects: VideoEffectsProfile;
  subtitleEnabled: boolean;
  subtitleStyle: string;
  subtitlePosition: "top" | "center" | "bottom";
  musicEnabled: boolean;
  musicTrack: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const filterCss = useMemo(() => buildCssFilter(effects), [effects]);
  const effectsActive = hasActiveEffects(effects);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  }, []);

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Number(e.target.value);
  }, []);

  const subtitlePosClass =
    subtitlePosition === "top" ? "top-4" : subtitlePosition === "center" ? "top-1/2 -translate-y-1/2" : "bottom-4";

  const previewContainer = (
    content: React.ReactNode,
    showControls: boolean,
  ) => (
    <div className="flex flex-col gap-3">
      {/* Effects active indicator */}
      {effectsActive && <ActiveEffectsPills effects={effects} />}

      <div className="relative rounded-xl overflow-hidden border border-border-card bg-black" style={{ maxHeight: "480px" }}>
        {content}

        {/* Vignette overlay */}
        {effects.vignetteStrength > 0 && (
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: `radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,${effects.vignetteStrength / 100}) 100%)`,
            }}
          />
        )}

        {/* Subtitle preview overlay */}
        {subtitleEnabled && (
          <div className={`absolute left-0 right-0 ${subtitlePosClass} flex justify-center pointer-events-none px-4`}>
            <div className={`rounded-lg px-4 py-2 max-w-[85%] text-center ${
              subtitleStyle === "Karaoke Bold"
                ? "bg-black/70 text-white text-base font-bold"
                : subtitleStyle === "Minimalist White"
                  ? "text-white text-sm font-medium drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]"
                  : "bg-black/50 text-yellow-100 text-sm font-semibold"
            }`}>
              {activeScene?.narration
                ? activeScene.narration.split(" ").slice(0, 8).join(" ") + "..."
                : "Sample subtitle text preview"}
            </div>
          </div>
        )}

        {/* Music indicator overlay */}
        {musicEnabled && (
          <div className="absolute top-3 right-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 pointer-events-none">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
            </svg>
            <span className="text-[0.6rem] font-semibold text-white/80">{musicTrack}</span>
          </div>
        )}
      </div>

      {/* Playback Controls */}
      {showControls && (
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={togglePlay}
            className="flex items-center justify-center w-9 h-9 rounded-full bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent transition-all"
          >
            {isPlaying ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg>
            )}
          </button>
          <span className="text-xs text-secondary tabular-nums w-12">
            {formatTime(currentTime)}
          </span>
          <input
            type="range"
            min={0}
            max={duration || 1}
            step={0.01}
            value={currentTime}
            onChange={handleSeek}
            className="flex-1 accent-[var(--accent)] h-1.5 rounded-full appearance-none bg-border-subtle cursor-pointer"
          />
          <span className="text-xs text-secondary tabular-nums w-12 text-right">
            {formatTime(duration)}
          </span>
        </div>
      )}
    </div>
  );

  /* ─── Has video ─── */
  if (exportUrl) {
    return previewContainer(
      <video
        ref={videoRef}
        src={exportUrl}
        playsInline
        onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime ?? 0)}
        onLoadedMetadata={() => setDuration(videoRef.current?.duration ?? 0)}
        onEnded={() => setIsPlaying(false)}
        className="w-full block transition-[filter] duration-300"
        style={{ filter: filterCss, maxHeight: "480px" }}
      />,
      true,
    );
  }

  /* ─── No video — show scene-based preview with effects ─── */
  return previewContainer(
    <div
      className="relative flex items-center justify-center transition-[filter] duration-300"
      style={{ aspectRatio: "9/16", maxHeight: "480px", filter: filterCss }}
    >
      {/* Scene gradient background */}
      <div
        className="absolute inset-0"
        style={{ background: activeScene?.gradient ?? "linear-gradient(135deg, #1a1a2e, #16213e)" }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30" />

      {/* Scene info */}
      <div className="relative z-10 flex flex-col items-center gap-3 text-center p-6">
        {activeScene ? (
          <>
            <span className="text-white/50 text-[0.65rem] font-bold uppercase tracking-widest">
              Scene {activeScene.index + 1} Preview
            </span>
            <h3 className="text-white text-lg font-bold leading-tight">
              {activeScene.title}
            </h3>
            <p className="text-white/60 text-xs max-w-[80%] leading-relaxed">
              {activeScene.beat}
            </p>
            <span className="text-white/40 text-[0.65rem] mt-2">
              {activeScene.durationSec}s · {activeScene.shotType}
            </span>
          </>
        ) : (
          <>
            <p className="text-white/60 text-sm font-semibold">Effects Preview</p>
            <p className="text-white/40 text-xs mt-1">
              Adjust effects to see a live preview. Render from the Renders tab first for a video preview.
            </p>
          </>
        )}
      </div>
    </div>,
    false,
  );
}

/* ─── Editor Tabs ────────────────────────────────────────────────────────── */

type EditorTab = "subtitles" | "music" | "effects" | "presets";

const colorFilters: { value: ColorFilterType; label: string; preview: string }[] = [
  { value: "none", label: "None", preview: "bg-gradient-to-br from-gray-200 to-gray-400" },
  { value: "warm", label: "Warm", preview: "bg-gradient-to-br from-orange-200 to-amber-400" },
  { value: "cool", label: "Cool", preview: "bg-gradient-to-br from-blue-200 to-cyan-400" },
  { value: "sepia", label: "Sepia", preview: "bg-gradient-to-br from-yellow-200 to-amber-600" },
  { value: "grayscale", label: "B&W", preview: "bg-gradient-to-br from-gray-300 to-gray-600" },
  { value: "vintage", label: "Vintage", preview: "bg-gradient-to-br from-amber-200 to-rose-400" },
  { value: "vibrant", label: "Vibrant", preview: "bg-gradient-to-br from-pink-300 to-violet-500" },
  { value: "moody", label: "Moody", preview: "bg-gradient-to-br from-slate-400 to-indigo-700" },
];

/* ─── Main Editor Page ───────────────────────────────────────────────────── */

export function VideoEditorPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: project, isLoading: projectLoading } = useProject(projectId || "");
  const { data: renders } = useRenders(project?.id || "");
  const { data: planSet } = useQuery<ScenePlanSet | null>({
    queryKey: ["scenePlan", projectId],
    queryFn: () =>
      isMockMode()
        ? mockGetScenePlan(projectId!)
        : liveGetScenePlan(projectId!),
    enabled: !!projectId,
  });
  const { data: renderPresets } = useQuery({
    queryKey: ["render-presets"],
    queryFn: mockGetRenderPresets,
  });

  const { mutateAsync: startRender, isPending: isStarting } = useStartRender(project?.id || "");

  const [activeTab, setActiveTab] = useState<EditorTab>("effects");
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);

  /* ─── Editor State ─── */
  const [subtitleEnabled, setSubtitleEnabled] = useState(false);
  const [subtitleStyle, setSubtitleStyle] = useState("Karaoke Bold");
  const [subtitlePosition, setSubtitlePosition] = useState<"top" | "center" | "bottom">("bottom");

  const [musicEnabled, setMusicEnabled] = useState(false);
  const [musicTrack, setMusicTrack] = useState("Ambient Corporate 1");
  const [musicVolume, setMusicVolume] = useState(70);
  const [musicDucking, setMusicDucking] = useState("-12 dB");

  const [effects, setEffects] = useState<VideoEffectsProfile>({ ...DEFAULT_VIDEO_EFFECTS });

  const updateEffect = useCallback(
    <K extends keyof VideoEffectsProfile>(key: K, val: VideoEffectsProfile[K]) => {
      setEffects((prev) => ({ ...prev, [key]: val }));
    },
    [],
  );

  const applyPreset = useCallback((preset: RenderPreset) => {
    setSubtitleEnabled(preset.settings.subtitleStyle !== "none");
    setSubtitleStyle(preset.settings.subtitleStyle === "none" ? "Karaoke Bold" : preset.settings.subtitleStyle);
    setMusicEnabled(preset.settings.musicTrack !== "none");
    setMusicTrack(preset.settings.musicTrack === "none" ? "Ambient Corporate 1" : preset.settings.musicTrack);
    setMusicDucking(preset.settings.musicDucking);
    setEffects({ ...preset.settings.videoEffects });
  }, []);

  const completedRender = useMemo<RenderJob | null>(() => {
    if (!renders?.length) return null;
    const sorted = [...renders].sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
    return sorted.find((r) => r.status === "completed" && r.exportUrl) ?? null;
  }, [renders]);

  const latestRender = renders?.length
    ? [...renders].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0]
    : null;

  useEffect(() => {
    if (!latestRender) return;

    if (latestRender.videoEffects) {
      setEffects((prev) => {
        const ve = latestRender.videoEffects!;
        if (JSON.stringify(prev) === JSON.stringify(ve)) return prev;
        return { ...ve };
      });
    }

    const hasSubs = latestRender.metrics.subtitleState === "Burned";
    setSubtitleEnabled(hasSubs);
    if (hasSubs && latestRender.metrics.subtitleStyle && latestRender.metrics.subtitleStyle !== "Off") {
      setSubtitleStyle(latestRender.metrics.subtitleStyle);
    }

    const hasMusic = latestRender.musicTrack !== "none";
    setMusicEnabled(hasMusic);
    if (hasMusic) {
      setMusicTrack(latestRender.musicTrack);
    }
    if (latestRender.metrics.musicDucking && latestRender.metrics.musicDucking !== "Off") {
      setMusicDucking(latestRender.metrics.musicDucking);
    }
  }, [latestRender]);

  const scenes = planSet?.scenes ?? [];
  const activeScene = scenes[activeSceneIndex] ?? null;
  const filterCss = useMemo(() => buildCssFilter(effects), [effects]);

  const handleApplyAndRerender = useCallback(async () => {
    if (!project?.id) return;
    try {
      await startRender({
        subtitleStyle: subtitleEnabled ? subtitleStyle : "none",
        musicDucking: musicEnabled ? musicDucking : "0 dB",
        musicTrack: musicEnabled ? musicTrack : "none",
        animationEffect: "ken_burns",
        videoEffects: effects,
      });
      queryClient.invalidateQueries({ queryKey: ["renders", project.id] });
      navigate(`/app/projects/${project.id}/renders`);
    } catch {
      // mutation error handled by react-query
    }
  }, [project?.id, subtitleEnabled, subtitleStyle, musicEnabled, musicDucking, musicTrack, effects, startRender, queryClient, navigate]);

  if (projectLoading || !project) {
    return <LoadingPage />;
  }

  const selectClass =
    "w-full rounded-xl border border-border-card bg-glass px-4 py-2.5 text-sm text-primary outline-none transition-all duration-200 focus:border-accent";

  const tabBtnBase =
    "px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 border flex-1 text-center";

  return (
    <PageFrame
      eyebrow="Video editor"
      title={`Edit ${project.title}`}
      description="Fine-tune your video with subtitles, background music, and visual effects before final export."
      actions={
        <div className="flex items-center gap-2">
          <Link
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
            to={`/app/projects/${project.id}/renders`}
          >
            Back to renders
          </Link>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px disabled:opacity-50"
            onClick={handleApplyAndRerender}
            disabled={isStarting}
          >
            {isStarting ? "Starting render..." : "Apply & Re-render"}
          </button>
        </div>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Current settings">
            <div className="inspector-list">
              <div>
                <span>Subtitles</span>
                <strong>{subtitleEnabled ? subtitleStyle : "Off"}</strong>
              </div>
              {subtitleEnabled && (
                <div>
                  <span>Position</span>
                  <strong className="capitalize">{subtitlePosition}</strong>
                </div>
              )}
              <div>
                <span>Music</span>
                <strong>{musicEnabled ? musicTrack : "Off"}</strong>
              </div>
              {musicEnabled && (
                <div>
                  <span>Volume</span>
                  <strong>{musicVolume}%</strong>
                </div>
              )}
              <div>
                <span>Brightness</span>
                <strong>{effects.brightness}</strong>
              </div>
              <div>
                <span>Contrast</span>
                <strong>{effects.contrast}</strong>
              </div>
              <div>
                <span>Saturation</span>
                <strong>{effects.saturation}</strong>
              </div>
              <div>
                <span>Color filter</span>
                <strong className="capitalize">{effects.colorFilter}</strong>
              </div>
              <div>
                <span>Speed</span>
                <strong>{effects.speed}x</strong>
              </div>
              <div>
                <span>Vignette</span>
                <strong>{effects.vignetteStrength}%</strong>
              </div>
            </div>
          </SectionCard>

          {activeScene && (
            <SectionCard title={`Scene ${activeScene.index + 1}`}>
              <div className="inspector-list">
                <div>
                  <span>Title</span>
                  <strong>{activeScene.title}</strong>
                </div>
                <div>
                  <span>Duration</span>
                  <strong>{activeScene.durationSec}s</strong>
                </div>
                <div>
                  <span>Shot</span>
                  <strong>{activeScene.shotType}</strong>
                </div>
                <div>
                  <span>Motion</span>
                  <strong>{activeScene.motion}</strong>
                </div>
                <div>
                  <span>Status</span>
                  <StatusBadge status={activeScene.status} />
                </div>
              </div>
            </SectionCard>
          )}

          {completedRender && (
            <SectionCard title="Export">
              <div className="flex flex-col gap-2">
                {completedRender.exportUrl && (
                  <a
                    href={completedRender.exportUrl}
                    download="export.mp4"
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent-gradient px-4 py-2 text-sm font-semibold text-on-accent shadow-sm hover:shadow-accent transition-all"
                  >
                    Download MP4
                  </a>
                )}
                <Link
                  to={`/app/projects/${project.id}/exports`}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary hover:border-border-active hover:bg-glass-hover transition-all"
                >
                  View exports
                </Link>
              </div>
            </SectionCard>
          )}
        </div>
      }
    >
      {/* Video Preview */}
      <SectionCard title="Preview" subtitle="Live preview of your effect settings — adjustments update in real time">
        <VideoPreview
          exportUrl={completedRender?.exportUrl ?? null}
          scenes={scenes}
          activeScene={activeScene}
          effects={effects}
          subtitleEnabled={subtitleEnabled}
          subtitleStyle={subtitleStyle}
          subtitlePosition={subtitlePosition}
          musicEnabled={musicEnabled}
          musicTrack={musicTrack}
        />
      </SectionCard>

      {/* Scene Timeline */}
      {scenes.length > 0 && (
        <SectionCard title="Timeline" subtitle="Select a scene to view its details and see the effect preview">
          <SceneTimeline
            scenes={scenes}
            activeIndex={activeSceneIndex}
            onSelect={setActiveSceneIndex}
            filterCss={filterCss}
          />
        </SectionCard>
      )}

      {/* Editor Controls */}
      <SectionCard title="Editor controls" subtitle="Adjust subtitles, music, visual effects, or apply a preset — changes preview instantly above">
        {/* Tab bar */}
        <div className="flex gap-1.5 p-1 rounded-xl bg-glass border border-border-subtle">
          {(
            [
              ["effects", "Effects"],
              ["subtitles", "Subtitles"],
              ["music", "Music"],
              ["presets", "Presets"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={`${tabBtnBase} ${
                activeTab === key
                  ? "bg-accent-gradient text-on-accent border-transparent shadow-sm"
                  : "bg-transparent text-secondary border-transparent hover:text-primary hover:bg-glass-hover"
              }`}
              onClick={() => setActiveTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex flex-col gap-4 mt-2">
          {/* ── Effects Tab ── */}
          {activeTab === "effects" && (
            <>
              <RangeSlider
                label="Brightness"
                value={effects.brightness}
                min={-50}
                max={50}
                step={1}
                onChange={(v) => updateEffect("brightness", v)}
              />
              <RangeSlider
                label="Contrast"
                value={effects.contrast}
                min={-50}
                max={50}
                step={1}
                onChange={(v) => updateEffect("contrast", v)}
              />
              <RangeSlider
                label="Saturation"
                value={effects.saturation}
                min={-50}
                max={50}
                step={1}
                onChange={(v) => updateEffect("saturation", v)}
              />
              <RangeSlider
                label="Speed"
                value={effects.speed}
                min={0.25}
                max={2}
                step={0.05}
                unit="x"
                onChange={(v) => updateEffect("speed", v)}
              />
              <RangeSlider
                label="Vignette"
                value={effects.vignetteStrength}
                min={0}
                max={100}
                step={1}
                unit="%"
                onChange={(v) => updateEffect("vignetteStrength", v)}
              />
              <RangeSlider
                label="Fade In"
                value={effects.fadeInSec}
                min={0}
                max={3}
                step={0.1}
                unit="s"
                onChange={(v) => updateEffect("fadeInSec", v)}
              />
              <RangeSlider
                label="Fade Out"
                value={effects.fadeOutSec}
                min={0}
                max={3}
                step={0.1}
                unit="s"
                onChange={(v) => updateEffect("fadeOutSec", v)}
              />

              {/* Color Filters */}
              <div className="form-field">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Color Filter
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {colorFilters.map((f) => (
                    <button
                      key={f.value}
                      type="button"
                      onClick={() => updateEffect("colorFilter", f.value)}
                      className={`flex flex-col items-center gap-1.5 rounded-lg border p-2 transition-all duration-150 ${
                        effects.colorFilter === f.value
                          ? "border-accent bg-primary-bg shadow-sm"
                          : "border-border-subtle bg-glass hover:border-border-active"
                      }`}
                    >
                      <div className={`h-8 w-full rounded-md ${f.preview}`} />
                      <span className="text-[0.65rem] font-semibold text-primary">
                        {f.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Reset */}
              {hasActiveEffects(effects) && (
                <button
                  type="button"
                  className="self-start text-[0.7rem] font-semibold text-secondary hover:text-primary transition-colors"
                  onClick={() => setEffects({ ...DEFAULT_VIDEO_EFFECTS })}
                >
                  Reset all effects
                </button>
              )}
            </>
          )}

          {/* ── Subtitles Tab ── */}
          {activeTab === "subtitles" && (
            <>
              <Toggle
                label="Enable subtitles"
                enabled={subtitleEnabled}
                onToggle={() => setSubtitleEnabled((p) => !p)}
              />
              {subtitleEnabled && (
                <>
                  <div className="form-field">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Style
                    </label>
                    <select
                      className={selectClass}
                      value={subtitleStyle}
                      onChange={(e) => setSubtitleStyle(e.target.value)}
                    >
                      <option value="Karaoke Bold">Karaoke Bold</option>
                      <option value="Minimalist White">Minimalist White</option>
                      <option value="Burned-in Default">Burned-in Default</option>
                    </select>
                  </div>
                  <div className="form-field">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Position
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {(["top", "center", "bottom"] as const).map((pos) => (
                        <button
                          key={pos}
                          type="button"
                          className={`rounded-lg px-3 py-2 text-xs font-semibold border capitalize transition-all duration-150 ${
                            subtitlePosition === pos
                              ? "border-accent bg-primary-bg text-primary"
                              : "border-border-subtle bg-glass text-secondary hover:border-border-active"
                          }`}
                          onClick={() => setSubtitlePosition(pos)}
                        >
                          {pos}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* ── Music Tab ── */}
          {activeTab === "music" && (
            <>
              <Toggle
                label="Enable background music"
                enabled={musicEnabled}
                onToggle={() => setMusicEnabled((p) => !p)}
              />
              {musicEnabled && (
                <>
                  <div className="form-field">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Track
                    </label>
                    <select
                      className={selectClass}
                      value={musicTrack}
                      onChange={(e) => setMusicTrack(e.target.value)}
                    >
                      <option value="Ambient Corporate 1">Ambient Corporate 1</option>
                      <option value="Lo-fi Chill">Lo-fi Chill</option>
                      <option value="Upbeat Electronic">Upbeat Electronic</option>
                    </select>
                  </div>
                  <RangeSlider
                    label="Volume"
                    value={musicVolume}
                    min={0}
                    max={100}
                    step={1}
                    unit="%"
                    onChange={setMusicVolume}
                  />
                  <div className="form-field">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Ducking
                    </label>
                    <select
                      className={selectClass}
                      value={musicDucking}
                      onChange={(e) => setMusicDucking(e.target.value)}
                    >
                      <option value="-6 dB">-6 dB (Loud)</option>
                      <option value="-12 dB">-12 dB (Balanced)</option>
                      <option value="-18 dB">-18 dB (Quiet)</option>
                    </select>
                  </div>
                </>
              )}
            </>
          )}

          {/* ── Presets Tab ── */}
          {activeTab === "presets" && (
            <>
              <p className="text-sm text-secondary">
                Apply a preset to instantly configure all settings — preview updates live above.
              </p>
              <div className="grid grid-cols-2 gap-3">
                {(renderPresets ?? []).map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => applyPreset(preset)}
                    className="flex flex-col gap-2 rounded-xl border border-border-card bg-glass p-3 text-left transition-all duration-200 hover:border-border-active hover:bg-glass-hover cursor-pointer group"
                  >
                    <div
                      className="h-10 w-full rounded-lg transition-transform duration-200 group-hover:scale-[1.02]"
                      style={{ background: preset.gradient }}
                    />
                    <h4 className="text-sm font-bold text-primary">
                      {preset.name}
                    </h4>
                    <p className="text-[0.7rem] text-secondary leading-snug line-clamp-2">
                      {preset.description}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {preset.tags.slice(0, 3).map((t) => (
                        <span
                          key={t}
                          className="rounded-md bg-glass px-1.5 py-0.5 text-[0.6rem] font-medium text-muted"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </SectionCard>
    </PageFrame>
  );
}
