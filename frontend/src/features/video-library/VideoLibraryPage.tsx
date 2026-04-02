import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dialog } from "../../components/Dialog";
import { LoadingPage, PageFrame, SectionCard } from "../../components/ui";
import {
  mockBrowseFolder,
  mockCreateVideoLibraryProject,
  mockDeleteVideoLibraryProject,
  mockDeleteUploadedVideo,
  mockGetStreamUrl,
  mockGetUploadedVideos,
  mockGetVideoLibraryProjects,
  mockMoveVideoToProject,
  mockUploadLocalFile,
  mockGetLocalFolderProjects,
  mockCreateLocalFolderProject,
  mockDeleteLocalFolderProject,
} from "../../lib/mock-service";
import type { LocalFolderProject, LocalVideoFile, VideoLibraryItem, VideoLibraryProject } from "../../types/domain";

/* ─── Icons ───────────────────────────────────────────────────────────────── */
function PlayIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M5 3l14 9-14 9V3z" />
    </svg>
  );
}

function PlusIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function UploadIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
    </svg>
  );
}

function TrashIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
    </svg>
  );
}

function ChevronLeftIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 19l-7-7 7-7" />
    </svg>
  );
}

function ChevronLeftSmIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 19l-7-7 7-7" />
    </svg>
  );
}

function ChevronRightSmIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 5l7 7-7 7" />
    </svg>
  );
}

function XIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function CheckIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function DotsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="12" cy="5" r="1.5" />
      <circle cx="12" cy="12" r="1.5" />
      <circle cx="12" cy="19" r="1.5" />
    </svg>
  );
}

function FolderIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2h-8l-2-2z" />
    </svg>
  );
}

function FilmIcon({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
      <path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5" />
    </svg>
  );
}

function MoveIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 9l7 7 7-7" />
    </svg>
  );
}

function WarningIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
    </svg>
  );
}

function FolderPlusIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
      <path d="M12 11v6M9 14h6" />
    </svg>
  );
}

/* ─── Helpers ─────────────────────────────────────────────────────────────── */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDuration(ms: number | null | undefined): string {
  if (!ms) return "--";
  const secs = Math.floor(ms / 1000);
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/* ─── VideoPlayerModal ────────────────────────────────────────────────────── */
function VideoPlayerModal({
  src,
  title,
  onClose,
}: {
  src: string;
  title: string;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-3xl rounded-2xl overflow-hidden bg-black shadow-2xl animate-rise-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 bg-surface/90 border-b border-border-subtle">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-bg text-primary-fg shrink-0">
              <PlayIcon size={12} />
            </div>
            <p className="text-sm font-semibold text-primary truncate">{title}</p>
          </div>
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-border-subtle bg-glass text-muted transition hover:border-border-active hover:text-primary hover:bg-glass-hover shrink-0 ml-3"
            onClick={onClose}
            aria-label="Close player"
          >
            <XIcon />
          </button>
        </div>
        <video
          src={src}
          controls
          autoPlay
          className="w-full max-h-[70vh] bg-black"
        />
      </div>
    </div>
  );
}

/* ─── CreateProjectDialog ─────────────────────────────────────────────────── */
function CreateProjectDialog({
  open,
  onClose,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string, description: string) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim(), description.trim());
      setName("");
      setDescription("");
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Create Project"
      actions={
        <div className="flex gap-3 justify-end">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="create-project-form" className="btn-primary">
            <PlusIcon size={13} />
            Create
          </button>
        </div>
      }
    >
      <form id="create-project-form" onSubmit={handleSubmit} className="form-grid">
        <div className="form-field">
          <label className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted" htmlFor="proj-name">
            Project name
          </label>
          <input
            id="proj-name"
            type="text"
            className="field-input"
            placeholder="e.g. Brand Assets 2024"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="form-field">
          <label className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted" htmlFor="proj-desc">
            Description <span className="text-muted font-normal normal-case tracking-normal">(optional)</span>
          </label>
          <textarea
            id="proj-desc"
            className="field-input field-textarea"
            placeholder="What kind of videos will go here?"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </form>
    </Dialog>
  );
}

