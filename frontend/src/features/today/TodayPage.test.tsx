import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchSession } from '../../lib/api'
import { fetchAccounts } from '../accounts/api'
import { fetchCategories } from '../categories/api'
import { fetchStreak, fetchSuggestions, fetchTransactions } from '../transactions/api'
import type { Transaction } from '../transactions/api'
import TodayPage from './TodayPage'

vi.mock('../../lib/api')
vi.mock('../accounts/api')
vi.mock('../categories/api')
vi.mock('../transactions/api')

const USER = { id: 1, email: 'owner@example.com' }

const TODAY = '2026-10-06'

const RECORDED: Transaction = {
  id: 7,
  transaction_date: TODAY,
  merchant: 'Blinkit',
  note: null,
  source: 'manual',
  postings: [{ id: 9, account_id: 1, amount_paise: -45_000, kind: 'expense', category_id: 11 }],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <TodayPage today={TODAY} />
    </QueryClientProvider>,
  )
}

async function ready() {
  await screen.findByRole('heading', { name: 'Today’s entries' })
}

beforeEach(() => {
  vi.mocked(fetchSession).mockResolvedValue(USER)
  vi.mocked(fetchAccounts).mockResolvedValue([])
  vi.mocked(fetchSuggestions).mockResolvedValue([])
  vi.mocked(fetchTransactions).mockResolvedValue([])
  vi.mocked(fetchStreak).mockResolvedValue({ days: 4, today_recorded: true })
  vi.mocked(fetchCategories).mockResolvedValue([
    { id: 10, name: 'Food & groceries', kind: 'expense', parent_id: null },
    { id: 11, name: 'Groceries', kind: 'expense', parent_id: 10 },
  ])
})

describe('TodayPage', () => {
  it('says how the run of days is going, without scolding', async () => {
    renderPage()

    expect(await screen.findByText('4 days in a row')).toBeInTheDocument()
  })

  it('says a run that ended yesterday has not been added to yet', async () => {
    vi.mocked(fetchStreak).mockResolvedValue({ days: 4, today_recorded: false })
    renderPage()

    expect(await screen.findByText('4 days in a row, up to yesterday')).toBeInTheDocument()
  })

  it('says plainly when nothing has been recorded today', async () => {
    renderPage()

    expect(await screen.findByText('Nothing recorded today yet.')).toBeInTheDocument()
  })

  it('lists what today holds, with what each entry was filed under', async () => {
    vi.mocked(fetchTransactions).mockResolvedValue([RECORDED])
    renderPage()

    expect(await screen.findByText('Blinkit')).toBeInTheDocument()
    expect(screen.getByText('-₹450.00')).toBeInTheDocument()
    expect(screen.getByText('Filed under Food & groceries · Groceries')).toBeInTheDocument()
  })

  it('asks the list only for today', async () => {
    renderPage()
    await ready()

    expect(fetchTransactions).toHaveBeenCalledWith(
      expect.objectContaining({ from: TODAY, to: TODAY }),
    )
  })

  it('opens the catch-up on request, and closes it again', async () => {
    renderPage()
    await ready()

    fireEvent.click(screen.getByRole('button', { name: 'Catch up on days I missed' }))
    expect(screen.getByRole('heading', { name: 'Catch up on days I missed' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Hide the catch-up' }))
    expect(
      screen.queryByRole('heading', { name: 'Catch up on days I missed' }),
    ).not.toBeInTheDocument()
  })

  it('says where a movement is corrected, since this screen does not do that', async () => {
    renderPage()
    await ready()

    expect(
      screen.getByText(/Correcting or removing a movement happens on the Transactions/),
    ).toBeInTheDocument()
  })
})
