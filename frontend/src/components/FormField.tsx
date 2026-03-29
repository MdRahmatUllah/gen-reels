import type { ReactNode } from "react";

interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  help?: string;
  children: ReactNode;
}

export function FormField({ label, htmlFor, error, help, children }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      <label className="text-xs font-semibold uppercase tracking-wider text-muted" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {error ? <p className="mt-1 text-[10px] text-error animate-fade-in-up">{error}</p> : null}
      {help && !error ? <p className="mt-1 text-[10px] text-muted">{help}</p> : null}
    </div>
  );
}

export function FormInput({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  error,
  help,
  disabled,
}: {
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  help?: string;
  disabled?: boolean;
}) {
  return (
    <FormField label={label} htmlFor={id} error={error} help={help}>
      <input
        id={id}
        className={`w-full rounded-xl border bg-glass px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none transition-all ${
          error 
            ? "border-error focus:border-error"
            : "border-border-card focus:border-accent hover:border-border-active"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </FormField>
  );
}

export function FormTextarea({
  id,
  label,
  value,
  onChange,
  placeholder,
  error,
  help,
  rows = 4,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  help?: string;
  rows?: number;
  disabled?: boolean;
}) {
  return (
    <FormField label={label} htmlFor={id} error={error} help={help}>
      <textarea
        id={id}
        className={`w-full rounded-xl border bg-glass px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none transition-all resize-y ${
          error 
            ? "border-error focus:border-error"
            : "border-border-card focus:border-accent hover:border-border-active"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
      />
    </FormField>
  );
}
