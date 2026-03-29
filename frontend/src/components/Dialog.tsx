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
    const element = dialogRef.current;
    if (!element) {
      return;
    }

    if (open && !element.open) {
      element.showModal();
    } else if (!open && element.open) {
      element.close();
    }
  }, [open]);

  useEffect(() => {
    const element = dialogRef.current;
    if (!element) {
      return;
    }

    const handleClose = () => onClose();
    element.addEventListener("close", handleClose);
    return () => element.removeEventListener("close", handleClose);
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
          x
        </button>
      </div>
      <div className="studio-dialog__body">{children}</div>
      {actions ? <div className="studio-dialog__actions">{actions}</div> : null}
    </dialog>
  );
}
