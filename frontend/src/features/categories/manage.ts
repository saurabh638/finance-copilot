/**
 * The rules for editing the tree, as pure functions.
 *
 * The server holds the same rules and refuses what breaks them; these are here so
 * a screen can say what is wrong before a request is sent, and so the wording is
 * the same whichever side refuses.
 */

import type { Category, CategoryCreate, CategoryKind, CategoryUpdate } from './api'

/** The name size the server holds, mirrored so the form can say it first. */
export const NAME_MAX = 80

/** What the form holds while a name is being added. Every value is text. */
export interface CategoryDraft {
  name: string
  /** Only used for a top-level name; a child carries its parent's kind. */
  kind: CategoryKind
  /** The branch to sit under, or empty text for a top-level name of its own. */
  parent_id: string
}

/** The kinds a name can be created as. Write-off names are not offered by hand. */
export const DRAFT_KINDS: CategoryKind[] = ['expense', 'income']

export const DRAFT_KIND_LABELS: Record<CategoryKind, string> = {
  expense: 'Spending',
  income: 'Earning',
  adjustment: 'Write-offs',
}

/** An empty form: spending, at the top level, with nothing typed. */
export function blankDraft(): CategoryDraft {
  return { name: '', kind: 'expense', parent_id: '' }
}

/** The payload for the API, with the name trimmed as the server trims it. */
export function draftPayload(draft: CategoryDraft): CategoryCreate {
  const name = draft.name.trim()
  if (draft.parent_id === '') {
    return { name, kind: draft.kind }
  }
  // A child carries its parent's kind, so sending one would be a second answer.
  return { name, parent_id: Number(draft.parent_id) }
}

/** The names filed directly under a category. */
export function childCount(categories: Category[], categoryId: number): number {
  return categories.filter((row) => row.parent_id === categoryId).length
}

/**
 * What is wrong with a name, or null when it can be used.
 *
 * The rules are the server's: a name is needed, it has to fit the column, and it
 * has to be free among the names it will sit beside. `ignoringId` is the category
 * being renamed, so changing nothing about its name is not a clash with itself.
 */
export function nameProblem(
  name: string,
  parentId: number | null,
  categories: Category[],
  ignoringId?: number,
): string | null {
  const cleaned = name.trim()
  if (cleaned === '') {
    return 'A name is required'
  }
  if (cleaned.length > NAME_MAX) {
    return `Keep the name under ${NAME_MAX} characters`
  }

  const clash = categories.some(
    (row) =>
      row.id !== ignoringId &&
      row.parent_id === parentId &&
      row.name.toLowerCase() === cleaned.toLowerCase(),
  )
  return clash ? `${cleaned} is already used here` : null
}

/**
 * The branches a category may be moved under, other than the one it is already in.
 *
 * A branch that holds names cannot be moved at all: its children would be left
 * behind, and the server refuses it. A name that already stands on its own has
 * nowhere else to go, so it is offered nothing; the caller adds the top level to
 * what comes back, because a name that sits under a branch may always go up.
 */
export function moveTargets(categories: Category[], category: Category): Category[] {
  if (category.parent_id === null) {
    return []
  }

  return categories.filter(
    (row) => row.parent_id === null && row.id !== category.parent_id && row.id !== category.id,
  )
}

/** What the editor holds while a name is being changed. */
export interface CategoryEditValues {
  name: string
  /** `''` leaves the name where it is, `'top'` moves it out, and an id moves it. */
  place: string
}

/** The editor as it opens for a category. */
export function editValues(category: Category): CategoryEditValues {
  return { name: category.name, place: '' }
}

/**
 * The change to send: only what differs from the category as it stands.
 *
 * The API leaves an omitted field alone, so `parent_id: null` is the only way to
 * say "move it out to the top level"; leaving the place alone sends nothing.
 */
export function updatePayload(values: CategoryEditValues, category: Category): CategoryUpdate {
  const update: CategoryUpdate = {}

  const name = values.name.trim()
  if (name !== category.name) {
    update.name = name
  }

  if (values.place === 'top') {
    update.parent_id = null
  } else if (values.place !== '') {
    update.parent_id = Number(values.place)
  }

  return update
}
