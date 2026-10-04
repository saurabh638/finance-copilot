import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AccountForm from './AccountForm'
import type { Account } from './api'
import type { NewAccount } from './useAccounts'

const SAVINGS: Account = {
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

interface RenderOptions {
  onSubmit: (payload: NewAccount) => void
  parents?: Account[]
  errorMessage?: string | null
}

function renderForm({ onSubmit, parents = [SAVINGS], errorMessage = null }: RenderOptions) {
  render(
    <AccountForm
      parents={parents}
      onSubmit={onSubmit}
      isSaving={false}
      errorMessage={errorMessage}
    />,
  )
}

function fillStandardFields() {
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'HDFC' } })
  fireEvent.change(screen.getByLabelText('Opening balance'), {
    target: { value: '1,23,456.78' },
  })
  fireEvent.change(screen.getByLabelText('Opening date'), { target: { value: '2026-04-01' } })
}

function submit() {
  fireEvent.click(screen.getByRole('button', { name: 'Add account' }))
}

describe('AccountForm', () => {
  it('sends the exact paise the user typed, and no rate', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    fillStandardFields()

    submit()

    const payload = onSubmit.mock.calls[0]?.[0]
    expect(payload?.account.opening_balance_paise).toBe(12_345_678)
    expect(payload?.account.name).toBe('HDFC')
    expect(payload?.account.type).toBe('savings')
    expect(payload?.rate).toBeNull()
  })

  it('refuses three decimal places and does not submit', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    fillStandardFields()
    fireEvent.change(screen.getByLabelText('Opening balance'), { target: { value: '10.005' } })

    submit()

    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('requires a name', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    fireEvent.change(screen.getByLabelText('Opening balance'), { target: { value: '500' } })
    fireEvent.change(screen.getByLabelText('Opening date'), { target: { value: '2026-04-01' } })

    submit()

    expect(screen.getByText('A name is required')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('asks for statement and due day only for a credit card', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    expect(screen.queryByLabelText('Statement day')).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Type'), { target: { value: 'credit_card' } })
    fillStandardFields()
    fireEvent.change(screen.getByLabelText('Statement day'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Due day'), { target: { value: '20' } })
    submit()

    const payload = onSubmit.mock.calls[0]?.[0]
    expect(payload?.account.statement_day).toBe(5)
    expect(payload?.account.due_day).toBe(20)
  })

  it('refuses a card day outside 1 to 31', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    fireEvent.change(screen.getByLabelText('Type'), { target: { value: 'credit_card' } })
    fillStandardFields()
    fireEvent.change(screen.getByLabelText('Statement day'), { target: { value: '32' } })

    submit()

    expect(screen.getByText('Use a day between 1 and 31')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('asks for a parent only for a pot, and requires it', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    fireEvent.change(screen.getByLabelText('Type'), { target: { value: 'pot' } })
    fillStandardFields()

    submit()

    expect(screen.getByText('A pot needs a parent account')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Parent account'), { target: { value: '1' } })
    submit()

    expect(onSubmit.mock.calls[0]?.[0]?.account.parent_id).toBe(1)
  })

  it('sends an optional rate and its frequency', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    fillStandardFields()
    fireEvent.change(screen.getByLabelText('Interest rate % a year'), {
      target: { value: '7.1' },
    })
    fireEvent.change(screen.getByLabelText('Interest credited'), { target: { value: 'monthly' } })

    submit()

    expect(onSubmit.mock.calls[0]?.[0]?.rate).toEqual({ rate: '7.1', frequency: 'monthly' })
  })

  it('refuses a rate with five decimal places', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit })
    fillStandardFields()
    fireEvent.change(screen.getByLabelText('Interest rate % a year'), {
      target: { value: '7.12345' },
    })

    submit()

    expect(screen.getByText('Use up to four decimals, like 7.1000')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows the error the server sent', () => {
    const onSubmit = vi.fn<(payload: NewAccount) => void>()
    renderForm({ onSubmit, errorMessage: 'a pot cannot be the parent of another pot' })

    expect(screen.getByRole('alert')).toHaveTextContent('a pot cannot be the parent of another pot')
  })
})
