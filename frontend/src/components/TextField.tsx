import Field, { INPUT_CLASS } from './Field'

interface TextFieldProps {
  label: string
  id: string
  value: string
  error?: string
  type?: 'text' | 'date'
  inputMode?: 'text' | 'decimal' | 'numeric'
  onChange: (value: string) => void
}

/** A labelled text input, with the error wired to it for screen readers. */
export default function TextField({
  label,
  id,
  value,
  error,
  type = 'text',
  inputMode = 'text',
  onChange,
}: TextFieldProps) {
  return (
    <Field label={label} htmlFor={id} error={error}>
      <input
        id={id}
        type={type}
        inputMode={inputMode}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error !== undefined}
        aria-describedby={error !== undefined ? `${id}-error` : undefined}
        className={INPUT_CLASS}
      />
    </Field>
  )
}
