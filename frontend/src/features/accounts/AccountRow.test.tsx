import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account } from './api'
import AccountRow from './AccountRow'
import { fetchBalance } from './api'

vi.mock('./api')

const SAVINGS: Account = {
  id: 1,
  name: 'SBI',
  type: 'savings',
  purpose: null,
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

function renderRow(account: Account, parentName?: string, isEditing = false, isChecking = false) {
  const onEdit = vi.fn()
  const onCheck = vi.fn()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <ul>
        <AccountRow
          account={account}
          parentName={parentName}
          isEditing={isEditing}
          onEdit={onEdit}
          isChecking={isChecking}
          onCheck={onCheck}
        >
          {isEditing && <p>editor</p>}
        </AccountRow>
      </ul>
    </QueryClientProvider>,
  )
  return onEdit
}

describe('AccountRow', () => {
  beforeEach(() => {
    vi.mocked(fetchBalance).mockResolvedValue({
      account_id: 1,
      as_of: null,
      opening_balance_paise: 12_345_678,
      postings_paise: 0,
      balance_paise: 12_345_678,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the name, the balance worked out from its movements, and the settings', async () => {
    renderRow(SAVINGS)

    expect(screen.getByText('SBI')).toBeInTheDocument()
    expect(await screen.findByText('₹1,23,456.78')).toBeInTheDocument()
    expect(screen.getByText(/Opening .* \+ movements/)).toBeInTheDocument()
    expect(screen.getByText(/Savings · Statement import · from 2026-04-01/)).toBeInTheDocument()
  })

  it('offers the two things a row can do, and says which is open', () => {
    renderRow(SAVINGS, undefined, true, true)

    expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel check' })).toBeInTheDocument()
  })

  it('offers a balance check when one is not open', () => {
    renderRow(SAVINGS)

    expect(screen.getByRole('button', { name: 'Check balance' })).toBeInTheDocument()
  })

  it('names the parent of a pot', () => {
    renderRow({ ...SAVINGS, id: 2, name: 'Goa trip', type: 'pot', parent_id: 1 }, 'SBI')

    expect(screen.getByText(/part of SBI/)).toBeInTheDocument()
  })

  it('shows the card days only for a credit card', () => {
    renderRow({ ...SAVINGS, type: 'credit_card', statement_day: 5, due_day: 20 })

    expect(screen.getByText(/Statement day 5, due day 20/)).toBeInTheDocument()
  })

  it('says when an account is not active', () => {
    renderRow({ ...SAVINGS, is_active: false })

    expect(screen.getByText('Not active')).toBeInTheDocument()
  })

  it('asks to open the editor, and shows it when open', () => {
    const onEdit = renderRow(SAVINGS)

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))

    expect(onEdit).toHaveBeenCalled()
    expect(screen.queryByText('editor')).not.toBeInTheDocument()

    renderRow(SAVINGS, undefined, true)
    expect(screen.getAllByText('editor')[0]).toBeInTheDocument()
  })

  it('offers to close instead of edit while the editor is open', () => {
    renderRow(SAVINGS, undefined, true)

    expect(screen.getAllByRole('button', { name: 'Close' })[0]).toBeInTheDocument()
  })
})
