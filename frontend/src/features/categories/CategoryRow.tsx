import { useState } from 'react'

import type { Category, CategoryUpdate } from './api'
import CategoryEditor from './CategoryEditor'

interface CategoryRowProps {
  category: Category
  /** The whole tree, so an edit can check the name and offer the places. */
  categories: Category[]
  /** How many names are filed under it, which is none for a name that holds nothing. */
  childCount: number
  isEditing: boolean
  isSaving: boolean
  onToggleEdit: () => void
  onSave: (update: CategoryUpdate) => void
  onRemove: () => void
  errorMessage?: string | null
}

/**
 * One name in the tree, with what can be done to it.
 *
 * Removal asks first and says what it would do, because removing a name that
 * holds others or that money is filed under is refused by the server and worth
 * explaining rather than discovering.
 */
export default function CategoryRow({
  category,
  categories,
  childCount,
  isEditing,
  isSaving,
  onToggleEdit,
  onSave,
  onRemove,
  errorMessage = null,
}: CategoryRowProps) {
  const [isConfirming, setIsConfirming] = useState(false)

  return (
    <li className="rounded border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3 className="font-medium text-slate-900">{category.name}</h3>
          <p className="text-sm text-slate-600">
            {childCount === 0
              ? 'Nothing filed under it'
              : `Holds ${childCount} ${childCount === 1 ? 'name' : 'names'}`}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            aria-expanded={isEditing}
            onClick={onToggleEdit}
            className="min-h-11 rounded border border-slate-300 px-3 text-slate-700"
          >
            {isEditing ? 'Close' : 'Rename or move'}
          </button>
          <button
            type="button"
            onClick={() => setIsConfirming(true)}
            disabled={isConfirming}
            className="min-h-11 rounded border border-slate-300 px-3 text-slate-700 disabled:opacity-60"
          >
            Remove
          </button>
        </div>
      </div>

      {isConfirming && (
        <div className="mt-3 rounded bg-amber-50 p-3">
          <p className="text-sm text-amber-900">
            Remove {category.name}?{childCount > 0 && ` It still holds ${childCount}.`} The record
            is kept, so movements already filed under it stay readable.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setIsConfirming(false)
                onRemove()
              }}
              className="min-h-11 rounded bg-red-700 px-3 text-white"
            >
              Yes, remove it
            </button>
            <button
              type="button"
              onClick={() => setIsConfirming(false)}
              className="min-h-11 rounded border border-slate-300 px-3 text-slate-700"
            >
              Keep it
            </button>
          </div>
        </div>
      )}

      {isEditing && (
        <CategoryEditor
          category={category}
          categories={categories}
          onSave={onSave}
          onCancel={onToggleEdit}
          isSaving={isSaving}
          errorMessage={errorMessage}
        />
      )}
    </li>
  )
}
