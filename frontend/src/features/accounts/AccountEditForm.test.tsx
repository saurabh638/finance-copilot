import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account, AccountUpdate } from './api'
import AccountEditForm from './AccountEditForm'

const SAVINGS: Account = {
  id: 1,
  name: 'SBI',
  alias: null,
  type: 'savings',
  purpose: 'salary',
  capture_mode: 'statement_import',
  parent_id: null,
  opening_balance_paise: 12_345_678,
  opening_date: '2026-04-01',
  statement_day: null,
  due_day: null,
  is_active: true,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

interface RenderOptions {
  onSubmit: (update: AccountUpdate) => void
  onCancel?: () => void
  account?: Account
  errorMessage?: string | null
}

function renderForm({
  onSubmit,
  onCancel = vi.fn(),
  account = SAVINGS,
  errorMessage = null,
}: RenderOptions) {
  render(
    <AccountEditForm
      account={account}
      parents={[SAVINGS]}
      onSubmit={onSubmit}
      onCancel={onCancel}
      isSaving={false}
      errorMessage={errorMessage}
    />,
  )
}

describe('AccountEditForm', () => {
  it('starts from what the account already holds', () => {
    renderForm({ onSubmit: vi.fn() })

    expect(screen.getByLabelText('Name')).toHaveValue('SBI')
    expect(screen.getByLabelText('Opening balance')).toHaveValue('₹1,23,456.78')
    expect(screen.getByLabelText('Purpose (optional)')).toHaveValue('salary')
    expect(screen.getByLabelText('Opening date')).toHaveValue('2026-04-01')
  })

  it('shows the type as fixed, with no way to change it', () => {
    renderForm({ onSubmit: vi.fn() })

    expect(screen.queryByRole('combobox', { name: 'Type' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Type')).toHaveValue('Savings')
    expect(screen.getByText('A type cannot change once the account exists.')).toBeInTheDocument()
  })

  it('sends the changed fields as paise, and never a type', () => {
    const onSubmit = vi.fn<(update: AccountUpdate) => void>()
    renderForm({ onSubmit })

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'SBI salary' } })
    fireEvent.change(screen.getByLabelText('Opening balance'), { target: { value: '2,00,000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    const update = onSubmit.mock.calls[0]?.[0]
    expect(update?.name).toBe('SBI salary')
    expect(update?.opening_balance_paise).toBe(20_000_000)
    expect(Object.keys(update ?? {})).not.toContain('type')
  })

  it('sends the account as no longer in use when the box is cleared', () => {
    const onSubmit = vi.fn<(update: AccountUpdate) => void>()
    renderForm({ onSubmit })

    fireEvent.click(screen.getByLabelText('In active use'))
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(onSubmit.mock.calls[0]?.[0].is_active).toBe(false)
  })

  it('refuses a malformed amount and does not submit', () => {
    const onSubmit = vi.fn<(update: AccountUpdate) => void>()
    renderForm({ onSubmit })

    fireEvent.change(screen.getByLabelText('Opening balance'), { target: { value: '10.005' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('asks for a parent when a pot has none, and offers only non-pots', () => {
    const onSubmit = vi.fn<(update: AccountUpdate) => void>()
    renderForm({ onSubmit, account: { ...SAVINGS, id: 2, name: 'Goa trip', type: 'pot' } })

    fireEvent.change(screen.getByLabelText('Parent account'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(screen.getByText('A pot needs a parent account')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('stops editing when Cancel is pressed', () => {
    const onCancel = vi.fn()
    renderForm({ onSubmit: vi.fn(), onCancel })

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalled()
  })

  it('shows the error the server sent', () => {
    renderForm({ onSubmit: vi.fn(), errorMessage: 'Account 1 does not exist' })

    expect(screen.getByRole('alert')).toHaveTextContent('Account 1 does not exist')
  })
})
