import { useState, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { mockGetRenderPresets } from "../../lib/mock-service";
import type {
  RenderPreset,
  VideoEffectsProfile,
  ColorFilterType,
} from "../../types/domain";
import { DEFAULT_VIDEO_EFFECTS } from "../../types/domain";

interface RenderSettingsModalProps {
  onClose: () => void;
  onConfirm: (settings: {
    subtitleStyle: string;
    musicDucking: string;
    musicTrack: string;
    animationEffect: string;
    videoEffects?: VideoEffectsProfile;
    presetId?: string;
  }) => void;
  isStarting: boolean;
}

type ModalStep = "presets" | "customize";

const selectClass =
  "w-full rounded-xl border border-border-card bg-glass px-4 py-2.5 text-sm text-primary outline-none transition-all duration-200 focus:border-accent";

const tabBtnBase =
  "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border";

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
          {value}
          {unit ?? ""}
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

function PresetCard({
  preset,
  selected,
  onSelect,
}: {
  preset: RenderPreset;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`relative flex flex-col gap-2 rounded-xl border p-3 text-left transition-all duration-200 cursor-pointer ${
        selected
          ? "border-accent bg-primary-bg shadow-[0_0_0_2px_var(--accent-glow-sm)]"
          : "border-border-card bg-glass hover:border-border-active hover:bg-glass-hover"
      }`}
    >
      {preset.recommended && (
        <span className="absolute -top-2 right-2 rounded-full bg-accent-gradient px-2 py-0.5 text-[0.6rem] font-bold uppercase text-on-accent shadow-sm">
          Recommended
        </span>
      )}
      <div
        className="h-10 w-full rounded-lg"
        style={{ background: preset.gradient }}
      />
      <h4 className="text-sm font-bold text-primary leading-tight">
        {preset.name}
      </h4>
      <p className="text-[0.7rem] text-secondary leading-snug line-clamp-2">
        {preset.description}
      </p>
      <div className="flex flex-wrap gap-1 mt-auto">
        {preset.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="rounded-md bg-glass px-1.5 py-0.5 text-[0.6rem] font-medium text-muted"
          >
            {tag}
          </span>
        ))}
      </div>
    </button>
  );
}

