import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Category } from '../categories/api'
import SplitEditor from './SplitEditor'
import type { MovementPart } from './parts'

const TREE: Category[] = [
  { id: 10, name: 'Food & groceries', kind: 'expense', parent_id: null },
  { id: 11, name: 'Groceries', kind: 'expense', parent_id: 10 },
  { id: 12, name: 'Eating out', kind: 'expense', parent_id: 10 },
]

/** The ₹500 shop that became ₹300 of groceries and ₹200 of eating out. */
const FILLED: MovementPart[] = [
  { amount: '300', category_id: '11' },
  { amount: '200', category_id: '12' },
]

function renderEditor(overrides: Partial<Parameters<typeof SplitEditor>[0]> = {}) {
  const onChange = vi.fn()
  render(
    <SplitEditor
      parts={FILLED}
      categories={TREE}
      kind="expense"
      remainingPaise={0}
      onChange={onChange}
      {...overrides}
    />,
  )
  return onChange
}

describe('SplitEditor', () => {
  it('shows a field for the amount and the category of each part', () => {
    renderEditor()

    expect(screen.getByLabelText('Part 1 amount')).toHaveValue('300')
    expect(screen.getByLabelText('Part 1 category')).toHaveValue('11')
    expect(screen.getByLabelText('Part 2 amount')).toHaveValue('200')
    expect(screen.getByLabelText('Part 2 category')).toHaveValue('12')
  })

  it('says the parts add up when nothing is left over', () => {
    renderEditor({ remainingPaise: 0 })

    expect(screen.getByRole('status')).toHaveTextContent('The parts add up')
  })

  it('says what is still to allocate', () => {
    renderEditor({ parts: [FILLED[0]], remainingPaise: 20000 })

    expect(screen.getByRole('status')).toHaveTextContent('₹200.00 still to allocate')
  })

  it('says when the parts ask for more than the amount', () => {
    renderEditor({ remainingPaise: -10000 })

    expect(screen.getByRole('status')).toHaveTextContent('₹100.00 too much')
  })

  it('asks for the amount first when there is not one yet', () => {
    renderEditor({ remainingPaise: null })

    expect(screen.getByRole('status')).toHaveTextContent('Enter the amount above first')
  })

  it('changes the amount of the part being typed in', () => {
    const onChange = renderEditor()

    fireEvent.change(screen.getByLabelText('Part 1 amount'), { target: { value: '350' } })

    expect(onChange).toHaveBeenCalledWith([
      { amount: '350', category_id: '11' },
      { amount: '200', category_id: '12' },
    ])
  })

  it('changes the category of the part it belongs to', () => {
    const onChange = renderEditor()

    fireEvent.change(screen.getByLabelText('Part 2 category'), { target: { value: '11' } })

    expect(onChange).toHaveBeenCalledWith([
      { amount: '300', category_id: '11' },
      { amount: '200', category_id: '11' },
    ])
  })

  it('adds an empty part', () => {
    const onChange = renderEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Add a part' }))

    expect(onChange).toHaveBeenCalledWith([...FILLED, { amount: '', category_id: '' }])
  })

  it('adds a part holding what is left over, so the parts can be made to add up', () => {
    const onChange = renderEditor({ parts: [FILLED[0]], remainingPaise: 20000 })

    fireEvent.click(screen.getByRole('button', { name: 'Add ₹200.00' }))

    expect(onChange).toHaveBeenCalledWith([
      { amount: '300', category_id: '11' },
      { amount: '₹200.00', category_id: '' },
    ])
  })

  it('offers no remainder button when there is none to allocate', () => {
    renderEditor({ remainingPaise: 0 })

    expect(screen.queryByRole('button', { name: /^Add ₹/ })).not.toBeInTheDocument()
  })

  it('removes a part, and only offers that past two parts', () => {
    const onChange = renderEditor({
      parts: [...FILLED, { amount: '100', category_id: '11' }],
    })

    fireEvent.click(screen.getByRole('button', { name: 'Remove part 2' }))

    expect(onChange).toHaveBeenCalledWith([FILLED[0], { amount: '100', category_id: '11' }])
  })

  it('offers no way to remove a part when two are left, because two is a split', () => {
    renderEditor()

    expect(screen.queryByRole('button', { name: /^Remove part/ })).not.toBeInTheDocument()
  })

  it('shows what is wrong with the parts', () => {
    renderEditor({ error: 'Every part needs a category' })

    expect(screen.getByRole('alert')).toHaveTextContent('Every part needs a category')
  })
})
