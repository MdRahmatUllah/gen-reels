import { useState } from "react";

import { useAddComment, useComments, useResolveComment } from "../hooks/use-collaboration";

export function CommentThread({ targetId }: { targetId: string }) {
  const { data: comments, isLoading } = useComments(targetId);
  const { mutateAsync: addComment } = useAddComment();
  const { mutateAsync: resolveComment } = useResolveComment();
  const [newComment, setNewComment] = useState("");

  const handleAdd = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newComment.trim()) {
      return;
    }

    await addComment({ targetId, text: newComment });
    setNewComment("");
  };

  if (isLoading) {
    return <div className="text-sm text-muted">Loading comments...</div>;
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border-card bg-card p-5 shadow-card">
      <h3 className="text-[0.6875rem] font-bold uppercase tracking-widest text-muted">Comments</h3>

      <div className="no-scrollbar flex max-h-52 flex-col gap-3 overflow-y-auto">
        {comments?.length === 0 ? (
          <p className="text-sm text-muted">No comments yet.</p>
        ) : (
          comments?.map((comment) => (
            <div
              key={comment.id}
              className={`rounded-xl border border-border-subtle bg-glass p-3 ${comment.resolved ? "opacity-60" : ""}`}
            >
              <div className="flex items-start justify-between gap-3">
                <strong className="text-xs font-semibold text-primary">{comment.authorName}</strong>
                <span className="text-[10px] text-muted">
                  {new Date(comment.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="mt-2 text-sm text-secondary">{comment.text}</p>
              {!comment.resolved ? (
                <button
                  className="mt-2 text-xs font-semibold text-accent transition hover:text-accent-bright"
                  onClick={() => resolveComment(comment.id)}
                  type="button"
                >
                  Resolve
                </button>
              ) : null}
            </div>
          ))
        )}
      </div>

      <form className="flex gap-2" onSubmit={handleAdd}>
        <input
          className="flex-1 rounded-xl border border-border-card bg-glass px-3 py-2 text-sm text-primary outline-none transition-all duration-200 placeholder:text-muted focus:border-accent"
          type="text"
          value={newComment}
          onChange={(event) => setNewComment(event.target.value)}
          placeholder="@mention or leave a note..."
        />
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 hover:-translate-y-px hover:border-border-active hover:bg-glass-hover"
        >
          Post
        </button>
      </form>
    </div>
  );
}
