import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Transaction } from './api'
import TransactionRow from './TransactionRow'

const NAMES = new Map([
  [1, 'SBI'],
  [2, 'Central Bank'],
])

const EXPENSE: Transaction = {
  id: 7,
  transaction_date: '2026-10-04',
  merchant: 'Blinkit',
  note: null,
  source: 'manual',
  postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense', category_id: null }],
}

/** The same movement, filed under a category. */
const FILED: Transaction = {
  ...EXPENSE,
  postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense', category_id: 11 }],
}

interface RenderOptions {
  transaction?: Transaction
  isEditing?: boolean
  isDeleting?: boolean
  onEdit?: () => void
  onDelete?: () => void
  children?: React.ReactNode
}

/** The labels the page builds from the tree: id to `Branch · Name`. */
const FILINGS = new Map([[11, 'Food & groceries · Groceries']])

function renderRow({
  transaction = EXPENSE,
  isEditing = false,
  isDeleting = false,
  onEdit = vi.fn(),
  onDelete = vi.fn(),
  children,
}: RenderOptions = {}) {
  render(
    <ul>
      <TransactionRow
        transaction={transaction}
        names={NAMES}
        filingLabels={FILINGS}
        isEditing={isEditing}
        isDeleting={isDeleting}
        onEdit={onEdit}
        onDelete={onDelete}
      >
        {children}
      </TransactionRow>
    </ul>,
  )
  return { onEdit, onDelete }
}

describe('TransactionRow', () => {
  it('reads as one movement, in rupees', () => {
    renderRow()

    expect(screen.getByText('Blinkit')).toBeInTheDocument()
    expect(screen.getByText('4 Oct 2026 · Money out · SBI')).toBeInTheDocument()
    expect(screen.getByText('-₹500.00')).toBeInTheDocument()
  })

  it('says which category the movement was filed under', () => {
    renderRow({ transaction: FILED })

    expect(screen.getByText('Filed under Food & groceries · Groceries')).toBeInTheDocument()
  })

  it('says nothing about a filing when there is none', () => {
    renderRow()

    expect(screen.queryByText(/^Filed under/)).not.toBeInTheDocument()
  })

  it('asks before removing anything', () => {
    const { onDelete } = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onDelete).not.toHaveBeenCalled()
    expect(screen.getByText(/Remove this movement\?/)).toBeInTheDocument()
  })

  it('removes it only once the removal is confirmed', () => {
    const { onDelete } = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }))

    expect(onDelete).toHaveBeenCalledTimes(1)
  })

  it('backs out with nothing sent', () => {
    const { onDelete } = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onDelete).not.toHaveBeenCalled()
    expect(screen.queryByText(/Remove this movement\?/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
  })

  it('says the row is open, and offers to close it', () => {
    renderRow({ isEditing: true })

    expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument()
  })

  it('shows the editor underneath when one is given', () => {
    renderRow({ isEditing: true, children: <p>the editor</p> })

    expect(screen.getByText('the editor')).toBeInTheDocument()
  })

  it('cannot be edited or removed twice at once', () => {
    renderRow({ isDeleting: true })

    expect(screen.getByRole('button', { name: 'Edit' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled()
  })
})
