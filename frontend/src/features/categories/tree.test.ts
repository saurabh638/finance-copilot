import { describe, expect, it } from 'vitest'

import type { Category } from './api'
import { buildTree, categoryLabel, pickable } from './tree'

/** A category as the API returns one. */
function category(
  id: number,
  name: string,
  kind: Category['kind'] = 'expense',
  parent_id: number | null = null,
): Category {
  return { id, name, kind, parent_id }
}

/** Food & groceries with Groceries under it, standing on its own. */
const TREE: Category[] = [
  category(1, 'Food & groceries'),
  category(2, 'Groceries', 'expense', 1),
  category(3, 'Eating out', 'expense', 1),
  category(4, 'Salary', 'income'),
]

describe('buildTree', () => {
  it('is empty when there are no categories', () => {
    expect(buildTree([])).toEqual([])
  })

  it('puts each name under its branch, in the order given', () => {
    expect(buildTree(TREE)).toEqual([
      { category: TREE[0], children: [TREE[1], TREE[2]] },
      { category: TREE[3], children: [] },
    ])
  })

  it('shows a name whose branch is gone as a name of its own, at the end', () => {
    const orphan = category(5, 'Chemist', 'expense', 99)

    const tree = buildTree([...TREE, orphan])

    expect(tree[tree.length - 1]).toEqual({ category: orphan, children: [] })
    expect(tree).toHaveLength(3)
  })

  it('keeps a name that is its own branch at the top level', () => {
    const lonely = category(6, 'Rent')

    const tree = buildTree([lonely])

    expect(tree).toEqual([{ category: lonely, children: [] }])
  })
})

describe('pickable', () => {
  it('offers the branch and the names under it, branch first', () => {
    expect(pickable(TREE, 'expense').map((row) => row.name)).toEqual([
      'Food & groceries',
      'Groceries',
      'Eating out',
    ])
  })

  it('offers only the kind asked for', () => {
    expect(pickable(TREE, 'income').map((row) => row.name)).toEqual(['Salary'])
  })

  it('never offers the write-off names', () => {
    const tree = [
      ...TREE,
      category(7, 'Unaccounted for spending', 'adjustment'),
      category(8, 'Unrecorded income', 'adjustment'),
    ]

    const offered = [...pickable(tree, 'expense'), ...pickable(tree, 'income')]

    expect(offered.map((row) => row.name)).not.toContain('Unaccounted for spending')
    expect(offered.map((row) => row.name)).not.toContain('Unrecorded income')
  })

  it('offers a name whose branch is gone', () => {
    const orphan = category(5, 'Chemist', 'expense', 99)

    expect(pickable([...TREE, orphan], 'expense').map((row) => row.name)).toContain('Chemist')
  })
})

describe('categoryLabel', () => {
  it('reads a name with its branch in front', () => {
    expect(categoryLabel(TREE, 2)).toBe('Food & groceries · Groceries')
  })

  it('reads a branch on its own', () => {
    expect(categoryLabel(TREE, 1)).toBe('Food & groceries')
  })

  it('has nothing to show when there is no category', () => {
    expect(categoryLabel(TREE, null)).toBeNull()
  })

  it('has nothing to show for a category that is no longer in the tree', () => {
    expect(categoryLabel(TREE, 404)).toBeNull()
  })

  it('reads a name whose branch is gone without a branch', () => {
    const orphan = category(5, 'Chemist', 'expense', 99)

    expect(categoryLabel([...TREE, orphan], 5)).toBe('Chemist')
  })
})
