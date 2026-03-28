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
    <div className="form-field">
      <label className="field-label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {error ? <p className="form-field__error">{error}</p> : null}
      {help && !error ? <p className="form-field__help">{help}</p> : null}
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
        className={`field-input ${error ? "field-input--error" : ""}`}
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
        className={`field-input field-textarea ${error ? "field-input--error" : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
      />
    </FormField>
  );
}
