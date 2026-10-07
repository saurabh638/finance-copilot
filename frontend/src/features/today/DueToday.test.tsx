import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
import { confirmItem, fetchDue, skipItem } from '../recurring/api'
import type { DueItem } from '../recurring/api'
import DueToday from './DueToday'

vi.mock('../recurring/api')

const TODAY = '2026-10-07'

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

const RENT: DueItem = {
  item: {
    id: 7,
    name: 'Rent',
    kind: 'expense',
    amount_paise: 1_800_000,
    account_id: 1,
    category_id: 11,
    frequency: 'monthly',
    day_of_month: 1,
    weekday: null,
    starts_on: '2026-04-01',
    ends_on: null,
    is_active: true,
  },
  due_on: '2026-10-01',
}

function renderDue() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <DueToday accounts={[SBI]} today={TODAY} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(fetchDue).mockResolvedValue([RENT])
  vi.mocked(confirmItem).mockResolvedValue({
    item: RENT.item,
    due_on: '2026-10-01',
    transaction_id: 20,
  })
  vi.mocked(skipItem).mockResolvedValue(RENT)
})

describe('DueToday', () => {
  it('says nothing at all when nothing is owed', async () => {
    vi.mocked(fetchDue).mockResolvedValue([])
    renderDue()

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Waiting to be recorded' })).toBeNull()
    })
  })

  it('shows what is owed, from which account, and the day it is owed for', async () => {
    renderDue()

    expect(await screen.findByText('Rent')).toBeInTheDocument()
    expect(screen.getByText('SBI')).toBeInTheDocument()
    expect(screen.getByText('₹18,000.00')).toBeInTheDocument()
    expect(screen.getByText('Owed for 1 Oct 2026')).toBeInTheDocument()
  })

  it('confirms a bill in one tap, for today', async () => {
    renderDue()
    await screen.findByText('Rent')

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    await waitFor(() => {
      expect(vi.mocked(confirmItem)).toHaveBeenCalledWith(7, TODAY, undefined)
    })
  })

  it('records a different amount when one is typed, and leaves the plan alone', async () => {
    renderDue()
    await screen.findByText('Rent')

    fireEvent.click(screen.getByRole('button', { name: 'Something else' }))
    const panel = screen.getByRole('group', { name: 'Something else for Rent' })
    fireEvent.change(within(panel).getByLabelText('A different amount this time'), {
      target: { value: '19,500' },
    })
    fireEvent.click(within(panel).getByRole('button', { name: 'Record that amount' }))

    await waitFor(() => {
      expect(vi.mocked(confirmItem)).toHaveBeenCalledWith(7, TODAY, 1_950_000)
    })
  })

  it('will not record an amount it cannot read', async () => {
    renderDue()
    await screen.findByText('Rent')

    fireEvent.click(screen.getByRole('button', { name: 'Something else' }))
    const panel = screen.getByRole('group', { name: 'Something else for Rent' })
    fireEvent.change(within(panel).getByLabelText('A different amount this time'), {
      target: { value: 'about nineteen thousand' },
    })

    expect(within(panel).getByRole('button', { name: 'Record that amount' })).toBeDisabled()
    expect(vi.mocked(confirmItem)).not.toHaveBeenCalled()
  })

  it('skips a bill that is not happening, recording nothing', async () => {
    renderDue()
    await screen.findByText('Rent')

    fireEvent.click(screen.getByRole('button', { name: 'Something else' }))
    const panel = screen.getByRole('group', { name: 'Something else for Rent' })
    fireEvent.click(within(panel).getByRole('button', { name: 'Not this time' }))

    await waitFor(() => {
      expect(vi.mocked(skipItem)).toHaveBeenCalledWith(7, TODAY)
    })
  })

  it('shows the server’s refusal on the row it belongs to', async () => {
    vi.mocked(confirmItem).mockRejectedValue(new Error('Rent was already recorded for 2026-10-01'))
    renderDue()
    await screen.findByText('Rent')

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Rent was already recorded for 2026-10-01',
    )
  })

  it('says it is recording while the movement is on its way', async () => {
    vi.mocked(confirmItem).mockReturnValue(new Promise(() => {}))
    renderDue()
    await screen.findByText('Rent')

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(await screen.findByRole('button', { name: 'Recording…' })).toBeDisabled()
  })

  it('lists two owed items as two rows', async () => {
    vi.mocked(fetchDue).mockResolvedValue([
      RENT,
      {
        item: { ...RENT.item, id: 8, name: 'Broadband', amount_paise: 99_900 },
        due_on: '2026-10-07',
      },
    ])
    renderDue()

    expect(await screen.findByText('Broadband')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm' })).toHaveLength(2)
  })
})
