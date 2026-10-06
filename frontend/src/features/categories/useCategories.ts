/** Category data for the screens: the tree, read through TanStack Query. */

import { useQuery } from '@tanstack/react-query'

import { fetchCategories } from './api'

/**
 * The tree is cached under one key.
 *
 * Exported because adding, renaming, moving or removing a category changes what
 * every picker offers, so the screens that do those things have to drop it.
 */
export const CATEGORIES_KEY = ['categories'] as const

/** Every category the user has, in the order the API lists them. */
export function useCategories() {
  return useQuery({ queryKey: CATEGORIES_KEY, queryFn: fetchCategories })
}
