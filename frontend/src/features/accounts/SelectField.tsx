import Field, { INPUT_CLASS } from './Field'

interface SelectFieldProps<T extends string> {
  label: string
  id: string
  value: T
  options: T[]
  labels: Record<T, string>
  error?: string
  onChange: (value: T) => void
}

/** A labelled select. Options come from the enum labels in `form.ts`. */
export default function SelectField<T extends string>({
  label,
  id,
  value,
  options,
  labels,
  error,
  onChange,
}: SelectFieldProps<T>) {
  return (
    <Field label={label} htmlFor={id} error={error}>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        aria-invalid={error !== undefined}
        aria-describedby={error !== undefined ? `${id}-error` : undefined}
        className={INPUT_CLASS}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {labels[option]}
          </option>
        ))}
      </select>
    </Field>
  )
}
