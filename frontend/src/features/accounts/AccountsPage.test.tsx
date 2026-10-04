import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchSession } from '../../lib/api'
import AccountsPage from './AccountsPage'
import { createAccount, createRate, fetchAccounts, type Account } from './api'

vi.mock('../../lib/api')
vi.mock('./api')

const USER = { id: 1, email: 'owner@example.com' }

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

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <AccountsPage />
    </QueryClientProvider>,
  )
}

async function fillAndAddAccount(rate?: string) {
  fireEvent.click(await screen.findByRole('button', { name: 'Add account' }))
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'HDFC' } })
  fireEvent.change(screen.getByLabelText('Opening balance'), { target: { value: '500' } })
  fireEvent.change(screen.getByLabelText('Opening date'), { target: { value: '2026-04-01' } })
  if (rate !== undefined) {
    fireEvent.change(screen.getByLabelText('Interest rate % a year'), { target: { value: rate } })
  }
  fireEvent.click(screen.getByRole('button', { name: 'Add account' }))
}

describe('AccountsPage', () => {
  beforeEach(() => {
    vi.mocked(fetchSession).mockResolvedValue(USER)
    vi.mocked(fetchAccounts).mockResolvedValue([SAVINGS])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('lists each account with its money formatted in rupees', async () => {
    renderPage()

    expect(await screen.findByText('SBI')).toBeInTheDocument()
    expect(screen.getByText('₹1,23,456.78')).toBeInTheDocument()
    expect(screen.getByText(/Signed in as owner@example.com/)).toBeInTheDocument()
  })

  it('says so when there are no accounts yet', async () => {
    vi.mocked(fetchAccounts).mockResolvedValue([])
    renderPage()

    expect(await screen.findByText(/No accounts yet/)).toBeInTheDocument()
  })

  it('shows a clear error when the list cannot be loaded', async () => {
    vi.mocked(fetchAccounts).mockRejectedValue(new Error('Request failed with HTTP 500'))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load your accounts: Request failed with HTTP 500',
    )
  })

  it('creates an account and shows it in the list', async () => {
    const created: Account = { ...SAVINGS, id: 2, name: 'HDFC', opening_balance_paise: 50_000 }
    vi.mocked(createAccount).mockResolvedValue(created)
    vi.mocked(fetchAccounts).mockResolvedValueOnce([SAVINGS]).mockResolvedValue([SAVINGS, created])
    renderPage()

    await fillAndAddAccount()

    expect(vi.mocked(createAccount).mock.calls[0]?.[0].opening_balance_paise).toBe(50_000)
    expect(await screen.findByText('HDFC')).toBeInTheDocument()
  })

  it('says when the account was saved but its rate was not', async () => {
    vi.mocked(createAccount).mockResolvedValue(SAVINGS)
    vi.mocked(createRate).mockRejectedValue(new Error('a rate from 2026-04-01 already exists'))
    renderPage()

    await fillAndAddAccount('7.1')

    expect(await screen.findByRole('status')).toHaveTextContent(
      'The account was saved, but its interest rate was not: a rate from 2026-04-01 already exists',
    )
    // The rate is dated from the account's opening date, never a date asked twice.
    expect(vi.mocked(createRate).mock.calls[0]?.[1]).toEqual({
      rate: '7.1',
      frequency: 'quarterly',
      from_date: '2026-04-01',
    })
  })

  it('reports the server error when the account itself is refused', async () => {
    vi.mocked(createAccount).mockRejectedValue(
      new Error('a pot cannot be the parent of another pot'),
    )
    renderPage()

    await fillAndAddAccount()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'a pot cannot be the parent of another pot',
    )
  })
})
