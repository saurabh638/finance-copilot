import { type FormEvent, useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { Category, CategoryUpdate } from './api'
import {
  editValues,
  moveTargets,
  nameProblem,
  updatePayload,
  type CategoryEditValues,
} from './manage'

interface CategoryEditorProps {
  category: Category
  /** The whole tree, so the name can be checked against its neighbours. */
  categories: Category[]
  onSave: (update: CategoryUpdate) => void
  onCancel: () => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * Renaming a name, moving it, or both.
 *
 * Where it goes is one choice with three meanings: leave it, take it out to the
 * top level, or put it under another group. A name that holds others cannot move
 * at all, because its children would be left behind, so it is offered no place.
 */
export default function CategoryEditor({
  category,
  categories,
  onSave,
  onCancel,
  isSaving,
  errorMessage = null,
}: CategoryEditorProps) {
  const [values, setValues] = useState<CategoryEditValues>(() => editValues(category))
  const [problem, setProblem] = useState<string | null>(null)

  const targets = moveTargets(categories, category)
  const canMove = category.parent_id !== null
  const placeOptions = ['', ...(canMove ? ['top'] : []), ...targets.map((row) => String(row.id))]
  const placeLabels: Record<string, string> = {
    '': 'Keep it where it is',
    top: 'A group of its own',
    ...Object.fromEntries(targets.map((row) => [String(row.id), `Under ${row.name}`])),
  }

  /** Where the name will sit once this is saved, for the name check. */
  function parentAfter(): number | null {
    if (values.place === 'top') {
      return null
    }
    if (values.place === '') {
      return category.parent_id
    }
    return Number(values.place)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = nameProblem(values.name, parentAfter(), categories, category.id)
    setProblem(found)
    if (found === null) {
      onSave(updatePayload(values, category))
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-3 grid gap-3 border-t pt-3">
      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <TextField
        label={`Name of ${category.name}`}
        id={`category-name-${category.id}`}
        value={values.name}
        error={problem ?? undefined}
        onChange={(value) => setValues((current) => ({ ...current, name: value }))}
      />

      {canMove && targets.length > 0 && (
        <SelectField
          label="Move it to"
          id={`category-place-${category.id}`}
          value={values.place}
          options={placeOptions}
          labels={placeLabels}
          onChange={(value) => setValues((current) => ({ ...current, place: value }))}
        />
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={isSaving}
          className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
        >
          {isSaving ? 'Saving…' : 'Save name'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 rounded border border-slate-300 px-4 text-slate-700"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