/* ─── UploadProjectDialog ─────────────────────────────────────────────────── */
function UploadProjectDialog({
  open,
  fileCount,
  projects,
  onClose,
  onConfirm,
  onCreateProject,
}: {
  open: boolean;
  fileCount: number;
  projects: VideoLibraryProject[];
  onClose: () => void;
  onConfirm: (projectId: string | null) => void;
  onCreateProject: (name: string, description: string) => Promise<VideoLibraryProject>;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const prevOpenRef = useRef(false);
  if (open !== prevOpenRef.current) {
    prevOpenRef.current = open;
    if (open) {
      setSelectedId(null);
      setShowCreate(false);
      setNewName("");
      setNewDesc("");
    }
  }

  const handleCreateAndSelect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const created = await onCreateProject(newName.trim(), newDesc.trim());
      setSelectedId(created.id);
      setShowCreate(false);
      setNewName("");
      setNewDesc("");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Upload ${fileCount} ${fileCount === 1 ? "file" : "files"} to...`}
      actions={
        <div className="flex gap-3 justify-end">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => onConfirm(selectedId)}
          >
            <UploadIcon size={13} />
            Upload{fileCount > 0 ? ` (${fileCount})` : ""}
          </button>
        </div>
      }
    >
      <div className="flex flex-col gap-2.5">
        {/* No-project option */}
        <button
          type="button"
          className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
            selectedId === null
              ? "border-border-active bg-primary-bg/40 ring-1 ring-accent/30"
              : "border-border-card bg-card hover:border-border-active"
          }`}
          onClick={() => setSelectedId(null)}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-glass border border-border-subtle shrink-0">
            <svg viewBox="0 0 24 24" className="w-5 h-5 text-muted" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.75h16.5M3.75 12h16.5m-16.5 2.25h16.5" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-primary">No project</p>
            <p className="text-xs text-muted">Upload without assigning to a project</p>
          </div>
          {selectedId === null && (
            <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-accent text-on-accent shrink-0">
              <CheckIcon size={11} />
            </span>
          )}
        </button>

        {/* Existing projects */}
        {projects.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
              selectedId === p.id
                ? "border-border-active bg-primary-bg/40 ring-1 ring-accent/30"
                : "border-border-card bg-card hover:border-border-active"
            }`}
            onClick={() => setSelectedId(p.id)}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-bg shrink-0">
              <FolderIcon size={18} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-primary truncate">{p.name}</p>
              {p.description && (
                <p className="text-xs text-muted truncate">{p.description}</p>
              )}
            </div>
            {selectedId === p.id && (
              <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-accent text-on-accent shrink-0">
                <CheckIcon size={11} />
              </span>
            )}
          </button>
        ))}

        {/* Create new project */}
        {showCreate ? (
          <form
            onSubmit={(e) => void handleCreateAndSelect(e)}
            className="flex flex-col gap-3 rounded-xl border border-border-active bg-primary-bg/20 p-4"
          >
            <p className="text-[0.6875rem] font-bold uppercase tracking-widest text-primary-fg">New project</p>
            <input
              type="text"
              className="field-input"
              placeholder="Project name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              autoFocus
              required
            />
            <input
              type="text"
              className="field-input"
              placeholder="Description (optional)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                className="btn-ghost text-sm"
                onClick={() => { setShowCreate(false); setNewName(""); setNewDesc(""); }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary text-sm"
                disabled={!newName.trim() || creating}
              >
                {creating ? "Creating..." : "Create & select"}
              </button>
            </div>
          </form>
        ) : (
          <button
            type="button"
            className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-border-card px-4 py-3 text-sm font-semibold text-muted hover:border-border-active hover:text-primary transition-all"
            onClick={() => setShowCreate(true)}
          >
            <PlusIcon size={14} />
            Create new project
          </button>
        )}
      </div>
    </Dialog>
  );
}

/* ─── CreateLocalProjectDialog ───────────────────────────────────────────── */
function CreateLocalProjectDialog({
  open,
  onClose,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string, path: string) => void;
}) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim() && path.trim()) {
      onCreate(name.trim(), path.trim());
      setName("");
      setPath("");
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="New Folder Project"
      actions={
        <div className="flex gap-3 justify-end">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="create-local-project-form" className="btn-primary">
            <FolderPlusIcon size={14} />
            Create
          </button>
        </div>
      }
    >
      <form id="create-local-project-form" onSubmit={handleSubmit} className="form-grid">
        <div className="form-field">
          <label className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted" htmlFor="lfp-name">
            Project name
          </label>
          <input
            id="lfp-name"
            type="text"
            className="field-input"
            placeholder="e.g. Food Reels"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="form-field">
          <label className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted" htmlFor="lfp-path">
            Folder path
          </label>
          <input
            id="lfp-path"
            type="text"
            className="field-input font-mono"
            placeholder={String.raw`F:\Personal\Ai Reels on Food\Bangla`}
            value={path}
            onChange={(e) => setPath(e.target.value)}
            required
          />
          <p className="text-[0.7rem] text-muted">
            Windows (e.g. <span className="font-mono">F:\Videos</span>) or Linux paths. Spaces and special characters are supported.
          </p>
        </div>
      </form>
    </Dialog>
  );
}

/* ─── VideoThumbnail ──────────────────────────────────────────────────────── */
function VideoThumbnail({ src }: { src: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [inView, setInView] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleMetadata = () => {
    const v = videoRef.current;
    if (!v) return;
    const target = Math.min(5, Math.max(1, v.duration * 0.1));
    v.currentTime = isFinite(target) ? target : 0;
  };

  const handleSeeked = () => setReady(true);

  const handleTimeUpdate = () => {
    if (!ready && videoRef.current && videoRef.current.currentTime > 0) {
      setReady(true);
    }
  };

  return (
    <div ref={containerRef} className="absolute inset-0">
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-bg">
          {inView && !error && (
            <div className="w-4 h-4 border-2 border-border-subtle border-t-muted rounded-full animate-spin" />
          )}
        </div>
      )}
      {inView && (
        <video
          ref={videoRef}
          src={src}
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${ready ? "opacity-100" : "opacity-0"}`}
          preload="metadata"
          muted
          playsInline
          onLoadedMetadata={handleMetadata}
          onSeeked={handleSeeked}
          onTimeUpdate={handleTimeUpdate}
          onError={() => { setError(true); }}
        />
      )}
    </div>
  );
}

