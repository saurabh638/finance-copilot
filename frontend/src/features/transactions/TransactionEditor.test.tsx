import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Category } from '../categories/api'
import type { Transaction, TransactionUpdate } from './api'
import TransactionEditor from './TransactionEditor'

const EXPENSE: Transaction = {
  id: 7,
  transaction_date: '2026-10-04',
  merchant: 'Blinkit',
  note: 'milk',
  source: 'manual',
  postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense', category_id: null }],
}

const TRANSFER: Transaction = {
  id: 8,
  transaction_date: '2026-10-03',
  merchant: null,
  note: null,
  source: 'manual',
  postings: [
    { id: 10, account_id: 1, amount_paise: -100000, kind: 'transfer', category_id: null },
    { id: 11, account_id: 2, amount_paise: 100000, kind: 'transfer', category_id: null },
  ],
}

const CATEGORIES: Category[] = [
  { id: 10, name: 'Food & groceries', kind: 'expense', parent_id: null },
  { id: 11, name: 'Groceries', kind: 'expense', parent_id: 10 },
]

/** The same movement, filed under the category given. */
function filed(category_id: number | null): Transaction {
  return {
    ...EXPENSE,
    postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense', category_id }],
  }
}

/** A ₹500 shop filed as ₹300 of groceries and ₹200 of the branch itself. */
const SPLIT: Transaction = {
  id: 12,
  transaction_date: '2026-10-04',
  merchant: 'Big Bazaar',
  note: null,
  source: 'manual',
  postings: [
    { id: 13, account_id: 1, amount_paise: -30000, kind: 'expense', category_id: 11 },
    { id: 14, account_id: 1, amount_paise: -20000, kind: 'expense', category_id: 10 },
  ],
}

interface RenderOptions {
  transaction?: Transaction
  isSaving?: boolean
  errorMessage?: string | null
}

function renderEditor({
  transaction = EXPENSE,
  isSaving = false,
  errorMessage = null,
}: RenderOptions = {}) {
  const onSave = vi.fn<(update: TransactionUpdate) => void>()
  render(
    <TransactionEditor
      transaction={transaction}
      categories={CATEGORIES}
      onSave={onSave}
      isSaving={isSaving}
      errorMessage={errorMessage}
    />,
  )
  return onSave
}

describe('TransactionEditor', () => {
  it('opens with what the movement already says', () => {
    renderEditor()

    expect(screen.getByLabelText('Amount')).toHaveValue('₹500.00')
    expect(screen.getByLabelText('Merchant (optional)')).toHaveValue('Blinkit')
    expect(screen.getByLabelText('Note (optional)')).toHaveValue('milk')
    expect(screen.getByLabelText('Date')).toHaveValue('2026-10-04')
  })

  it('will not save what nobody changed', () => {
    renderEditor()

    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled()
  })

  it('sends only the field that changed', () => {
    const onSave = renderEditor()

    fireEvent.change(screen.getByLabelText('Note (optional)'), { target: { value: 'bread' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(onSave).toHaveBeenCalledWith({ note: 'bread' })
  })

  it('sends a corrected amount as exact paise', () => {
    const onSave = renderEditor()

    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '1,234.56' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(onSave).toHaveBeenCalledWith({ amount_paise: 123456 })
  })

  it('refuses an amount that is not money, and sends nothing', () => {
    const onSave = renderEditor()

    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '10.005' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
  })

  it('asks for money in the amount field when it can be corrected', () => {
    renderEditor()

    expect(screen.getByLabelText('Amount')).toBeEnabled()
  })

  it('opens with the category the movement is filed under', () => {
    renderEditor({ transaction: filed(11) })

    expect(screen.getByLabelText('Category (optional)')).toHaveValue('11')
  })

  it('files a movement under a category, or unfiles it, and only when that changed', () => {
    const onSave = renderEditor()

    fireEvent.change(screen.getByLabelText('Category (optional)'), { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(onSave).toHaveBeenCalledWith({ category_id: 10 })
  })

  it('unfiles a movement with an explicit null', () => {
    const onSave = renderEditor({ transaction: filed(11) })

    fireEvent.change(screen.getByLabelText('Category (optional)'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(onSave).toHaveBeenCalledWith({ category_id: null })
  })

  it('shows a split’s parts but offers no picker for them', () => {
    renderEditor({ transaction: SPLIT })

    expect(screen.getByLabelText('Amount')).toHaveValue('₹500.00')
    expect(screen.queryByLabelText('Category (optional)')).not.toBeInTheDocument()
    expect(screen.getByText(/its parts are the filing/)).toBeInTheDocument()
    expect(screen.getByText(/^Filed under:/)).toBeInTheDocument()
    expect(screen.getByText(/Food & groceries · Groceries/)).toBeInTheDocument()
  })

  it('says a transfer is filed under nothing', () => {
    renderEditor({ transaction: TRANSFER })

    expect(screen.queryByLabelText('Category (optional)')).not.toBeInTheDocument()
    expect(screen.getByText(/moves money without spending it/)).toBeInTheDocument()
  })

  it('shows a two-sided amount but will not let it be changed', () => {
    renderEditor({ transaction: TRANSFER })

    expect(screen.getByLabelText('Amount')).toBeDisabled()
    expect(screen.getByLabelText('Amount')).toHaveValue('₹1,000.00')
    expect(screen.getByText(/cannot be edited here/)).toBeInTheDocument()
  })

  it('still allows the date and the note of a two-sided movement', () => {
    const onSave = renderEditor({ transaction: TRANSFER })

    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-10-01' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(onSave).toHaveBeenCalledWith({ transaction_date: '2026-10-01' })
  })

  it('shows what the server said when a save is refused', () => {
    renderEditor({ errorMessage: 'SBI opened on 2026-04-01, so 2026-03-31 is too early' })

    expect(screen.getByRole('alert')).toHaveTextContent('SBI opened on 2026-04-01')
  })

  it('will not save twice while saving', () => {
    renderEditor({ isSaving: true })

    fireEvent.change(screen.getByLabelText('Note (optional)'), { target: { value: 'bread' } })

    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
  })
})