export function RenderSettingsModal({
  onClose,
  onConfirm,
  isStarting,
}: RenderSettingsModalProps) {
  const [step, setStep] = useState<ModalStep>("presets");
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);

  const [subtitleStyle, setSubtitleStyle] = useState("none");
  const [musicDucking, setMusicDucking] = useState("0 dB");
  const [musicTrack, setMusicTrack] = useState("none");
  const [animationEffect, setAnimationEffect] = useState("ken_burns");
  const [effects, setEffects] = useState<VideoEffectsProfile>({
    ...DEFAULT_VIDEO_EFFECTS,
  });
  const [activeTab, setActiveTab] = useState<
    "animation" | "subtitles" | "music" | "effects"
  >("animation");

  const { data: presets } = useQuery({
    queryKey: ["render-presets"],
    queryFn: mockGetRenderPresets,
  });

  const selectedPreset = useMemo(
    () => presets?.find((p) => p.id === selectedPresetId) ?? null,
    [presets, selectedPresetId],
  );

  const applyPreset = useCallback(
    (preset: RenderPreset) => {
      setSelectedPresetId(preset.id);
      setAnimationEffect(preset.settings.animationEffect);
      setSubtitleStyle(preset.settings.subtitleStyle);
      setMusicTrack(preset.settings.musicTrack);
      setMusicDucking(preset.settings.musicDucking);
      setEffects({ ...preset.settings.videoEffects });
    },
    [],
  );

  const updateEffect = useCallback(
    <K extends keyof VideoEffectsProfile>(key: K, value: VideoEffectsProfile[K]) => {
      setEffects((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const colorFilters: { value: ColorFilterType; label: string }[] = [
    { value: "none", label: "None" },
    { value: "warm", label: "Warm" },
    { value: "cool", label: "Cool" },
    { value: "sepia", label: "Sepia" },
    { value: "grayscale", label: "B&W" },
    { value: "vintage", label: "Vintage" },
    { value: "vibrant", label: "Vibrant" },
    { value: "moody", label: "Moody" },
  ];

  if (step === "presets") {
    return (
      <div className="modal-backdrop">
        <div className="w-full max-w-2xl rounded-2xl border border-border-card bg-surface p-6 shadow-lg max-h-[85vh] overflow-y-auto">
          <div className="mb-5">
            <h2 className="font-heading text-lg font-bold text-primary">
              Choose a Render Preset
            </h2>
            <p className="mt-1 text-sm text-secondary">
              Select a starting configuration for your video. You can
              fine-tune every setting in the next step.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
            {(presets ?? []).map((preset) => (
              <PresetCard
                key={preset.id}
                preset={preset}
                selected={selectedPresetId === preset.id}
                onSelect={() => applyPreset(preset)}
              />
            ))}
          </div>

          <div className="flex justify-between items-center border-t border-border-subtle pt-4">
            <button
              className="text-xs font-semibold text-secondary hover:text-primary transition-colors"
              onClick={() => {
                setSelectedPresetId(null);
                setStep("customize");
              }}
              type="button"
            >
              Skip — start from scratch
            </button>
            <div className="flex gap-2">
              <button
                className="inline-flex items-center justify-center rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 hover:-translate-y-px hover:border-border-active hover:bg-glass-hover disabled:opacity-60"
                onClick={onClose}
                type="button"
              >
                Cancel
              </button>
              <button
                className="inline-flex items-center justify-center rounded-xl bg-accent-gradient px-4 py-2 text-sm font-semibold text-on-accent shadow-sm transition-all duration-200 hover:-translate-y-px hover:shadow-accent disabled:opacity-60"
                onClick={() => setStep("customize")}
                disabled={!selectedPresetId}
                type="button"
              >
                Customize Settings
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop">
      <div className="w-full max-w-lg rounded-2xl border border-border-card bg-surface p-6 shadow-lg max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-heading text-lg font-bold text-primary">
            Render Settings
          </h2>
          {selectedPreset && (
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.7rem] font-semibold border border-border-card bg-glass text-secondary">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: selectedPreset.gradient }}
              />
              {selectedPreset.name}
            </span>
          )}
        </div>
        <p className="text-sm text-secondary mb-4">
          Fine-tune animation, subtitles, music, and video effects before
          rendering.
        </p>

        {/* Tabs */}
        <div className="flex gap-1.5 mb-4 p-1 rounded-xl bg-glass border border-border-subtle">
          {(
            [
              ["animation", "Animation"],
              ["subtitles", "Subtitles"],
              ["music", "Music"],
              ["effects", "Effects"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={`${tabBtnBase} flex-1 ${
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
        <div className="flex flex-col gap-4 min-h-[200px]">
          {activeTab === "animation" && (
            <>
              <div className="form-field">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Animation Effect
                </label>
                <select
                  className={selectClass}
                  value={animationEffect}
                  onChange={(e) => setAnimationEffect(e.target.value)}
                >
                  <option value="ken_burns">Ken Burns (Zoom In + Out)</option>
                  <option value="zoom_in">Zoom In</option>
                  <option value="zoom_out">Zoom Out</option>
                  <option value="pan_left">Pan Left</option>
                  <option value="pan_right">Pan Right</option>
                </select>
              </div>
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
            </>
          )}

          {activeTab === "subtitles" && (
            <>
              <div className="form-field">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Subtitle Style
                </label>
                <select
                  className={selectClass}
                  value={subtitleStyle}
                  onChange={(e) => setSubtitleStyle(e.target.value)}
                >
                  <option value="none">No Subtitles</option>
                  <option value="Karaoke Bold">Karaoke Bold</option>
                  <option value="Minimalist White">Minimalist White</option>
                  <option value="Burned-in Default">Burned-in Default</option>
                </select>
              </div>
              {subtitleStyle !== "none" && (
                <div className="rounded-xl border border-border-subtle bg-glass/50 p-3">
                  <p className="text-[0.7rem] text-secondary leading-snug">
                    Subtitles will be burned into the video with the{" "}
                    <strong className="text-primary">{subtitleStyle}</strong>{" "}
                    style. Font, size, and placement use the project defaults
                    from your subtitle profile.
                  </p>
                </div>
              )}
            </>
          )}

          {activeTab === "music" && (
            <>
              <div className="form-field">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Background Music
                </label>
                <select
                  className={selectClass}
                  value={musicTrack}
                  onChange={(e) => {
                    const next = e.target.value;
                    setMusicTrack(next);
                    if (next === "none") {
                      setMusicDucking("0 dB");
                    } else if (musicTrack === "none") {
                      setMusicDucking("-12 dB");
                    }
                  }}
                >
                  <option value="none">No Background Music</option>
                  <option value="Ambient Corporate 1">
                    Ambient Corporate 1
                  </option>
                  <option value="Lo-fi Chill">Lo-fi Chill</option>
                  <option value="Upbeat Electronic">Upbeat Electronic</option>
                </select>
              </div>
              {musicTrack !== "none" && (
                <div className="form-field">
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Music Ducking
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
              )}
            </>
          )}

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
                label="Vignette"
                value={effects.vignetteStrength}
                min={0}
                max={100}
                step={1}
                onChange={(v) => updateEffect("vignetteStrength", v)}
              />
              <div className="form-field">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Color Filter
                </label>
                <div className="grid grid-cols-4 gap-1.5">
                  {colorFilters.map((f) => (
                    <button
                      key={f.value}
                      type="button"
                      onClick={() => updateEffect("colorFilter", f.value)}
                      className={`rounded-lg px-2 py-1.5 text-[0.7rem] font-semibold border transition-all duration-150 ${
                        effects.colorFilter === f.value
                          ? "border-accent bg-primary-bg text-primary shadow-sm"
                          : "border-border-subtle bg-glass text-secondary hover:border-border-active"
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>
              {(effects.brightness !== 0 ||
                effects.contrast !== 0 ||
                effects.saturation !== 0 ||
                effects.vignetteStrength !== 0 ||
                effects.colorFilter !== "none") && (
                <button
                  type="button"
                  className="self-start text-[0.7rem] font-semibold text-secondary hover:text-primary transition-colors"
                  onClick={() =>
                    setEffects({ ...DEFAULT_VIDEO_EFFECTS, speed: effects.speed, fadeInSec: effects.fadeInSec, fadeOutSec: effects.fadeOutSec })
                  }
                >
                  Reset effects to defaults
                </button>
              )}
            </>
          )}
        </div>

        {/* Actions */}
        <div className="mt-6 flex items-center justify-between border-t border-border-subtle pt-4">
          <button
            className="text-xs font-semibold text-secondary hover:text-primary transition-colors"
            onClick={() => setStep("presets")}
            type="button"
          >
            Back to presets
          </button>
          <div className="flex gap-2">
            <button
              className="inline-flex items-center justify-center rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 hover:-translate-y-px hover:border-border-active hover:bg-glass-hover disabled:opacity-60"
              onClick={onClose}
              disabled={isStarting}
              type="button"
            >
              Cancel
            </button>
            <button
              className="inline-flex items-center justify-center rounded-xl bg-accent-gradient px-4 py-2 text-sm font-semibold text-on-accent shadow-sm transition-all duration-200 hover:-translate-y-px hover:shadow-accent disabled:opacity-60"
              onClick={() =>
                onConfirm({
                  subtitleStyle,
                  musicDucking,
                  musicTrack,
                  animationEffect,
                  videoEffects: effects,
                  presetId: selectedPresetId ?? undefined,
                })
              }
              disabled={isStarting}
              type="button"
            >
              {isStarting ? "Starting..." : "Start Render"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
