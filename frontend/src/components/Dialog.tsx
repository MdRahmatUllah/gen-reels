import { useEffect, useRef, type ReactNode } from "react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  actions?: ReactNode;
}

export function Dialog({ open, onClose, title, children, actions }: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;

    if (open && !el.open) {
      el.showModal();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;

    const handleClose = () => onClose();
    el.addEventListener("close", handleClose);
    return () => el.removeEventListener("close", handleClose);
  }, [onClose]);

  return (
    <dialog ref={dialogRef} className="studio-dialog">
      <div className="studio-dialog__header">
        <h2>{title}</h2>
        <button
          type="button"
          className="studio-dialog__close"
          onClick={onClose}
          aria-label="Close dialog"
        >
          ✕
        </button>
      </div>
      <div className="studio-dialog__body">{children}</div>
      {actions ? (
        <div className="studio-dialog__actions">{actions}</div>
      ) : null}
    </dialog>
  );
}