/* ─── LocalFileCard ───────────────────────────────────────────────────────── */
function LocalFileCard({
  file,
  selected,
  onSelect,
  onPlay,
  duplicates = [],
  thumbnailSrc,
}: {
  file: LocalVideoFile;
  selected: boolean;
  onSelect: () => void;
  onPlay: () => void;
  duplicates?: VideoLibraryItem[];
  thumbnailSrc?: string;
}) {
  const [showDupTooltip, setShowDupTooltip] = useState(false);
  const isDuplicate = duplicates.length > 0;

  return (
    <div
      className={`vlib-thumb-card group ${
        selected
          ? "vlib-thumb-card--selected"
          : isDuplicate
            ? "vlib-thumb-card--warning"
            : ""
      }`}
    >
      {/* Thumbnail / play area */}
      <div
        className="relative h-36 bg-neutral-bg flex items-center justify-center overflow-hidden cursor-pointer"
        onClick={onPlay}
      >
        {thumbnailSrc && <VideoThumbnail src={thumbnailSrc} />}
        <div className="relative z-10 flex h-11 w-11 items-center justify-center rounded-full bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-all duration-200 backdrop-blur-sm">
          <PlayIcon size={18} />
        </div>
        <div className="absolute bottom-2 right-2 z-10 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] text-white font-mono backdrop-blur-sm">
          {file.content_type.split("/")[1]?.toUpperCase() ?? "VIDEO"}
        </div>
        {isDuplicate && (
          <div className="absolute top-0 inset-x-0 z-10 flex items-center justify-center gap-1 bg-warning/90 py-1 text-[10px] font-bold text-black">
            <WarningIcon />
            Already uploaded
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-col gap-1 px-3 py-2.5">
        <p className="text-xs font-semibold text-primary truncate" title={file.name}>
          {file.name}
        </p>
        <div className="flex items-center justify-between gap-1">
          <p className="text-[0.68rem] text-muted">{formatBytes(file.size_bytes)}</p>
          {isDuplicate && (
            <div className="relative">
              <button
                type="button"
                className="text-[10px] font-semibold text-warning hover:text-warning/70 transition-colors underline underline-offset-2"
                onClick={(e) => { e.stopPropagation(); setShowDupTooltip((v) => !v); }}
              >
                {duplicates.length} match{duplicates.length > 1 ? "es" : ""}
              </button>
              {showDupTooltip && (
                <div
                  className="absolute bottom-full right-0 mb-2 w-52 rounded-xl border border-border-card bg-surface shadow-lg z-30 overflow-hidden"
                  onClick={(e) => e.stopPropagation()}
                >
                  <p className="px-3 py-2 text-[0.6875rem] uppercase tracking-widest font-bold text-muted border-b border-border-subtle">
                    Matched by file size
                  </p>
                  {duplicates.map((d) => (
                    <div key={d.id} className="px-3 py-2 border-b border-border-subtle last:border-0">
                      <p className="text-xs font-semibold text-primary truncate">{d.file_name}</p>
                      <p className="text-[0.68rem] text-muted">{formatBytes(d.size_bytes)}</p>
                    </div>
                  ))}
                  <p className="px-3 py-2 text-[10px] text-muted italic">
                    Same size strongly suggests identical content, even if names differ.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Select checkbox */}
      <div className="absolute top-2 left-2 z-10">
        <input
          type="checkbox"
          className="h-4 w-4 accent-[var(--accent)] rounded cursor-pointer"
          checked={selected}
          onChange={onSelect}
          onClick={(e) => e.stopPropagation()}
          aria-label={`Select ${file.name}`}
        />
      </div>
    </div>
  );
}

/* ─── UploadedVideoCard ───────────────────────────────────────────────────── */
function UploadedVideoCard({
  item,
  projects,
  selected = false,
  onSelect,
  onPlay,
  onMoveToProject,
  onDelete,
}: {
  item: VideoLibraryItem;
  projects: VideoLibraryProject[];
  selected?: boolean;
  onSelect?: () => void;
  onPlay: () => void;
  onMoveToProject: (projectId: string | null) => void;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const projectName = projects.find((p) => p.id === item.project_id)?.name ?? null;

  return (
    <div
      className={`vlib-thumb-card group ${selected ? "vlib-thumb-card--selected" : ""}`}
    >
      {/* Thumbnail / play area */}
      <div
        className="relative h-36 bg-neutral-bg flex items-center justify-center cursor-pointer overflow-hidden"
        onClick={onPlay}
      >
        <VideoThumbnail src={item.url} />
        <div className="relative z-10 flex h-11 w-11 items-center justify-center rounded-full bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-all duration-200 backdrop-blur-sm">
          <PlayIcon size={18} />
        </div>
        {item.duration_ms && (
          <div className="absolute bottom-2 right-2 z-10 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] text-white font-mono backdrop-blur-sm">
            {formatDuration(item.duration_ms)}
          </div>
        )}
        {item.width && item.height && (
          <div className="absolute bottom-2 left-2 z-10 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] text-white font-mono backdrop-blur-sm">
            {item.width}x{item.height}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-col gap-1.5 px-3 py-2.5">
        <p className="text-xs font-semibold text-primary truncate" title={item.file_name}>
          {item.file_name}
        </p>
        <div className="flex items-center justify-between gap-2">
          <p className="text-[0.68rem] text-muted">{formatBytes(item.size_bytes)}</p>
          {projectName && (
            <span className="tag-chip text-[10px] truncate max-w-[8rem]">{projectName}</span>
          )}
        </div>
      </div>

      {/* Select checkbox */}
      {onSelect && (
        <div className="absolute top-2 left-2 z-10">
          <input
            type="checkbox"
            className="h-4 w-4 accent-[var(--accent)] rounded cursor-pointer"
            checked={selected}
            onChange={onSelect}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select ${item.file_name}`}
          />
        </div>
      )}

      {/* Context menu */}
      <div className="absolute top-2 right-2 z-10" ref={menuRef}>
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-lg bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-all duration-200 hover:bg-black/70 backdrop-blur-sm"
          onClick={() => setShowMenu((v) => !v)}
          aria-label="Options"
        >
          <DotsIcon />
        </button>
        {showMenu && (
          <div className="absolute right-0 top-full mt-1 w-48 rounded-xl border border-border-card bg-surface shadow-lg z-20 overflow-hidden animate-rise-in">
            <p className="px-3 py-2 text-[0.6875rem] uppercase tracking-widest font-bold text-muted border-b border-border-subtle">
              Move to project
            </p>
            <button
              type="button"
              className="w-full px-3 py-2 text-left text-xs text-secondary hover:bg-glass transition-colors"
              onClick={() => { onMoveToProject(null); setShowMenu(false); }}
            >
              No project
            </button>
            {projects.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`w-full px-3 py-2 text-left text-xs hover:bg-glass transition-colors ${
                  item.project_id === p.id ? "text-primary-fg font-semibold" : "text-secondary"
                }`}
                onClick={() => { onMoveToProject(p.id); setShowMenu(false); }}
              >
                {p.name}
              </button>
            ))}
            <div className="border-t border-border-subtle">
              <button
                type="button"
                className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs text-error hover:bg-error-bg transition-colors"
                onClick={() => { onDelete(); setShowMenu(false); }}
              >
                <TrashIcon size={12} />
                Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── LocalFilesTab ───────────────────────────────────────────────────────── */
const LOCAL_FILES_PAGE_SIZE = 50;

function LocalFilesTab({ projects }: { projects: VideoLibraryProject[] }) {
  const queryClient = useQueryClient();
  const [openProject, setOpenProject] = useState<LocalFolderProject | null>(null);
  const [committedPath, setCommittedPath] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [playingFile, setPlayingFile] = useState<{ src: string; name: string } | null>(null);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [page, setPage] = useState(1);
  const [uploadStatus, setUploadStatus] = useState<Map<string, "pending" | "uploading" | "done" | "error">>(new Map());

  const { data: localProjects = [], isLoading: localProjectsLoading } = useQuery({
    queryKey: ["local-folder-projects"],
    queryFn: mockGetLocalFolderProjects,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (openProject) {
      setCommittedPath(openProject.path);
      setSelectedFiles(new Set());
      setUploadStatus(new Map());
      setPage(1);
    } else {
      setCommittedPath("");
    }
  }, [openProject]);

  const { data: browseResult, isLoading: isBrowsing, error: browseError } = useQuery({
    queryKey: ["video-library-browse", committedPath],
    queryFn: () => mockBrowseFolder(committedPath),
    enabled: committedPath.length > 0,
    staleTime: 30_000,
  });

  const createProjectMutation = useMutation({
    mutationFn: (payload: { name: string; path: string }) =>
      mockCreateLocalFolderProject(payload),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: ["local-folder-projects"] });
      setShowCreateProject(false);
      setOpenProject(created);
    },
  });

  const deleteProjectMutation = useMutation({
    mutationFn: (id: string) => mockDeleteLocalFolderProject(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["local-folder-projects"] });
      setOpenProject(null);
    },
  });

  const handleSelectFile = useCallback((path: string) => {
    setSelectedFiles((prev) => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    const pf = browseResult?.files.slice((page - 1) * LOCAL_FILES_PAGE_SIZE, page * LOCAL_FILES_PAGE_SIZE) ?? [];
    const allChecked = pf.length > 0 && pf.every((f) => selectedFiles.has(f.path));
    setSelectedFiles((prev) => {
      const next = new Set(prev);
      if (allChecked) pf.forEach((f) => next.delete(f.path));
      else pf.forEach((f) => next.add(f.path));
      return next;
    });
  }, [browseResult, page, selectedFiles]);

  const handleUpload = useCallback(async (projectId: string | null) => {
    const files = browseResult?.files.filter((f) => selectedFiles.has(f.path)) ?? [];
    if (!files.length) return;
    setShowUploadDialog(false);
    for (const file of files) {
      setUploadStatus((prev) => new Map(prev).set(file.path, "uploading"));
      try {
        await mockUploadLocalFile({ local_path: file.path, project_id: projectId });
        setUploadStatus((prev) => new Map(prev).set(file.path, "done"));
      } catch {
        setUploadStatus((prev) => new Map(prev).set(file.path, "error"));
      }
    }
    void queryClient.invalidateQueries({ queryKey: ["video-library-uploaded"] });
    setSelectedFiles(new Set());
  }, [browseResult, selectedFiles, queryClient]);

  const files = browseResult?.files ?? [];
  const totalPages = Math.max(1, Math.ceil(files.length / LOCAL_FILES_PAGE_SIZE));
  const pageFiles = files.slice((page - 1) * LOCAL_FILES_PAGE_SIZE, page * LOCAL_FILES_PAGE_SIZE);
  const selectedCount = selectedFiles.size;
  const allPageSelected = pageFiles.length > 0 && pageFiles.every((f) => selectedFiles.has(f.path));

  const { data: allUploaded = [] } = useQuery({
    queryKey: ["video-library-uploaded", null],
    queryFn: () => mockGetUploadedVideos(null),
    enabled: openProject !== null,
    staleTime: 30_000,
  });

  const uploadedBySize = new Map<number, VideoLibraryItem[]>();
  for (const item of allUploaded) {
    const bucket = uploadedBySize.get(item.size_bytes) ?? [];
    bucket.push(item);
    uploadedBySize.set(item.size_bytes, bucket);
  }

  /* ── Inside a project ─────────────────────────────────────── */
  if (openProject) {
    return (
      <>
        {/* Breadcrumb */}
        <div className="flex items-center justify-between">
          <div className="vlib-breadcrumb">
            <button
              type="button"
              className="vlib-breadcrumb__back"
              onClick={() => setOpenProject(null)}
            >
              <ChevronLeftIcon />
              All Folders
            </button>
            <span className="text-muted">/</span>
            <span className="font-semibold text-primary">{openProject.name}</span>
          </div>
          <button
            type="button"
            className="btn-ghost text-xs"
            style={{ color: "var(--error-fg)" }}
            onClick={() => deleteProjectMutation.mutate(openProject.id)}
          >
            <TrashIcon size={12} />
            Remove folder
          </button>
        </div>

        {/* Path badge */}
        <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-glass border border-border-subtle">
          <FolderIcon size={16} />
          <span className="text-xs font-mono text-muted truncate">{openProject.path}</span>
        </div>

        {/* Toolbar */}
        {files.length > 0 && (() => {
          const dupCount = files.filter((f) => (uploadedBySize.get(f.size_bytes)?.length ?? 0) > 0).length;
          return (
          <div className="vlib-toolbar">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer text-sm text-secondary">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--accent)] rounded"
                  checked={allPageSelected}
                  onChange={handleSelectAll}
                />
                {allPageSelected ? "Deselect page" : "Select page"} ({pageFiles.length})
              </label>
              {dupCount > 0 && (
                <span className="inline-flex items-center gap-1 text-[0.7rem] font-semibold text-warning bg-warning-bg border border-warning/30 rounded-full px-2.5 py-0.5">
                  <WarningIcon />
                  {dupCount} already uploaded
                </span>
              )}
            </div>
            {selectedCount > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-primary">{selectedCount} selected</span>
                <button
                  type="button"
                  className="btn-primary text-sm"
                  onClick={() => setShowUploadDialog(true)}
                >
                  <UploadIcon size={13} />
                  Upload ({selectedCount})
                </button>
              </div>
            )}
          </div>
          );
        })()}

        {/* Gallery */}
        {isBrowsing && (
          <div className="flex flex-col items-center justify-center gap-3 py-16">
            <div className="w-6 h-6 border-4 border-border-subtle border-t-accent rounded-full animate-spin" />
            <p className="text-sm text-muted">Scanning folder...</p>
          </div>
        )}

        {!isBrowsing && browseError && (
          <div className="rounded-xl border border-error/30 bg-error-bg px-4 py-3 text-sm text-error flex items-center gap-2">
            <WarningIcon size={16} />
            {browseError instanceof Error ? browseError.message : "Failed to browse folder."}
          </div>
        )}

        {!isBrowsing && !browseError && files.length === 0 && (
          <div className="vlib-empty">
            <div className="vlib-empty__icon">
              <FilmIcon />
            </div>
            <div className="flex flex-col gap-2 max-w-md">
              <h3 className="font-heading text-xl font-bold text-primary">No video files found</h3>
              <p className="text-[0.9rem] leading-relaxed text-secondary">
                No supported video files were found in: <span className="font-mono text-muted">{openProject.path}</span>
              </p>
            </div>
          </div>
        )}

        {!isBrowsing && files.length > 0 && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-4">
              {pageFiles.map((file) => {
                const status = uploadStatus.get(file.path);
                return (
                  <div key={file.path} className="relative">
                    <LocalFileCard
                      file={file}
                      selected={selectedFiles.has(file.path)}
                      onSelect={() => handleSelectFile(file.path)}
                      onPlay={() => setPlayingFile({ src: mockGetStreamUrl(file.path), name: file.name })}
                      thumbnailSrc={mockGetStreamUrl(file.path)}
                      duplicates={uploadedBySize.get(file.size_bytes) ?? []}
                    />
                    {status === "uploading" && (
                      <div className="absolute inset-0 rounded-2xl bg-black/60 flex flex-col items-center justify-center gap-2 backdrop-blur-sm">
                        <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                        <span className="text-[10px] font-semibold text-white/80">Uploading...</span>
                      </div>
                    )}
                    {status === "done" && (
                      <div className="absolute inset-0 rounded-2xl bg-success/20 flex flex-col items-center justify-center gap-1 backdrop-blur-sm">
                        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-success text-white">
                          <CheckIcon size={16} />
                        </span>
                        <span className="text-[10px] font-bold text-success">Uploaded</span>
                      </div>
                    )}
                    {status === "error" && (
                      <div className="absolute inset-0 rounded-2xl bg-error/20 flex flex-col items-center justify-center gap-1 backdrop-blur-sm">
                        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-error text-white">
                          <XIcon size={16} />
                        </span>
                        <span className="text-[10px] font-bold text-error">Failed</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-1 pt-2">
                <p className="text-xs text-muted">
                  {files.length} files · showing {(page - 1) * LOCAL_FILES_PAGE_SIZE + 1}--{Math.min(page * LOCAL_FILES_PAGE_SIZE, files.length)}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-card bg-card text-sm text-secondary transition-all hover:border-border-active hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed"
                    aria-label="Previous page"
                  >
                    <ChevronLeftSmIcon />
                  </button>

                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
                    .reduce<(number | "...")[]>((acc, p, i, arr) => {
                      if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push("...");
                      acc.push(p);
                      return acc;
                    }, [])
                    .map((item, i) =>
                      item === "..." ? (
                        <span key={`ellipsis-${i}`} className="px-1 text-muted text-sm">...</span>
                      ) : (
                        <button
                          key={item}
                          type="button"
                          onClick={() => setPage(item as number)}
                          className={`h-8 min-w-[2rem] px-2 rounded-lg border text-sm font-semibold transition-all ${
                            page === item
                              ? "border-border-active bg-primary-bg text-primary-fg"
                              : "border-border-card bg-card text-secondary hover:border-border-active hover:text-primary"
                          }`}
                        >
                          {item}
                        </button>
                      )
                    )}

                  <button
                    type="button"
                    disabled={page === totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-card bg-card text-sm text-secondary transition-all hover:border-border-active hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed"
                    aria-label="Next page"
                  >
                    <ChevronRightSmIcon />
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {playingFile && (
          <VideoPlayerModal
            src={playingFile.src}
            title={playingFile.name}
            onClose={() => setPlayingFile(null)}
          />
        )}

        <UploadProjectDialog
          open={showUploadDialog}
          fileCount={selectedFiles.size}
          projects={projects}
          onClose={() => setShowUploadDialog(false)}
          onConfirm={(projectId) => void handleUpload(projectId)}
          onCreateProject={async (name, description) => {
            const created = await mockCreateVideoLibraryProject({ name, description });
            void queryClient.invalidateQueries({ queryKey: ["video-library-projects"] });
            return created;
          }}
        />
      </>
    );
  }

  /* ── Root: folder project grid ────────────────────────────── */
  if (localProjectsLoading) return <LoadingPage />;

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <p className="text-sm text-muted">
          {localProjects.length} saved {localProjects.length === 1 ? "folder" : "folders"}
        </p>
        <button
          type="button"
          className="btn-ghost text-sm"
          onClick={() => setShowCreateProject(true)}
        >
          <FolderPlusIcon size={14} />
          New folder
        </button>
      </div>

      {localProjects.length === 0 ? (
        <div className="vlib-empty">
          <div className="vlib-empty__icon">
            <FolderIcon size={36} />
          </div>
          <div className="flex flex-col gap-2 max-w-md">
            <h3 className="font-heading text-xl font-bold text-primary">No saved folders</h3>
            <p className="text-[0.9rem] leading-relaxed text-secondary">
              Save a server folder path as a project to quickly browse and upload videos from it.
            </p>
          </div>
          <div className="flex flex-col gap-2 text-left max-w-sm w-full">
            {[
              { label: "Point to any folder", detail: "Save paths to server-side video directories" },
              { label: "Browse & preview", detail: "View thumbnails and play clips before uploading" },
              { label: "Batch upload", detail: "Select multiple files and upload them in one go" },
            ].map((item) => (
              <div key={item.label} className="vlib-empty__feature">
                <span className="vlib-empty__dot" />
                <div className="flex flex-col">
                  <strong className="text-sm font-semibold text-primary">{item.label}</strong>
                  <span className="text-xs text-secondary">{item.detail}</span>
                </div>
              </div>
            ))}
          </div>
          <button
            className="btn-primary mt-2"
            onClick={() => setShowCreateProject(true)}
            type="button"
          >
            <FolderPlusIcon size={14} />
            Add a folder
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-4">
          {localProjects.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setOpenProject(p)}
              className="vlib-folder-card text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <div className="vlib-folder-card__icon">
                <FolderIcon size={20} />
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-semibold text-primary group-hover:text-primary-fg transition-colors line-clamp-1">
                  {p.name}
                </span>
                <span className="text-[0.68rem] text-muted font-mono truncate">{p.path}</span>
              </div>
            </button>
          ))}
        </div>
      )}

      <CreateLocalProjectDialog
        open={showCreateProject}
        onClose={() => setShowCreateProject(false)}
        onCreate={(name, path) => createProjectMutation.mutate({ name, path })}
      />
    </>
  );
}

/* ─── MoveToProjectDialog ─────────────────────────────────────────────────── */
function MoveToProjectDialog({
  open,
  itemCount,
  projects,
  currentProjectId,
  onClose,
  onConfirm,
}: {
  open: boolean;
  itemCount: number;
  projects: VideoLibraryProject[];
  currentProjectId: string | null;
  onClose: () => void;
  onConfirm: (projectId: string | null) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | "unassigned">("unassigned");

  const prevOpenRef = useRef(false);
  if (open !== prevOpenRef.current) {
    prevOpenRef.current = open;
    if (open) setSelectedId("unassigned");
  }

  const targetProjectId = selectedId === "unassigned" ? null : selectedId;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Move ${itemCount} ${itemCount === 1 ? "file" : "files"} to...`}
      actions={
        <div className="flex gap-3 justify-end">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => onConfirm(targetProjectId)}
          >
            <MoveIcon />
            Move{itemCount > 0 ? ` (${itemCount})` : ""}
          </button>
        </div>
      }
    >
      <div className="flex flex-col gap-2.5">
        {/* No-project option */}
        {currentProjectId !== null && (
          <button
            type="button"
            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
              selectedId === "unassigned"
                ? "border-border-active bg-primary-bg/40 ring-1 ring-accent/30"
                : "border-border-card bg-card hover:border-border-active"
            }`}
            onClick={() => setSelectedId("unassigned")}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-glass border border-border-subtle shrink-0">
              <svg viewBox="0 0 24 24" className="w-5 h-5 text-muted" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.75h16.5M3.75 12h16.5m-16.5 2.25h16.5" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-primary">No project</p>
              <p className="text-xs text-muted">Remove from any project</p>
            </div>
            {selectedId === "unassigned" && (
              <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-accent text-on-accent shrink-0">
                <CheckIcon size={11} />
              </span>
            )}
          </button>
        )}

        {/* Projects (exclude current) */}
        {projects
          .filter((p) => p.id !== currentProjectId)
          .map((p) => (
            <button
              key={p.id}
              type="button"
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
                selectedId === p.id
                  ? "border-border-active bg-primary-bg/40 ring-1 ring-accent/30"
                  : "border-border-card bg-card hover:border-border-active"
              }`}
              onClick={() => setSelectedId(p.id)}
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-bg shrink-0">
                <FolderIcon size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-primary truncate">{p.name}</p>
                {p.description && (
                  <p className="text-xs text-muted truncate">{p.description}</p>
                )}
              </div>
              {selectedId === p.id && (
                <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-accent text-on-accent shrink-0">
                  <CheckIcon size={11} />
                </span>
              )}
            </button>
          ))}

        {projects.filter((p) => p.id !== currentProjectId).length === 0 && currentProjectId === null && (
          <p className="text-sm text-muted text-center py-4">No projects to move to. Create a project first.</p>
        )}
      </div>
    </Dialog>
  );
}

/* ─── ProjectFolderCard ──────────────────────────────────────────────────── */
function ProjectFolderCard({
  name,
  description,
  count,
  onClick,
  onDelete,
}: {
  name: string;
  description?: string | null;
  count: number;
  onClick: () => void;
  onDelete?: () => void;
}) {
  return (
    <div className="vlib-folder-card group">
      {/* Delete button */}
      {onDelete && (
        <button
          type="button"
          className="absolute top-3 right-3 z-10 opacity-0 group-hover:opacity-100 transition-opacity flex h-7 w-7 items-center justify-center rounded-lg bg-glass border border-border-subtle text-muted hover:text-error hover:border-error/40 hover:bg-error-bg"
          title="Delete project"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          <TrashIcon size={13} />
        </button>
      )}
      <button
        type="button"
        onClick={onClick}
        className="flex flex-col gap-2.5 text-left focus:outline-none w-full"
      >
        <div className="flex items-center justify-between w-full">
          <div className="vlib-folder-card__icon">
            <FolderIcon size={20} />
          </div>
          <span className="tag-chip text-[10px]">
            {count} {count === 1 ? "video" : "videos"}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-semibold text-primary group-hover:text-primary-fg transition-colors line-clamp-1">
            {name}
          </span>
          {description && (
            <span className="text-xs text-muted line-clamp-2">{description}</span>
          )}
        </div>
      </button>
    </div>
  );
}

/* ─── UploadedFilesTab ────────────────────────────────────────────────────── */
function UploadedFilesTab({
  projects,
  openFolderId,
  setOpenFolderId,
}: {
  projects: VideoLibraryProject[];
  openFolderId: string | null;
  setOpenFolderId: (id: string | null) => void;
}) {
  const queryClient = useQueryClient();
  const [playingItem, setPlayingItem] = useState<VideoLibraryItem | null>(null);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showMoveDialog, setShowMoveDialog] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: allItems = [], isLoading: allLoading } = useQuery({
    queryKey: ["video-library-uploaded", null],
    queryFn: () => mockGetUploadedVideos(null),
    staleTime: 30_000,
  });

  const apiProjectId = openFolderId === "unassigned" ? null : openFolderId;
  const { data: folderItems = [], isLoading: folderLoading } = useQuery({
    queryKey: ["video-library-uploaded", openFolderId],
    queryFn: () => mockGetUploadedVideos(apiProjectId),
    enabled: openFolderId !== null,
    staleTime: 30_000,
  });

  const displayItems =
    openFolderId === null
      ? []
      : openFolderId === "unassigned"
        ? folderItems.filter((i) => i.project_id === null)
        : folderItems;

  const moveMutation = useMutation({
    mutationFn: ({ itemId, projectId }: { itemId: string; projectId: string | null }) =>
      mockMoveVideoToProject(itemId, projectId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["video-library-uploaded"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId: string) => mockDeleteUploadedVideo(itemId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["video-library-uploaded"] });
    },
  });

  const deleteProjectMutation = useMutation({
    mutationFn: (projectId: string) => mockDeleteVideoLibraryProject(projectId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["video-library-projects"] });
      void queryClient.invalidateQueries({ queryKey: ["video-library-uploaded"] });
    },
  });

  function handleDeleteProject(projectId: string, name: string) {
    if (confirm(`Delete project "${name}" and all its videos? This cannot be undone.`)) {
      deleteProjectMutation.mutate(projectId);
    }
  }

  const createProjectMutation = useMutation({
    mutationFn: (payload: { name: string; description: string }) =>
      mockCreateVideoLibraryProject(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["video-library-projects"] });
      setShowCreateProject(false);
    },
  });

  const openProject = projects.find((p) => p.id === openFolderId);
  const folderName =
    openFolderId === "unassigned" ? "No Project" : (openProject?.name ?? "");
  const currentProjectId = openFolderId === "unassigned" ? null : openFolderId;

  const toggleSelect = (id: string) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  const allSelected = displayItems.length > 0 && selectedIds.size === displayItems.length;
  const handleSelectAll = () =>
    setSelectedIds(allSelected ? new Set() : new Set(displayItems.map((i) => i.id)));

  const handleBulkMove = async (projectId: string | null) => {
    setShowMoveDialog(false);
    for (const itemId of selectedIds) {
      await moveMutation.mutateAsync({ itemId, projectId });
    }
    setSelectedIds(new Set());
    void queryClient.invalidateQueries({ queryKey: ["video-library-uploaded"] });
  };

  const handleBulkDelete = async () => {
    setConfirmDelete(false);
    for (const itemId of selectedIds) {
      await deleteMutation.mutateAsync(itemId);
    }
    setSelectedIds(new Set());
    void queryClient.invalidateQueries({ queryKey: ["video-library-uploaded"] });
  };

  const countForProject = (id: string) =>
    allItems.filter((i) => i.project_id === id).length;
  const unassignedCount = allItems.filter((i) => i.project_id === null).length;

  if (allLoading) return <LoadingPage />;

  /* ── Inside a folder ─────────────────────────────────────── */
  if (openFolderId !== null) {
    return (
      <>
        {/* Breadcrumb */}
        <div className="flex items-center justify-between">
          <div className="vlib-breadcrumb">
            <button
              type="button"
              className="vlib-breadcrumb__back"
              onClick={() => { setOpenFolderId(null); setSelectedIds(new Set()); }}
            >
              <ChevronLeftIcon />
              All Projects
            </button>
            <span className="text-muted">/</span>
            <span className="font-semibold text-primary">{folderName}</span>
          </div>
          {openFolderId !== "unassigned" && openProject && (
            <button
              type="button"
              className="btn-ghost text-xs"
              style={{ color: "var(--error-fg)" }}
              disabled={deleteProjectMutation.isPending}
              onClick={() => {
                if (confirm(`Delete project "${openProject.name}" and all its videos? This cannot be undone.`)) {
                  deleteProjectMutation.mutate(openProject.id, {
                    onSuccess: () => { setOpenFolderId(null); setSelectedIds(new Set()); },
                  });
                }
              }}
            >
              <TrashIcon size={12} />
              {deleteProjectMutation.isPending ? "Deleting…" : "Delete project"}
            </button>
          )}
        </div>

        {/* Bulk-selection toolbar */}
        {!folderLoading && displayItems.length > 0 && (
          <div className="vlib-toolbar">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-secondary">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[var(--accent)] rounded"
                checked={allSelected}
                onChange={handleSelectAll}
              />
              {allSelected ? "Deselect all" : "Select all"} ({displayItems.length})
            </label>
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-primary">{selectedIds.size} selected</span>
                <button
                  type="button"
                  className="btn-ghost text-sm"
                  onClick={() => setShowMoveDialog(true)}
                >
                  <MoveIcon />
                  Move
                </button>
                <button
                  type="button"
                  className="btn-ghost text-sm"
                  style={{ color: "var(--error-fg)" }}
                  onClick={() => setConfirmDelete(true)}
                >
                  <TrashIcon size={13} />
                  Delete ({selectedIds.size})
                </button>
              </div>
            )}
          </div>
        )}

        {/* Folder content */}
        {folderLoading ? (
          <div className="flex flex-col items-center justify-center gap-3 py-16">
            <div className="w-6 h-6 border-4 border-border-subtle border-t-accent rounded-full animate-spin" />
            <p className="text-sm text-muted">Loading videos...</p>
          </div>
        ) : displayItems.length === 0 ? (
          <div className="vlib-empty">
            <div className="vlib-empty__icon">
              <FilmIcon />
            </div>
            <div className="flex flex-col gap-2 max-w-md">
              <h3 className="font-heading text-xl font-bold text-primary">No videos in this project</h3>
              <p className="text-[0.9rem] leading-relaxed text-secondary">
                Upload videos from the Local Files tab and assign them to this project.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-4">
            {displayItems.map((item) => (
              <UploadedVideoCard
                key={item.id}
                item={item}
                projects={projects}
                selected={selectedIds.has(item.id)}
                onSelect={() => toggleSelect(item.id)}
                onPlay={() => setPlayingItem(item)}
                onMoveToProject={(projectId) =>
                  moveMutation.mutate({ itemId: item.id, projectId })
                }
                onDelete={() => deleteMutation.mutate(item.id)}
              />
            ))}
          </div>
        )}

        {/* Video player modal */}
        {playingItem && (
          <VideoPlayerModal
            src={playingItem.url}
            title={playingItem.file_name}
            onClose={() => setPlayingItem(null)}
          />
        )}

        {/* Bulk move dialog */}
        <MoveToProjectDialog
          open={showMoveDialog}
          itemCount={selectedIds.size}
          projects={projects}
          currentProjectId={currentProjectId}
          onClose={() => setShowMoveDialog(false)}
          onConfirm={(projectId) => void handleBulkMove(projectId)}
        />

        {/* Bulk delete confirmation */}
        {confirmDelete && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setConfirmDelete(false)}
          >
            <div
              className="flex flex-col gap-5 w-full max-w-sm rounded-2xl bg-surface border border-border-card p-6 shadow-2xl animate-rise-in"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-error-bg text-error shrink-0">
                  <TrashIcon size={22} />
                </div>
                <div>
                  <p className="text-base font-heading font-bold text-primary">Delete {selectedIds.size} {selectedIds.size === 1 ? "video" : "videos"}?</p>
                  <p className="text-sm text-secondary mt-1">This will permanently remove the selected files from storage. This cannot be undone.</p>
                </div>
              </div>
              <div className="flex gap-3 justify-end">
                <button type="button" className="btn-ghost" onClick={() => setConfirmDelete(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="inline-flex items-center justify-center gap-2 min-h-[2.2rem] px-4 py-1.5 rounded-lg font-semibold text-sm transition-all duration-200 cursor-pointer bg-error text-white hover:bg-error/80 shadow-sm"
                  onClick={() => void handleBulkDelete()}
                >
                  <TrashIcon size={13} />
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  /* ── Root: project folder grid ───────────────────────────── */
  return (
    <>
      {/* Header row */}
      <div className="flex items-center justify-between px-1">
        <p className="text-sm text-muted">
          {projects.length} {projects.length === 1 ? "project" : "projects"}
          {unassignedCount > 0 && ` · ${unassignedCount} unassigned`}
        </p>
        <button
          type="button"
          className="btn-ghost text-sm"
          onClick={() => setShowCreateProject(true)}
        >
          <PlusIcon size={13} />
          New project
        </button>
      </div>

      {projects.length === 0 && unassignedCount === 0 ? (
        <div className="vlib-empty">
          <div className="vlib-empty__icon">
            <UploadIcon size={36} />
          </div>
          <div className="flex flex-col gap-2 max-w-md">
            <h3 className="font-heading text-xl font-bold text-primary">No uploaded videos</h3>
            <p className="text-[0.9rem] leading-relaxed text-secondary">
              Upload videos from the Local Files tab and organize them into projects here.
            </p>
          </div>
          <div className="flex flex-col gap-2 text-left max-w-sm w-full">
            {[
              { label: "Create projects", detail: "Group videos by topic, brand, or campaign" },
              { label: "Organize clips", detail: "Drag videos between projects or leave unassigned" },
              { label: "Preview & manage", detail: "Play, move, or delete uploaded videos" },
            ].map((item) => (
              <div key={item.label} className="vlib-empty__feature">
                <span className="vlib-empty__dot" />
                <div className="flex flex-col">
                  <strong className="text-sm font-semibold text-primary">{item.label}</strong>
                  <span className="text-xs text-secondary">{item.detail}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-4">
          {projects.map((p) => (
            <ProjectFolderCard
              key={p.id}
              name={p.name}
              description={p.description}
              count={countForProject(p.id)}
              onClick={() => setOpenFolderId(p.id)}
              onDelete={() => handleDeleteProject(p.id, p.name)}
            />
          ))}
          {unassignedCount > 0 && (
            <ProjectFolderCard
              name="No Project"
              description="Videos not assigned to any project"
              count={unassignedCount}
              onClick={() => setOpenFolderId("unassigned")}
            />
          )}
        </div>
      )}

      {/* Create project dialog */}
      <CreateProjectDialog
        open={showCreateProject}
        onClose={() => setShowCreateProject(false)}
        onCreate={(name, description) => createProjectMutation.mutate({ name, description })}
      />
    </>
  );
}

/* ─── VideoLibraryPage ────────────────────────────────────────────────────── */
export function VideoLibraryPage() {
  const [activeTab, setActiveTab] = useState<"local" | "uploaded">("local");
  const [openFolderId, setOpenFolderId] = useState<string | null>(null);

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ["video-library-projects"],
    queryFn: mockGetVideoLibraryProjects,
    staleTime: 60_000,
  });

  const totalUploaded = useQuery({
    queryKey: ["video-library-uploaded", null],
    queryFn: () => mockGetUploadedVideos(null),
    staleTime: 60_000,
  });

  const totalUploadedCount = totalUploaded.data?.length ?? 0;
  const totalSizeBytes = totalUploaded.data?.reduce((sum, i) => sum + i.size_bytes, 0) ?? 0;

  return (
    <PageFrame
      eyebrow="Media management"
      title="Video Library"
      description="Browse server-side video folders, upload clips to storage, and organize them into projects for remix and generation."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Library overview">
            <div className="grid grid-cols-2 gap-2">
              <div className="vlib-page-stat">
                <span className="vlib-page-stat__value text-primary-fg">{projects.length}</span>
                <span className="vlib-page-stat__label">Projects</span>
              </div>
              <div className="vlib-page-stat">
                <span className="vlib-page-stat__value">{totalUploadedCount}</span>
                <span className="vlib-page-stat__label">Uploaded</span>
              </div>
            </div>
            {totalSizeBytes > 0 && (
              <p className="text-xs text-muted mt-2 text-center">
                {formatBytes(totalSizeBytes)} total storage
              </p>
            )}
          </SectionCard>

          {projects.length > 0 && (
            <SectionCard title="Projects">
              <div className="flex flex-col gap-2">
                {projects.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="group flex items-center gap-3 px-3 py-2.5 rounded-xl bg-glass border border-border-subtle text-left transition-all hover:border-border-active hover:bg-glass-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    onClick={() => {
                      setOpenFolderId(p.id);
                      setActiveTab("uploaded");
                    }}
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-bg text-primary-fg shrink-0">
                      <FolderIcon size={14} />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <strong className="text-xs font-semibold text-primary group-hover:text-primary-fg transition-colors truncate">
                        {p.name}
                      </strong>
                      {p.description && (
                        <p className="text-[0.68rem] text-muted line-clamp-1">{p.description}</p>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </SectionCard>
          )}
        </div>
      }
    >
      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl bg-glass border border-border-subtle p-1 w-fit">
        <button
          type="button"
          className={`vlib-tab ${activeTab === "local" ? "vlib-tab--active" : "vlib-tab--inactive"}`}
          onClick={() => setActiveTab("local")}
        >
          <span className="flex items-center gap-2">
            <FolderIcon size={14} />
            Local Files
          </span>
        </button>
        <button
          type="button"
          className={`vlib-tab ${activeTab === "uploaded" ? "vlib-tab--active" : "vlib-tab--inactive"}`}
          onClick={() => setActiveTab("uploaded")}
        >
          <span className="flex items-center gap-2">
            <UploadIcon size={14} />
            Uploaded Files
            {totalUploadedCount > 0 && (
              <span className="inline-flex items-center justify-center rounded-full bg-primary-bg text-primary-fg text-[10px] font-bold px-1.5 py-px min-w-[1.25rem]">
                {totalUploadedCount}
              </span>
            )}
          </span>
        </button>
      </div>

      {projectsLoading ? (
        <LoadingPage />
      ) : activeTab === "local" ? (
        <LocalFilesTab projects={projects} />
      ) : (
        <UploadedFilesTab
          projects={projects}
          openFolderId={openFolderId}
          setOpenFolderId={setOpenFolderId}
        />
      )}
    </PageFrame>
  );
}
