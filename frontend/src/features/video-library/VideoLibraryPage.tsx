import { useCallback, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dialog } from "../../components/Dialog";
import { EmptyState, LoadingPage, PageFrame, SectionCard } from "../../components/ui";
import {
  mockBrowseFolder,
  mockCreateVideoLibraryProject,
  mockDeleteUploadedVideo,
  mockGetStreamUrl,
  mockGetUploadedVideos,
  mockGetVideoLibraryProjects,
  mockMoveVideoToProject,
  mockUploadLocalFile,
} from "../../lib/mock-service";
import type { LocalVideoFile, VideoLibraryItem, VideoLibraryProject } from "../../types/domain";

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
        className="relative w-full max-w-3xl rounded-2xl overflow-hidden bg-black shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 bg-surface/90 border-b border-border-subtle">
          <p className="text-sm font-semibold text-primary truncate max-w-[80%]">{title}</p>
          <button
            type="button"
            className="text-muted hover:text-primary transition-colors text-lg leading-none"
            onClick={onClose}
            aria-label="Close player"
          >
            ✕
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
            Create
          </button>
        </div>
      }
    >
      <form id="create-project-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-secondary uppercase tracking-wider" htmlFor="proj-name">
            Project name
          </label>
          <input
            id="proj-name"
            type="text"
            className="w-full rounded-lg border border-border-card bg-card px-3 py-2 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
            placeholder="e.g. Brand Assets 2024"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-secondary uppercase tracking-wider" htmlFor="proj-desc">
            Description <span className="text-muted font-normal normal-case">(optional)</span>
          </label>
          <textarea
            id="proj-desc"
            className="w-full rounded-lg border border-border-card bg-card px-3 py-2 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all resize-none"
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

  // Reset form state each time the dialog opens
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
      title={`Upload ${fileCount} ${fileCount === 1 ? "file" : "files"} to…`}
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
            Upload {fileCount > 0 ? `(${fileCount})` : ""} →
          </button>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        {/* No-project option */}
        <button
          type="button"
          className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
            selectedId === null
              ? "border-accent bg-primary-bg/40 ring-1 ring-accent/30"
              : "border-border-card bg-card hover:border-border-active"
          }`}
          onClick={() => setSelectedId(null)}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-bg shrink-0">
            <svg viewBox="0 0 24 24" className="w-5 h-5 text-muted" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.75h16.5M3.75 12h16.5m-16.5 2.25h16.5" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-primary">No project</p>
            <p className="text-xs text-muted">Upload without assigning to a project</p>
          </div>
          {selectedId === null && (
            <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent ml-auto shrink-0" fill="currentColor">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
            </svg>
          )}
        </button>

        {/* Existing projects */}
        {projects.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
              selectedId === p.id
                ? "border-accent bg-primary-bg/40 ring-1 ring-accent/30"
                : "border-border-card bg-card hover:border-border-active"
            }`}
            onClick={() => setSelectedId(p.id)}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-bg/50 shrink-0">
              <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent/70" fill="currentColor">
                <path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2h-8l-2-2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-primary truncate">{p.name}</p>
              {p.description && (
                <p className="text-xs text-muted truncate">{p.description}</p>
              )}
            </div>
            {selectedId === p.id && (
              <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent ml-auto shrink-0" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
              </svg>
            )}
          </button>
        ))}

        {/* Create new project */}
        {showCreate ? (
          <form
            onSubmit={(e) => void handleCreateAndSelect(e)}
            className="flex flex-col gap-3 rounded-xl border border-accent/40 bg-primary-bg/20 p-4"
          >
            <p className="text-xs font-bold uppercase tracking-wider text-accent">New project</p>
            <input
              type="text"
              className="w-full rounded-lg border border-border-card bg-card px-3 py-2 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
              placeholder="Project name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              autoFocus
              required
            />
            <input
              type="text"
              className="w-full rounded-lg border border-border-card bg-card px-3 py-2 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
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
                {creating ? "Creating…" : "Create & select"}
              </button>
            </div>
          </form>
        ) : (
          <button
            type="button"
            className="flex items-center gap-2 rounded-xl border border-dashed border-border-card px-4 py-3 text-sm text-muted hover:border-accent hover:text-accent transition-all"
            onClick={() => setShowCreate(true)}
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Create new project
          </button>
        )}
      </div>
    </Dialog>
  );
}

