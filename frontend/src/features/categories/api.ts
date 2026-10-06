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
export type SpendReport = components['schemas']['SpendReportResponse']
export type SpendRow = components['schemas']['CategorySpendResponse']
export type CategoryUpdate = components['schemas']['CategoryUpdate']
export type CategoryDefaults = components['schemas']['DefaultsResponse']

const CATEGORIES_PATH = '/api/v1/categories'

/** The user's tree: each branch, then the names filed under it. */
export function fetchCategories(): Promise<Category[]> {
  return requestJson<Category[]>(CATEGORIES_PATH)
}

/**
 * The query string for a spending period.
 *
 * Only what is set is sent, as the movements list does it: an empty end means
 * "no end", rather than a blank date for the server to refuse.
 */
export function spendQuery(from: string, to: string): string {
  const parts: string[] = []

  if (from !== '') {
    parts.push(`from=${encodeURIComponent(from)}`)
  }
  if (to !== '') {
    parts.push(`to=${encodeURIComponent(to)}`)
  }
  return parts.length === 0 ? '' : `?${parts.join('&')}`
}

/** What was spent in a period: the tree, the money in no category, and the whole. */
export function fetchSpend(from: string, to: string): Promise<SpendReport> {
  return requestJson<SpendReport>(`${CATEGORIES_PATH}/spend${spendQuery(from, to)}`)
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
