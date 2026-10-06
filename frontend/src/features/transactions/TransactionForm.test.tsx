import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
import type { Category } from '../categories/api'
import type { MovementCreate } from './api'
import TransactionForm from './TransactionForm'

const SBI: Account = {
  id: 1,
  name: 'SBI',
  type: 'savings',
  purpose: null,
  capture_mode: 'statement_import',
  parent_id: null,
  opening_balance_paise: 0,
  opening_date: '2026-04-01',
  statement_day: null,
  due_day: null,
  is_active: true,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

const CENTRAL: Account = { ...SBI, id: 2, name: 'Central Bank' }

/** The tree the form is given: one branch with a name under it, and one income. */
const CATEGORIES: Category[] = [
  { id: 10, name: 'Food & groceries', kind: 'expense', parent_id: null },
  { id: 11, name: 'Groceries', kind: 'expense', parent_id: 10 },
  { id: 12, name: 'Salary', kind: 'income', parent_id: null },
]

interface RenderOptions {
  onSubmit?: (payload: MovementCreate) => void
  isSaving?: boolean
  errorMessage?: string | null
}

function renderForm({
  onSubmit = vi.fn<(payload: MovementCreate) => void>(),
  isSaving = false,
  errorMessage = null,
}: RenderOptions = {}) {
  render(
    <TransactionForm
      accounts={[SBI, CENTRAL]}
      categories={CATEGORIES}
      today="2026-10-04"
      onSubmit={onSubmit}
      isSaving={isSaving}
      errorMessage={errorMessage}
    />,
  )
  return onSubmit
}

function type(field: string, value: string) {
  fireEvent.change(screen.getByLabelText(field), { target: { value } })
}

function submit() {
  fireEvent.click(screen.getByRole('button', { name: /Record/ }))
}

describe('TransactionForm', () => {
  it('opens on today, as an expense, with both accounts to choose from', () => {
    renderForm()

    expect(screen.getByLabelText('Date')).toHaveValue('2026-10-04')
    expect(screen.getByLabelText('Direction')).toHaveValue('expense')
    expect(screen.getByLabelText('Account').textContent).toContain('SBI')
    expect(screen.getByLabelText('Account').textContent).toContain('Central Bank')
  })

  it('records an expense with the exact paise the user typed', () => {
    const onSubmit = renderForm()
    type('Amount', '1,234.56')
    type('Account', '1')
    type('Merchant (optional)', '  Blinkit ')
    type('Note (optional)', 'milk')

    submit()

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 1,
      amount_paise: 123456,
      transaction_date: '2026-10-04',
      merchant: 'Blinkit',
      note: 'milk',
    })
  })

  it('offers both sides of a transfer and asks for no merchant', () => {
    renderForm()

    type('Direction', 'transfer')

    expect(screen.getByLabelText('From account')).toBeInTheDocument()
    expect(screen.getByLabelText('To account')).toBeInTheDocument()
    expect(screen.queryByLabelText('Account')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Merchant (optional)')).not.toBeInTheDocument()
  })

  it('offers the category tree for money spent, a branch and the name under it', () => {
    renderForm()

    const options = Array.from(
      screen.getByLabelText('Category (optional)').querySelectorAll('option'),
    )

    expect(options.map((option) => option.textContent)).toEqual([
      'No category',
      'Food & groceries',
      'Food & groceries · Groceries',
    ])
  })

  it('files the movement under the category chosen', () => {
    const onSubmit = renderForm()
    type('Amount', '500')
    type('Account', '1')
    type('Category (optional)', '11')

    submit()

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 1,
      amount_paise: 50000,
      transaction_date: '2026-10-04',
      category_id: 11,
      merchant: null,
      note: null,
    })
  })

  it('records a movement with no category when none was chosen', () => {
    const onSubmit = vi.fn<(payload: MovementCreate) => void>()
    renderForm({ onSubmit })
    type('Amount', '500')
    type('Account', '1')

    submit()

    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty('category_id')
  })

  it('offers no category for a transfer', () => {
    renderForm()

    type('Direction', 'transfer')

    expect(screen.queryByLabelText('Category (optional)')).not.toBeInTheDocument()
  })

  it('offers no split for a transfer', () => {
    renderForm()

    type('Direction', 'transfer')

    expect(
      screen.queryByLabelText('Split this amount between several categories'),
    ).not.toBeInTheDocument()
  })

  it('swaps the single category for the parts when the split mode is turned on', () => {
    renderForm()

    expect(screen.getByLabelText('Category (optional)')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Split this amount between several categories'))

    expect(screen.queryByLabelText('Category (optional)')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Part 1 amount')).toBeInTheDocument()
    expect(screen.getByLabelText('Part 2 category')).toBeInTheDocument()
  })

  it('records one amount split between the categories it was filed under', () => {
    const onSubmit = vi.fn<(payload: MovementCreate) => void>()
    renderForm({ onSubmit })
    type('Amount', '500')
    type('Account', '1')
    fireEvent.click(screen.getByLabelText('Split this amount between several categories'))
    type('Part 1 amount', '300')
    type('Part 1 category', '11')
    type('Part 2 amount', '200')
    type('Part 2 category', '10')

    submit()

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 1,
      amount_paise: 50000,
      transaction_date: '2026-10-04',
      merchant: null,
      note: null,
      parts: [
        { amount_paise: 30000, category_id: 11 },
        { amount_paise: 20000, category_id: 10 },
      ],
    })
  })

  it('refuses a split whose parts do not add up, and sends nothing', () => {
    const onSubmit = vi.fn<(payload: MovementCreate) => void>()
    renderForm({ onSubmit })
    type('Amount', '500')
    type('Account', '1')
    fireEvent.click(screen.getByLabelText('Split this amount between several categories'))
    type('Part 1 amount', '300')
    type('Part 1 category', '11')
    type('Part 2 amount', '100')
    type('Part 2 category', '10')

    submit()

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The parts must add up to ₹500.00; ₹100.00 is still to allocate',
    )
  })

  it('offers earning names once the direction is money received', () => {
    renderForm()

    type('Direction', 'income')
    const options = Array.from(
      screen.getByLabelText('Category (optional)').querySelectorAll('option'),
    )

    expect(options.map((option) => option.textContent)).toEqual(['No category', 'Salary'])
  })

  it('sends a transfer as two accounts', () => {
    const onSubmit = renderForm()
    type('Direction', 'transfer')
    type('Amount', '1000')
    type('From account', '1')
    type('To account', '2')

    submit()

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'transfer',
      from_account_id: 1,
      to_account_id: 2,
      amount_paise: 100000,
      transaction_date: '2026-10-04',
      merchant: null,
      note: null,
    })
  })

  it('refuses money that is not money, and sends nothing', () => {
    const onSubmit = renderForm()
    type('Amount', 'abc')
    type('Account', '1')

    submit()

    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('refuses zero and a negative amount', () => {
    renderForm()
    type('Amount', '0')
    type('Account', '1')
    submit()
    expect(screen.getByText('The amount must be more than zero')).toBeInTheDocument()

    type('Amount', '-500')
    submit()
    expect(screen.getByText('The amount must be more than zero')).toBeInTheDocument()
  })

  it('refuses an expense with no account', () => {
    const onSubmit = renderForm()
    type('Amount', '500')

    submit()

    expect(screen.getByText('Pick an account')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('refuses a transfer into the account the money came from', () => {
    const onSubmit = renderForm()
    type('Direction', 'transfer')
    type('Amount', '500')
    type('From account', '1')
    type('To account', '1')

    submit()

    expect(screen.getByText('Pick two different accounts')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows what the server said when a save fails', () => {
    renderForm({ errorMessage: 'Account 9 does not exist or is no longer in use' })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Account 9 does not exist or is no longer in use',
    )
  })

  it('will not submit twice while saving', () => {
    const onSubmit = renderForm({ isSaving: true })

    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
