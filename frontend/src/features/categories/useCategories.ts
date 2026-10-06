/** Category data for the screens: the tree, and the edits that change it. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  type CategoryCreate,
  type CategoryUpdate,
  createCategory,
  createDefaults,
  fetchCategories,
  fetchSpend,
  removeCategory,
  updateCategory,
} from './api'

/**
 * The tree is cached under one key.
 *
 * Exported because adding, renaming, moving or removing a category changes what
 * every picker offers, so the screens that do those things have to drop it.
 */
export const CATEGORIES_KEY = ['categories'] as const

/**
 * Spending is cached per period.
 *
 * The prefix is exported because the report is derived from the tree and the
 * postings: a rename changes the names it reports, and a new movement changes
 * the figures, so both of them have to drop these caches.
 */
export const SPEND_KEY = 'category-spend'

function spendKey(from: string, to: string) {
  return [SPEND_KEY, from, to] as const
}

/** Every category the user has, in the order the API lists them. */
export function useCategories() {
  return useQuery({ queryKey: CATEGORIES_KEY, queryFn: fetchCategories })
}

/** What was spent in a period, as the server works it out. */
export function useSpend(from: string, to: string) {
  return useQuery({ queryKey: spendKey(from, to), queryFn: () => fetchSpend(from, to) })
}

/**
 * Tell the screens that the tree changed.
 *
 * The movements are dropped too: a row says which category a movement was filed
 * under, so a rename changes what the list says without changing the list. A
 * balance is untouched by any of this, which is why no balance cache is dropped.
 */
function useTreeChanged(): () => void {
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: CATEGORIES_KEY })
    void queryClient.invalidateQueries({ queryKey: [SPEND_KEY] })
    void queryClient.invalidateQueries({ queryKey: ['transactions'] })
  }
}

/** Add a name, as a branch of its own or under one. */
export function useCreateCategory() {
  const onChanged = useTreeChanged()

  return useMutation({
    mutationFn: (payload: CategoryCreate) => createCategory(payload),
    onSuccess: onChanged,
  })
}

/** Rename a name, move it, or both. */
export function useUpdateCategory() {
  const onChanged = useTreeChanged()

  return useMutation({
    mutationFn: ({ id, update }: { id: number; update: CategoryUpdate }) =>
      updateCategory(id, update),
    onSuccess: onChanged,
  })
}

/** Remove a name. The server keeps the row, so history stays readable. */
export function useRemoveCategory() {
  const onChanged = useTreeChanged()

  return useMutation({
    mutationFn: (id: number) => removeCategory(id),
    onSuccess: onChanged,
  })
}

/** Seed the default set, which does something only on an empty tree. */
export function useCreateDefaults() {
  const onChanged = useTreeChanged()

  return useMutation({
    mutationFn: () => createDefaults(),
    onSuccess: onChanged,
  })
}
