import type { ReactNode } from 'react'

/** The one input style: 44px tall, so it is comfortable to tap on a phone. */
export const INPUT_CLASS = 'min-h-11 rounded border border-slate-300 px-3 py-2 text-slate-900'

interface FieldProps {
  label: string
  htmlFor: string
  error?: string
  children: ReactNode
}

/** A labelled form row: the label, the control, and the error under it. */
export default function Field({ label, htmlFor, error, children }: FieldProps) {
  return (
    <div className="grid gap-1">
      <label htmlFor={htmlFor} className="text-sm font-medium text-slate-800">
        {label}
      </label>
      {children}
      {error !== undefined && (
        <p id={`${htmlFor}-error`} className="text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
