import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Transaction, TransactionUpdate } from './api'
import TransactionEditor from './TransactionEditor'

const EXPENSE: Transaction = {
  id: 7,
  transaction_date: '2026-10-04',
  merchant: 'Blinkit',
  note: 'milk',
  source: 'manual',
  postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense' }],
}

const TRANSFER: Transaction = {
  id: 8,
  transaction_date: '2026-10-03',
  merchant: null,
  note: null,
  source: 'manual',
  postings: [
    { id: 10, account_id: 1, amount_paise: -100000, kind: 'transfer' },
    { id: 11, account_id: 2, amount_paise: 100000, kind: 'transfer' },
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
