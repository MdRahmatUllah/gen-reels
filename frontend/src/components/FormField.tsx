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
      <label className="text-xs font-semibold text-slate-300" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {error ? <p className="text-[10px] text-accent-coral animate-fade-in-up mt-1">{error}</p> : null}
      {help && !error ? <p className="text-[10px] text-slate-500 mt-1">{help}</p> : null}
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
        className={`w-full rounded-md border bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none transition-all ${
          error 
            ? "border-accent-coral/50 focus:border-accent-coral focus:ring-1 focus:ring-accent-coral shadow-[0_0_10px_rgba(244,63,94,0.1)]" 
            : "border-slate-800/80 focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan hover:border-slate-700/80"
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
        className={`w-full rounded-md border bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none transition-all resize-y ${
          error 
            ? "border-accent-coral/50 focus:border-accent-coral focus:ring-1 focus:ring-accent-coral shadow-[0_0_10px_rgba(244,63,94,0.1)]" 
            : "border-slate-800/80 focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan hover:border-slate-700/80"
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
