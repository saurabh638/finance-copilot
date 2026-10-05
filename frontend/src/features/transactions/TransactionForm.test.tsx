import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
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
