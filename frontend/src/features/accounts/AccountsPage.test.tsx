import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchSession } from '../../lib/api'
import AccountsPage from './AccountsPage'
import {
  createAccount,
  createRate,
  fetchAccounts,
  fetchBalance,
  fetchRates,
  updateAccount,
} from './api'
import type { Account } from './api'

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
    vi.mocked(fetchRates).mockResolvedValue([])
    vi.mocked(fetchBalance).mockResolvedValue({
      account_id: 1,
      as_of: null,
      opening_balance_paise: 12_345_678,
      postings_paise: -50_000,
      balance_paise: 12_295_678,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('lists each account with its balance as the movements left it', async () => {
    renderPage()

    expect(await screen.findByText('SBI')).toBeInTheDocument()
    // The opening balance was ₹1,23,456.78; ₹500 has left since.
    expect(await screen.findByText('₹1,22,956.78')).toBeInTheDocument()
    expect(screen.getByText(/Opening ₹1,23,456.78 \+ movements -₹500.00/)).toBeInTheDocument()
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

  it('opens an editor holding the account and its rate history', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))

    expect(await screen.findByLabelText('Name')).toHaveValue('SBI')
    expect(screen.getByLabelText('Opening balance')).toHaveValue('₹1,23,456.78')
    expect(screen.getByRole('heading', { name: 'Interest rates' })).toBeInTheDocument()
    expect(fetchRates).toHaveBeenCalledWith(SAVINGS.id)
  })

  it('saves an edited account as paise and says so', async () => {
    vi.mocked(updateAccount).mockResolvedValue({ ...SAVINGS, name: 'SBI salary' })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))

    fireEvent.change(await screen.findByLabelText('Name'), { target: { value: 'SBI salary' } })
    fireEvent.change(screen.getByLabelText('Opening balance'), { target: { value: '5,000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByRole('status')).toHaveTextContent('SBI was saved.')
    expect(vi.mocked(updateAccount).mock.calls[0]?.[0]).toBe(SAVINGS.id)
    expect(vi.mocked(updateAccount).mock.calls[0]?.[1].opening_balance_paise).toBe(500_000)
  })

  it('keeps the editor open and shows why a save was refused', async () => {
    vi.mocked(updateAccount).mockRejectedValue(new Error('Account 1 does not exist'))
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))

    fireEvent.change(await screen.findByLabelText('Name'), { target: { value: 'SBI salary' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Account 1 does not exist')
    expect(screen.getByLabelText('Name')).toHaveValue('SBI salary')
  })
})
