import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Category } from './api'
import CategoryPicker from './CategoryPicker'

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
  category(3, 'Salary', 'income'),
  category(4, 'Unaccounted for spending', 'adjustment'),
  category(5, 'Unrecorded income', 'adjustment'),
]

function renderPicker(kind: Category['kind'] = 'expense', onChange = vi.fn()) {
  render(
    <CategoryPicker
      id="movement-category"
      label="Category (optional)"
      categories={TREE}
      kind={kind}
      value=""
      onChange={onChange}
    />,
  )
  return screen.getByLabelText('Category (optional)')
}

/** The options as a person reads them. */
function optionsText(select: HTMLElement): string[] {
  return Array.from(select.querySelectorAll('option')).map((option) => option.textContent ?? '')
}

describe('CategoryPicker', () => {
  it('offers no category at all, first', () => {
    expect(optionsText(renderPicker())).toEqual([
      'No category',
      'Food & groceries',
      'Food & groceries · Groceries',
    ])
  })

  it('offers the names of the kind the movement is', () => {
    expect(optionsText(renderPicker('income'))).toEqual(['No category', 'Salary'])
  })

  it('never offers a write-off name', () => {
    const shown = optionsText(renderPicker())

    expect(shown).not.toContain('Unaccounted for spending')
    expect(shown).not.toContain('Unrecorded income')
  })

  it('says which name was chosen, as the id in text', () => {
    const onChange = vi.fn()
    const select = renderPicker('expense', onChange)

    fireEvent.change(select, { target: { value: '2' } })

    expect(onChange).toHaveBeenCalledWith('2')
  })

  it('shows the server’s refusal beside the field when one is given', () => {
    render(
      <CategoryPicker
        id="split-category-0"
        label="Part 1 category"
        categories={TREE}
        kind="expense"
        value="2"
        error="Groceries is for spending, not earning"
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('Part 1 category')).toHaveValue('2')
    expect(screen.getByText('Groceries is for spending, not earning')).toBeInTheDocument()
  })
})
