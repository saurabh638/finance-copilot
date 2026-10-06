import { describe, expect, it } from 'vitest'

import type { Category } from './api'
import {
  NAME_MAX,
  blankDraft,
  childCount,
  draftPayload,
  editValues,
  moveTargets,
  nameProblem,
  updatePayload,
} from './manage'

/** A category as the API returns one. */
function category(
  id: number,
  name: string,
  kind: Category['kind'] = 'expense',
  parent_id: number | null = null,
): Category {
  return { id, name, kind, parent_id }
}

const TREE: Category[] = [
  category(1, 'Food & groceries'),
  category(2, 'Groceries', 'expense', 1),
  category(3, 'Eating out', 'expense', 1),
  category(4, 'Salary', 'income'),
]

describe('blankDraft', () => {
  it('starts as spending, at the top level, with nothing typed', () => {
    expect(blankDraft()).toEqual({ name: '', kind: 'expense', parent_id: '' })
  })
})

describe('draftPayload', () => {
  it('sends a top-level name with the kind it will hold', () => {
    expect(draftPayload({ name: '  Pets  ', kind: 'income', parent_id: '' })).toEqual({
      name: 'Pets',
      kind: 'income',
    })
  })

  it('sends a name under a branch with where it goes, and no kind of its own', () => {
    // A child carries its parent's kind, so sending one would be a second answer.
    expect(draftPayload({ name: 'Vet', kind: 'income', parent_id: '12' })).toEqual({
      name: 'Vet',
      parent_id: 12,
    })
  })
})

describe('nameProblem', () => {
  it('accepts a name that is free where it is going', () => {
    expect(nameProblem('Chemist', 1, TREE)).toBeNull()
  })

  it('accepts a name already used somewhere else in the tree', () => {
    expect(nameProblem('Groceries', null, TREE)).toBeNull()
  })

  it('asks for a name at all', () => {
    expect(nameProblem('   ', null, TREE)).toBe('A name is required')
  })

  it('keeps the name inside the column size', () => {
    expect(nameProblem('x'.repeat(NAME_MAX + 1), null, TREE)).toBe(
      `Keep the name under ${NAME_MAX} characters`,
    )
  })

  it('refuses a name already used among its siblings, as the server does', () => {
    expect(nameProblem('Groceries', 1, TREE)).toBe('Groceries is already used here')
  })

  it('refuses a name already used at the top level when that is where it goes', () => {
    expect(nameProblem('Salary', null, TREE)).toBe('Salary is already used here')
  })

  it('lets a name keep its own place while it is renamed to itself', () => {
    expect(nameProblem('Groceries', 1, TREE, 2)).toBeNull()
  })
})

describe('childCount', () => {
  it('counts the names filed under a branch', () => {
    expect(childCount(TREE, 1)).toBe(2)
  })

  it('counts nothing for a name that holds none', () => {
    expect(childCount(TREE, 4)).toBe(0)
  })
})

describe('moveTargets', () => {
  it('offers the other branches, not the one it already sits under', () => {
    expect(moveTargets(TREE, TREE[1]).map((row) => row.name)).toEqual(['Salary'])
  })

  it('does not offer the branch a name is already under', () => {
    expect(moveTargets(TREE, TREE[2]).map((row) => row.name)).not.toContain('Food & groceries')
  })

  it('offers nothing for a branch that holds names, because it cannot be moved', () => {
    expect(moveTargets(TREE, TREE[0])).toEqual([])
  })

  it('offers nothing for a name that already stands on its own', () => {
    // Nothing but the top level is on offer, and it is already there.
    expect(moveTargets([TREE[3]], TREE[3])).toEqual([])
  })
})

describe('editValues and updatePayload', () => {
  it('opens on the name it has and where it is', () => {
    expect(editValues(TREE[1])).toEqual({ name: 'Groceries', place: '' })
  })

  it('sends nothing at all when nothing was touched', () => {
    expect(updatePayload(editValues(TREE[1]), TREE[1])).toEqual({})
  })

  it('sends a new name, trimmed', () => {
    expect(updatePayload({ name: '  Fruit & veg  ', place: '' }, TREE[1])).toEqual({
      name: 'Fruit & veg',
    })
  })

  it('moves a name with the branch it was sent to', () => {
    expect(updatePayload({ name: 'Groceries', place: '4' }, TREE[1])).toEqual({ parent_id: 4 })
  })

  it('moves a name out to the top level with an explicit null', () => {
    expect(updatePayload({ name: 'Groceries', place: 'top' }, TREE[1])).toEqual({ parent_id: null })
  })

  it('keeps the name where it is when the place was left alone', () => {
    expect(updatePayload({ name: 'Fruit & veg', place: '' }, TREE[1])).toEqual({
      name: 'Fruit & veg',
    })
  })
})
