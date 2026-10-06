/**
 * The tree, read the way a screen needs it.
 *
 * The API returns a flat list; every screen wants branches with their children
 * under them, or the names a movement of a given kind may be filed under. That
 * is pure work over the list, so it is tested here rather than through a browser.
 */

import type { Category, CategoryKind } from './api'

/** Separates a branch from the name filed under it: `Food & groceries · Milk`. */
export const PATH_SEPARATOR = ' · '

/** One branch and the names filed under it. */
export interface CategoryBranch {
  category: Category
  children: Category[]
}

/**
 * The branches in the order the API lists them, each with its own children.
 *
 * A name whose branch was removed is still live and money may be filed under it,
 * so it is shown as a name of its own at the end rather than hidden.
 */
export function buildTree(categories: Category[]): CategoryBranch[] {
  const children = new Map<number, Category[]>()
  for (const row of categories) {
    if (row.parent_id !== null) {
      children.set(row.parent_id, [...(children.get(row.parent_id) ?? []), row])
    }
  }

  const tree: CategoryBranch[] = categories
    .filter((row) => row.parent_id === null)
    .map((category) => ({ category, children: children.get(category.id) ?? [] }))

  const placed = new Set(tree.flatMap((branch) => [branch.category, ...branch.children]))
  for (const row of categories) {
    if (!placed.has(row)) {
      tree.push({ category: row, children: [] })
    }
  }
  return tree
}

/**
 * The categories a movement of this kind may be filed under, branch then child.
 *
 * A branch is offered as well as the names under it, because spending can be
 * filed under either. The write-off names are never offered: they belong to a
 * balance check, and the server refuses one offered by hand.
 */
export function pickable(categories: Category[], kind: CategoryKind): Category[] {
  return buildTree(categories).flatMap((branch) =>
    branch.category.kind === kind
      ? [branch.category, ...branch.children.filter((child) => child.kind === kind)]
      : [],
  )
}

/**
 * What a category reads as, with its branch in front when it is not a branch.
 *
 * Null means there is nothing to show: no category, or one that is no longer in
 * the tree, which a movement recorded earlier may still point at.
 */
export function categoryLabel(categories: Category[], categoryId: number | null): string | null {
  if (categoryId === null) {
    return null
  }

  const found = categories.find((row) => row.id === categoryId)
  if (found === undefined) {
    return null
  }

  const branch = categories.find((row) => row.id === found.parent_id)
  return branch === undefined ? found.name : `${branch.name}${PATH_SEPARATOR}${found.name}`
}
