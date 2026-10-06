/**
 * Category calls.
 *
 * Every type comes from the generated OpenAPI schema, so a change on the server
 * surfaces here as a type error rather than a surprise at runtime.
 */

import type { components } from '../../lib/api-types'
import { requestJson, requestNoContent } from '../../lib/api'

export type Category = components['schemas']['CategoryResponse']
export type CategoryCreate = components['schemas']['CategoryCreate']
export type CategoryKind = Category['kind']
export type CategorySpend = components['schemas']['CategorySpendResponse']
export type CategoryUpdate = components['schemas']['CategoryUpdate']
export type CategoryDefaults = components['schemas']['DefaultsResponse']

const CATEGORIES_PATH = '/api/v1/categories'

/** The user's tree: each branch, then the names filed under it. */
export function fetchCategories(): Promise<Category[]> {
  return requestJson<Category[]>(CATEGORIES_PATH)
}

/** Add a name to the tree, as a branch of its own or under one. */
export function createCategory(payload: CategoryCreate): Promise<Category> {
  return requestJson<Category>(CATEGORIES_PATH, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Rename a category, move it in the tree, or both. */
export function updateCategory(categoryId: number, payload: CategoryUpdate): Promise<Category> {
  return requestJson<Category>(`${CATEGORIES_PATH}/${categoryId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/** Remove a category. The server keeps the row, so history stays readable. */
export function removeCategory(categoryId: number): Promise<void> {
  return requestNoContent(`${CATEGORIES_PATH}/${categoryId}`, { method: 'DELETE' })
}

/** Seed the default set, which does something only on an empty tree. */
export function createDefaults(): Promise<CategoryDefaults> {
  return requestJson<CategoryDefaults>(`${CATEGORIES_PATH}/defaults`, { method: 'POST' })
}
