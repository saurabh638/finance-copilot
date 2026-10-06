import { type FormEvent, useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { Category, CategoryCreate } from './api'
import {
  DRAFT_KINDS,
  DRAFT_KIND_LABELS,
  blankDraft,
  draftPayload,
  nameProblem,
  type CategoryDraft,
} from './manage'

interface CategoryFormProps {
  /** The tree the new name has to fit into. */
  categories: Category[]
  onSubmit: (payload: CategoryCreate) => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * Adding one name to the tree.
 *
 * A name either stands on its own, and then it needs a kind, or it sits under a
 * branch and carries that branch's kind. The two are one form because they are
 * one action: the user is naming something, and only the place differs.
 */
export default function CategoryForm({
  categories,
  onSubmit,
  isSaving,
  errorMessage = null,
}: CategoryFormProps) {
  const [draft, setDraft] = useState<CategoryDraft>(() => blankDraft())
  const [problem, setProblem] = useState<string | null>(null)

  const branches = categories.filter((row) => row.parent_id === null)
  const parentId = draft.parent_id === '' ? null : Number(draft.parent_id)

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = nameProblem(draft.name, parentId, categories)
    setProblem(found)
    if (found === null) {
      onSubmit(draftPayload(draft))
      setDraft(blankDraft())
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-4 grid gap-4 sm:max-w-md">
      <h2 className="text-lg font-semibold text-slate-900">Add a name</h2>

      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <TextField
        label="Name"
        id="category-name"
        value={draft.name}
        error={problem ?? undefined}
        onChange={(value) => setDraft((current) => ({ ...current, name: value }))}
      />

      <SelectField
        label="Where it goes"
        id="category-parent"
        value={draft.parent_id}
        options={['', ...branches.map((row) => String(row.id))]}
        labels={{
          '': 'A group of its own',
          ...Object.fromEntries(branches.map((row) => [String(row.id), `Under ${row.name}`])),
        }}
        onChange={(value) => setDraft((current) => ({ ...current, parent_id: value }))}
      />

      {draft.parent_id === '' && (
        <SelectField<Category['kind']>
          label="What it is for"
          id="category-kind"
          value={draft.kind}
          options={DRAFT_KINDS}
          labels={DRAFT_KIND_LABELS}
          onChange={(value) => setDraft((current) => ({ ...current, kind: value }))}
        />
      )}

      <button
        type="submit"
        disabled={isSaving}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        {isSaving ? 'Adding…' : 'Add name'}
      </button>
    </form>
  )
}
