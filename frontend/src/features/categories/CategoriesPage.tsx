import { useState } from 'react'

import PageHeader from '../../components/PageHeader'
import type { CategoryUpdate } from './api'
import CategoryForm from './CategoryForm'
import CategoryRow from './CategoryRow'
import SpendView from './SpendView'
import { buildTree } from './tree'
import {
  useCategories,
  useCreateCategory,
  useCreateDefaults,
  useRemoveCategory,
  useUpdateCategory,
} from './useCategories'

/**
 * The category tree, as a screen.
 *
 * The tree is drawn as the API lists it - each group, then the names under it -
 * and every edit is refused or accepted by the server, whose wording is shown
 * here rather than replaced by a second opinion.
 */
export default function CategoriesPage() {
  const categories = useCategories()
  const addCategory = useCreateCategory()
  const changeCategory = useUpdateCategory()
  const dropCategory = useRemoveCategory()
  const seedDefaults = useCreateDefaults()
  const [editingId, setEditingId] = useState<number | null>(null)

  const list = categories.data ?? []
  const tree = buildTree(list)
  const isEmpty = categories.isSuccess && list.length === 0

  /** Save one name's change, and close its editor once the server has taken it. */
  function save(categoryId: number) {
    return (update: CategoryUpdate): void => {
      changeCategory.mutate({ id: categoryId, update }, { onSuccess: () => setEditingId(null) })
    }
  }

  return (
    <>
      <PageHeader title="Categories" />

      {categories.isPending && <p className="mt-6 text-slate-600">Loading your categories…</p>}

      {categories.isError && (
        <p role="alert" className="mt-6 rounded bg-red-50 px-3 py-2 text-red-800">
          Could not load your categories: {categories.error.message}
        </p>
      )}

      {isEmpty && (
        <p className="mt-6 text-slate-700">
          There are no names yet. The default set is a recognisable starting point, and every part
          of it can be renamed, moved or removed afterwards.
        </p>
      )}

      {isEmpty && (
        <button
          type="button"
          onClick={() => seedDefaults.mutate()}
          disabled={seedDefaults.isPending}
          className="mt-4 min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
        >
          {seedDefaults.isPending ? 'Adding the default set…' : 'Add the default set'}
        </button>
      )}

      {seedDefaults.isError && (
        <p role="alert" className="mt-4 rounded bg-red-50 px-3 py-2 text-red-800">
          Could not add the default set: {seedDefaults.error.message}
        </p>
      )}

      {list.length > 0 && (
        <>
          <CategoryForm
            categories={list}
            onSubmit={(payload) => addCategory.mutate(payload)}
            isSaving={addCategory.isPending}
            errorMessage={addCategory.isError ? addCategory.error.message : null}
          />

          <h2 className="mt-8 text-lg font-semibold text-slate-900">The tree</h2>
          <ul className="mt-3 grid gap-3">
            {tree.map(({ category, children }) => (
              <li key={category.id} className="grid gap-2">
                <ul className="grid gap-2">
                  <CategoryRow
                    category={category}
                    categories={list}
                    childCount={children.length}
                    isEditing={editingId === category.id}
                    isSaving={changeCategory.isPending}
                    onToggleEdit={() =>
                      setEditingId(editingId === category.id ? null : category.id)
                    }
                    onSave={save(category.id)}
                    onRemove={() => dropCategory.mutate(category.id)}
                    errorMessage={changeCategory.isError ? changeCategory.error.message : null}
                  />
                </ul>

                {children.length > 0 && (
                  <ul className="ml-4 grid gap-2 border-l-2 border-slate-100 pl-3">
                    {children.map((child) => (
                      <CategoryRow
                        key={child.id}
                        category={child}
                        categories={list}
                        childCount={0}
                        isEditing={editingId === child.id}
                        isSaving={changeCategory.isPending}
                        onToggleEdit={() => setEditingId(editingId === child.id ? null : child.id)}
                        onSave={save(child.id)}
                        onRemove={() => dropCategory.mutate(child.id)}
                        errorMessage={changeCategory.isError ? changeCategory.error.message : null}
                      />
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>

          {dropCategory.isError && (
            <p role="alert" className="mt-4 rounded bg-red-50 px-3 py-2 text-red-800">
              {dropCategory.error.message}
            </p>
          )}

          <SpendView />
        </>
      )}
    </>
  )
}