/* ─── LocalFileCard ───────────────────────────────────────────────────────── */
function LocalFileCard({
  file,
  selected,
  onSelect,
  onPlay,
}: {
  file: LocalVideoFile;
  selected: boolean;
  onSelect: () => void;
  onPlay: () => void;
}) {
  return (
    <div
      className={`relative flex flex-col rounded-xl border transition-all duration-150 overflow-hidden cursor-pointer group ${
        selected
          ? "border-accent shadow-[0_0_0_2px_var(--accent-glow-sm)] bg-primary-bg"
          : "border-border-card bg-card hover:border-border-active"
      }`}
    >
      {/* Thumbnail / play area */}
      <div
        className="relative h-32 bg-neutral-bg flex items-center justify-center"
        onClick={onPlay}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60 text-white transition-transform group-hover:scale-110">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M5 3l14 9-14 9V3z" />
          </svg>
        </div>
        <div className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-white font-mono">
          {file.content_type.split("/")[1]?.toUpperCase() ?? "VIDEO"}
        </div>
      </div>

      {/* Info */}
      <div className="flex flex-col gap-1 px-3 py-2.5">
        <p className="text-xs font-semibold text-primary truncate" title={file.name}>
          {file.name}
        </p>
        <p className="text-[11px] text-muted">{formatBytes(file.size_bytes)}</p>
      </div>

      {/* Select checkbox */}
      <div className="absolute top-2 left-2">
        <input
          type="checkbox"
          className="h-4 w-4 accent-accent rounded cursor-pointer"
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
      className={`relative flex flex-col rounded-xl border transition-all overflow-hidden group ${
        selected
          ? "border-accent shadow-[0_0_0_2px_var(--accent-glow-sm)] bg-primary-bg"
          : "border-border-card bg-card hover:border-border-active"
      }`}
    >
      {/* Thumbnail / play area */}
      <div
        className="relative h-32 bg-neutral-bg flex items-center justify-center cursor-pointer"
        onClick={onPlay}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60 text-white transition-transform group-hover:scale-110">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M5 3l14 9-14 9V3z" />
          </svg>
        </div>
        {item.duration_ms && (
          <div className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-white font-mono">
            {formatDuration(item.duration_ms)}
          </div>
        )}
        {item.width && item.height && (
          <div className="absolute bottom-2 left-2 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-white font-mono">
            {item.width}×{item.height}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-col gap-1 px-3 py-2.5">
        <p className="text-xs font-semibold text-primary truncate" title={item.file_name}>
          {item.file_name}
        </p>
        <div className="flex items-center justify-between gap-2">
          <p className="text-[11px] text-muted">{formatBytes(item.size_bytes)}</p>
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
            className="h-4 w-4 accent-accent rounded cursor-pointer"
            checked={selected}
            onChange={onSelect}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select ${item.file_name}`}
          />
        </div>
      )}

      {/* Context menu */}
      <div className="absolute top-2 right-2" ref={menuRef}>
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-lg bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80"
          onClick={() => setShowMenu((v) => !v)}
          aria-label="Options"
        >
          ⋯
        </button>
        {showMenu && (
          <div className="absolute right-0 top-full mt-1 w-48 rounded-xl border border-border-card bg-surface shadow-lg z-20 overflow-hidden">
            <p className="px-3 py-2 text-[0.65rem] uppercase tracking-wider font-bold text-muted border-b border-border-subtle">
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
                  item.project_id === p.id ? "text-accent font-semibold" : "text-secondary"
                }`}
                onClick={() => { onMoveToProject(p.id); setShowMenu(false); }}
              >
                {p.name}
              </button>
            ))}
            <div className="border-t border-border-subtle">
              <button
                type="button"
                className="w-full px-3 py-2 text-left text-xs text-error hover:bg-error-bg transition-colors"
                onClick={() => { onDelete(); setShowMenu(false); }}
              >
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
function LocalFilesTab({ projects }: { projects: VideoLibraryProject[] }) {
  const queryClient = useQueryClient();
  const [folderPath, setFolderPath] = useState("");
  const [committedPath, setCommittedPath] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [playingFile, setPlayingFile] = useState<{ src: string; name: string } | null>(null);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<Map<string, "pending" | "uploading" | "done" | "error">>(new Map());

  const { data: browseResult, isLoading: isBrowsing, error: browseError } = useQuery({
    queryKey: ["video-library-browse", committedPath],
    queryFn: () => mockBrowseFolder(committedPath),
    enabled: committedPath.length > 0,
    staleTime: 30_000,
  });

  const handleBrowse = useCallback(() => {
    // Trim whitespace and any trailing path separators (\ or /)
    const normalized = folderPath.trim().replace(/[/\\]+$/, "");
    if (normalized) {
      setCommittedPath(normalized);
      setSelectedFiles(new Set());
    }
  }, [folderPath]);

  const handleSelectFile = useCallback((path: string) => {
    setSelectedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    const files = browseResult?.files ?? [];
    setSelectedFiles((prev) =>
      prev.size === files.length ? new Set() : new Set(files.map((f) => f.path))
    );
  }, [browseResult]);

  const handleUpload = useCallback(async (projectId: string | null) => {
    const files = browseResult?.files.filter((f) => selectedFiles.has(f.path)) ?? [];
    if (!files.length) return;
    setShowUploadDialog(false);

    for (const file of files) {
      setUploadStatus((prev) => new Map(prev).set(file.path, "uploading"));
      try {
        await mockUploadLocalFile({
          local_path: file.path,
          project_id: projectId,
        });
        setUploadStatus((prev) => new Map(prev).set(file.path, "done"));
      } catch {
        setUploadStatus((prev) => new Map(prev).set(file.path, "error"));
      }
    }
    void queryClient.invalidateQueries({ queryKey: ["video-library-uploaded"] });
    setSelectedFiles(new Set());
  }, [browseResult, selectedFiles, queryClient]);

  const files = browseResult?.files ?? [];
  const selectedCount = selectedFiles.size;
  const allSelected = files.length > 0 && selectedCount === files.length;

  return (
    <>
      {/* Folder path input */}
      <div className="flex flex-col gap-3 p-5 rounded-xl bg-card border border-border-card shadow-card">
        <div className="flex flex-col gap-0.5">
          <p className="text-[0.6875rem] font-bold uppercase tracking-wider text-muted">Server folder path</p>
          <p className="text-[0.75rem] text-muted">
            Paste a Windows path (e.g. <span className="font-mono">F:\Personal\Videos</span>) or a Linux path. Spaces and special characters are supported.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 rounded-lg border border-border-card bg-surface px-3 py-2.5 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all font-mono placeholder:text-muted placeholder:font-sans"
            placeholder={String.raw`F:\Personal\Ai Reels on Food\Bangla (500+)`}
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleBrowse()}
          />
          <button
            type="button"
            className="btn-primary px-5"
            onClick={handleBrowse}
            disabled={!folderPath.trim()}
          >
            Browse
          </button>
        </div>
        {browseError && (
          <p className="text-xs text-error">
            {browseError instanceof Error ? browseError.message : "Failed to browse folder."}
          </p>
        )}
      </div>

      {/* Toolbar: select all, project, upload */}
      {files.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-1">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-secondary">
              <input
                type="checkbox"
                className="h-4 w-4 accent-accent rounded"
                checked={allSelected}
                onChange={handleSelectAll}
              />
              {allSelected ? "Deselect all" : "Select all"} ({files.length})
            </label>
            {selectedCount > 0 && (
              <span className="text-sm font-semibold text-primary">{selectedCount} selected</span>
            )}
          </div>

          <button
            type="button"
            className="btn-primary text-sm"
            disabled={selectedCount === 0}
            onClick={() => setShowUploadDialog(true)}
          >
            Upload {selectedCount > 0 ? `(${selectedCount})` : ""} →
          </button>
        </div>
      )}

      {/* Gallery */}
      {isBrowsing && (
        <div className="flex items-center justify-center py-16">
          <div className="w-6 h-6 border-4 border-border-subtle border-t-primary rounded-full animate-spin" />
        </div>
      )}

      {!isBrowsing && !browseError && committedPath && files.length === 0 && (
        <EmptyState
          title="No video files found"
          description={`No supported video files were found in: ${committedPath}`}
        />
      )}

      {!isBrowsing && !committedPath && (
        <EmptyState
          title="Enter a folder path"
          description="Paste a local server folder path above to browse video files stored on the server."
        />
      )}

      {!isBrowsing && files.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-4">
          {files.map((file) => {
            const status = uploadStatus.get(file.path);
            return (
              <div key={file.path} className="relative">
                <LocalFileCard
                  file={file}
                  selected={selectedFiles.has(file.path)}
                  onSelect={() => handleSelectFile(file.path)}
                  onPlay={() =>
                    setPlayingFile({
                      src: mockGetStreamUrl(file.path),
                      name: file.name,
                    })
                  }
                />
                {status === "uploading" && (
                  <div className="absolute inset-0 rounded-xl bg-black/60 flex items-center justify-center">
                    <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  </div>
                )}
                {status === "done" && (
                  <div className="absolute inset-0 rounded-xl bg-success/20 flex items-center justify-center">
                    <span className="text-success font-bold text-xl">✓</span>
                  </div>
                )}
                {status === "error" && (
                  <div className="absolute inset-0 rounded-xl bg-error/20 flex items-center justify-center">
                    <span className="text-error font-bold text-sm">Error</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Video player modal */}
      {playingFile && (
        <VideoPlayerModal
          src={playingFile.src}
          title={playingFile.name}
          onClose={() => setPlayingFile(null)}
        />
      )}

      {/* Upload project picker */}
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
      title={`Move ${itemCount} ${itemCount === 1 ? "file" : "files"} to…`}
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
            Move {itemCount > 0 ? `(${itemCount})` : ""} →
          </button>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        {/* No-project option */}
        {currentProjectId !== null && (
          <button
            type="button"
            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${
              selectedId === "unassigned"
                ? "border-accent bg-primary-bg/40 ring-1 ring-accent/30"
                : "border-border-card bg-card hover:border-border-active"
            }`}
            onClick={() => setSelectedId("unassigned")}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-bg shrink-0">
              <svg viewBox="0 0 24 24" className="w-5 h-5 text-muted" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.75h16.5M3.75 12h16.5m-16.5 2.25h16.5" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-primary">No project</p>
              <p className="text-xs text-muted">Remove from any project</p>
            </div>
            {selectedId === "unassigned" && (
              <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent ml-auto shrink-0" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
              </svg>
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
                  ? "border-accent bg-primary-bg/40 ring-1 ring-accent/30"
                  : "border-border-card bg-card hover:border-border-active"
              }`}
              onClick={() => setSelectedId(p.id)}
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-bg/50 shrink-0">
                <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent/70" fill="currentColor">
                  <path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2h-8l-2-2z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-primary truncate">{p.name}</p>
                {p.description && (
                  <p className="text-xs text-muted truncate">{p.description}</p>
                )}
              </div>
              {selectedId === p.id && (
                <svg viewBox="0 0 24 24" className="w-4 h-4 text-accent ml-auto shrink-0" fill="currentColor">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
                </svg>
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
}: {
  name: string;
  description?: string | null;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col gap-2 rounded-xl bg-glass border border-border-subtle p-4 text-left transition-all hover:border-accent/50 hover:bg-primary-bg/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      {/* Folder icon */}
      <div className="flex items-center justify-between w-full">
        <svg
          viewBox="0 0 24 24"
          className="w-10 h-10 text-accent/70 group-hover:text-accent transition-colors"
          fill="currentColor"
        >
          <path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2h-8l-2-2z" />
        </svg>
        <span className="text-xs font-semibold text-muted bg-primary-bg/50 rounded-full px-2 py-0.5">
          {count} {count === 1 ? "video" : "videos"}
        </span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-semibold text-primary group-hover:text-accent transition-colors line-clamp-1">
          {name}
        </span>
        {description && (
          <span className="text-xs text-muted line-clamp-2">{description}</span>
        )}
      </div>
    </button>
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

  // Fetch all items to compute per-folder counts at root level
  const { data: allItems = [], isLoading: allLoading } = useQuery({
    queryKey: ["video-library-uploaded", null],
    queryFn: () => mockGetUploadedVideos(null),
    staleTime: 30_000,
  });

  // When inside a project folder, fetch only that project's items
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

  // Bulk selection helpers
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

  // Count helpers
  const countForProject = (id: string) =>
    allItems.filter((i) => i.project_id === id).length;
  const unassignedCount = allItems.filter((i) => i.project_id === null).length;

  if (allLoading) return <LoadingPage />;

  /* ── Inside a folder ─────────────────────────────────────── */
  if (openFolderId !== null) {
    return (
      <>
        {/* Breadcrumb / back */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="flex items-center gap-1.5 text-sm text-muted hover:text-primary transition-colors"
              onClick={() => { setOpenFolderId(null); setSelectedIds(new Set()); }}
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              All Projects
            </button>
            <span className="text-muted text-sm">/</span>
            <span className="text-sm font-semibold text-primary">{folderName}</span>
          </div>
        </div>

        {/* Bulk-selection toolbar */}
        {!folderLoading && displayItems.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 px-1">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-secondary">
              <input
                type="checkbox"
                className="h-4 w-4 accent-accent rounded"
                checked={allSelected}
                onChange={handleSelectAll}
              />
              {allSelected ? "Deselect all" : "Select all"} ({displayItems.length})
            </label>
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-primary">{selectedIds.size} selected</span>
                <button
                  type="button"
                  className="btn-ghost text-sm"
                  onClick={() => setShowMoveDialog(true)}
                >
                  Move to project
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-error/40 bg-error-bg px-3 py-1.5 text-sm font-semibold text-error hover:bg-error/20 transition-colors"
                  onClick={() => setConfirmDelete(true)}
                >
                  Delete ({selectedIds.size})
                </button>
              </div>
            )}
          </div>
        )}

        {/* Folder content */}
        {folderLoading ? (
          <LoadingPage />
        ) : displayItems.length === 0 ? (
          <EmptyState
            title="No videos in this project"
            description="Upload videos from the Local Files tab and assign them to this project."
          />
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
              className="flex flex-col gap-5 w-full max-w-sm rounded-2xl bg-surface border border-border-card p-6 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div>
                <p className="text-base font-bold text-primary">Delete {selectedIds.size} {selectedIds.size === 1 ? "video" : "videos"}?</p>
                <p className="text-sm text-muted mt-1">This will permanently remove the selected files from storage. This cannot be undone.</p>
              </div>
              <div className="flex gap-3 justify-end">
                <button type="button" className="btn-ghost" onClick={() => setConfirmDelete(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="rounded-lg bg-error px-4 py-2 text-sm font-semibold text-white hover:bg-error/80 transition-colors"
                  onClick={() => void handleBulkDelete()}
                >
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
          + New project
        </button>
      </div>

      {projects.length === 0 && unassignedCount === 0 ? (
        <EmptyState
          title="No uploaded videos"
          description="Upload videos from the Local Files tab to see them here."
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-4">
          {projects.map((p) => (
            <ProjectFolderCard
              key={p.id}
              name={p.name}
              description={p.description}
              count={countForProject(p.id)}
              onClick={() => setOpenFolderId(p.id)}
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
  // Lifted from UploadedFilesTab so the inspector can navigate into a project
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

  return (
    <PageFrame
      eyebrow="Media management"
      title="Video Library"
      description="Browse server-side video folders, upload clips to MinIO storage, and organize them into projects."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Library stats">
            <div className="inspector-list">
              <div>
                <span>Projects</span>
                <strong>{projects.length}</strong>
              </div>
              <div>
                <span>Uploaded videos</span>
                <strong>{totalUploaded.data?.length ?? "--"}</strong>
              </div>
            </div>
          </SectionCard>

          {projects.length > 0 && (
            <SectionCard title="Projects">
              <div className="flex flex-col gap-2">
                {projects.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="group flex flex-col gap-0.5 px-3 py-2.5 rounded-lg bg-glass border border-border-subtle text-left transition-all hover:border-accent/50 hover:bg-primary-bg/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    onClick={() => {
                      setOpenFolderId(p.id);
                      setActiveTab("uploaded");
                    }}
                  >
                    <strong className="text-xs font-semibold text-primary group-hover:text-accent transition-colors">
                      {p.name}
                    </strong>
                    {p.description && (
                      <p className="text-[11px] text-muted line-clamp-2">{p.description}</p>
                    )}
                    <p className="text-[11px] text-muted mt-0.5">
                      {new Date(p.created_at).toLocaleDateString()}
                    </p>
                  </button>
                ))}
              </div>
            </SectionCard>
          )}
        </div>
      }
    >
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border-subtle pb-0 -mb-2">
        <button
          type="button"
          className={`px-4 py-2.5 text-sm font-semibold transition-all border-b-2 -mb-px ${
            activeTab === "local"
              ? "border-accent text-primary"
              : "border-transparent text-muted hover:text-secondary"
          }`}
          onClick={() => setActiveTab("local")}
        >
          Local Files
        </button>
        <button
          type="button"
          className={`px-4 py-2.5 text-sm font-semibold transition-all border-b-2 -mb-px ${
            activeTab === "uploaded"
              ? "border-accent text-primary"
              : "border-transparent text-muted hover:text-secondary"
          }`}
          onClick={() => setActiveTab("uploaded")}
        >
          Uploaded Files
          {(totalUploaded.data?.length ?? 0) > 0 && (
            <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-primary-bg text-primary text-[10px] font-bold px-1.5 py-px min-w-[1.25rem]">
              {totalUploaded.data?.length}
            </span>
          )}
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
