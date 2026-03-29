import { useState } from "react";
import { useComments, useAddComment, useResolveComment } from "../hooks/use-collaboration";

export function CommentThread({ targetId }: { targetId: string }) {
  const { data: comments, isLoading } = useComments(targetId);
  const { mutateAsync: addComment } = useAddComment();
  const { mutateAsync: resolveComment } = useResolveComment();
  const [newComment, setNewComment] = useState("");

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    await addComment({ targetId, text: newComment });
    setNewComment("");
  };

  if (isLoading) return <div style={{ fontSize: "14px", color: "var(--color-ink-lighter)" }}>Loading comments...</div>;

  return (
    <div className="surface-card">
      <h3 className="section-heading">Comments</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px", maxHeight: "200px", overflowY: "auto" }}>
        {comments?.length === 0 ? (
          <p className="body-copy" style={{ fontSize: "12px", color: "var(--color-ink-lighter)" }}>No comments yet.</p>
        ) : (
          comments?.map((c) => (
            <div key={c.id} style={{ padding: "8px", background: "var(--color-background)", borderRadius: "4px", border: "1px solid var(--color-border-subtle)", opacity: c.resolved ? 0.6 : 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                <strong style={{ fontSize: "11px", color: "var(--color-ink)" }}>{c.authorName}</strong>
                <span style={{ fontSize: "10px", color: "var(--color-ink-lighter)" }}>{new Date(c.timestamp).toLocaleTimeString()}</span>
              </div>
              <p style={{ fontSize: "12px", margin: 0 }}>{c.text}</p>
              {!c.resolved && (
                <button 
                  onClick={() => resolveComment(c.id)}
                  style={{ background: "transparent", border: "none", color: "var(--color-accent)", fontSize: "11px", padding: 0, marginTop: "6px", cursor: "pointer" }}
                >
                  Resolve
                </button>
              )}
            </div>
          ))
        )}
      </div>
      <form onSubmit={handleAdd} style={{ marginTop: "12px", display: "flex", gap: "8px" }}>
        <input 
          type="text" 
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="@mention or leave a note..." 
          style={{ flex: 1, padding: "8px", fontSize: "12px", borderRadius: "4px", border: "1px solid var(--color-border-subtle)", background: "var(--color-background)", color: "var(--color-ink)" }} 
        />
        <button type="submit" className="button button--secondary" style={{ padding: "8px 12px", fontSize: "12px" }}>Post</button>
      </form>
    </div>
  );
}
