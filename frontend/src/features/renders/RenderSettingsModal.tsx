import { useState } from "react";

interface RenderSettingsModalProps {
  onClose: () => void;
  onConfirm: (settings: { subtitleStyle: string; musicDucking: string; musicTrack: string; }) => void;
  isStarting: boolean;
}

export function RenderSettingsModal({ onClose, onConfirm, isStarting }: RenderSettingsModalProps) {
  const [subtitleStyle, setSubtitleStyle] = useState("Karaoke Bold");
  const [musicDucking, setMusicDucking] = useState("-12 dB");
  const [musicTrack, setMusicTrack] = useState("Ambient Corporate 1");

  return (
    <div className="scene-empty-state" style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="surface-card" style={{ width: "400px", display: "flex", flexDirection: "column", gap: "16px", background: "var(--color-surface)", border: "1px solid var(--color-border-subtle)" }}>
        <div>
          <h2 style={{ fontSize: "16px", marginBottom: "4px" }}>Mix Settings</h2>
          <p style={{ fontSize: "12px", color: "var(--color-ink-lighter)", margin: 0 }}>Configure subtitles and audio before initiating the render pipeline.</p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "var(--font-weight-medium)", marginBottom: "4px" }}>Subtitle Style</label>
            <select className="search-input" value={subtitleStyle} onChange={(e) => setSubtitleStyle(e.target.value)} style={{ width: "100%" }}>
              <option value="Karaoke Bold">Karaoke Bold</option>
              <option value="Minimalist White">Minimalist White</option>
              <option value="Burned-in Default">Burned-in Default</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "var(--font-weight-medium)", marginBottom: "4px" }}>Music Track</label>
            <select className="search-input" value={musicTrack} onChange={(e) => setMusicTrack(e.target.value)} style={{ width: "100%" }}>
              <option value="Ambient Corporate 1">Ambient Corporate 1</option>
              <option value="Lo-fi Chill">Lo-fi Chill</option>
              <option value="Upbeat Electronic">Upbeat Electronic</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "var(--font-weight-medium)", marginBottom: "4px" }}>Music Ducking</label>
            <select className="search-input" value={musicDucking} onChange={(e) => setMusicDucking(e.target.value)} style={{ width: "100%" }}>
              <option value="-6 dB">-6 dB (Loud)</option>
              <option value="-12 dB">-12 dB (Balanced)</option>
              <option value="-18 dB">-18 dB (Quiet)</option>
            </select>
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "16px", paddingTop: "16px", borderTop: "1px solid var(--color-border-subtle)" }}>
          <button className="button button--secondary" onClick={onClose} disabled={isStarting}>
            Cancel
          </button>
          <button 
            className="button button--primary" 
            onClick={() => onConfirm({ subtitleStyle, musicDucking, musicTrack })}
            disabled={isStarting}
          >
            {isStarting ? "Starting..." : "Start Render"}
          </button>
        </div>
      </div>
    </div>
  );
}
