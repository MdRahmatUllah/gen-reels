import { useState } from "react";

interface RenderSettingsModalProps {
  onClose: () => void;
  onConfirm: (settings: {
    subtitleStyle: string;
    musicDucking: string;
    musicTrack: string;
  }) => void;
  isStarting: boolean;
}

const selectClassName =
  "w-full rounded-xl border border-border-card bg-glass px-4 py-2.5 text-sm text-primary outline-none transition-all duration-200 focus:border-accent";

export function RenderSettingsModal({
  onClose,
  onConfirm,
  isStarting,
}: RenderSettingsModalProps) {
  const [subtitleStyle, setSubtitleStyle] = useState("Karaoke Bold");
  const [musicDucking, setMusicDucking] = useState("-12 dB");
  const [musicTrack, setMusicTrack] = useState("Ambient Corporate 1");

  return (
    <div className="modal-backdrop">
      <div className="w-full max-w-md rounded-2xl border border-border-card bg-surface p-6 shadow-lg">
        <div>
          <h2 className="font-heading text-lg font-bold text-primary">Generate Video</h2>
          <p className="mt-1 text-sm text-secondary">
            Animates your scene keyframes with Ken Burns motion, adds voiceover and captions,
            then exports the final MP4.
          </p>
        </div>

        <div className="mt-5 flex flex-col gap-4">
          <div className="form-field">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted">
              Subtitle Style
            </label>
            <select
              className={selectClassName}
              value={subtitleStyle}
              onChange={(event) => setSubtitleStyle(event.target.value)}
            >
              <option value="Karaoke Bold">Karaoke Bold</option>
              <option value="Minimalist White">Minimalist White</option>
              <option value="Burned-in Default">Burned-in Default</option>
            </select>
          </div>

          <div className="form-field">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted">
              Music Track
            </label>
            <select
              className={selectClassName}
              value={musicTrack}
              onChange={(event) => setMusicTrack(event.target.value)}
            >
              <option value="Ambient Corporate 1">Ambient Corporate 1</option>
              <option value="Lo-fi Chill">Lo-fi Chill</option>
              <option value="Upbeat Electronic">Upbeat Electronic</option>
            </select>
          </div>

          <div className="form-field">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted">
              Music Ducking
            </label>
            <select
              className={selectClassName}
              value={musicDucking}
              onChange={(event) => setMusicDucking(event.target.value)}
            >
              <option value="-6 dB">-6 dB (Loud)</option>
              <option value="-12 dB">-12 dB (Balanced)</option>
              <option value="-18 dB">-18 dB (Quiet)</option>
            </select>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2 border-t border-border-subtle pt-4">
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
            onClick={() => onConfirm({ subtitleStyle, musicDucking, musicTrack })}
            disabled={isStarting}
            type="button"
          >
            {isStarting ? "Starting..." : "Start Render"}
          </button>
        </div>
      </div>
    </div>
  );
}
