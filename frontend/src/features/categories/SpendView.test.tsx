import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { todayIso } from '../../lib/dates'
import SpendView from './SpendView'
import { fetchSpend } from './api'
import type { SpendReport } from './api'
import { monthRange } from './spend'

vi.mock('./api')

const PERIOD = monthRange(todayIso())

/** A month of ₹950: ₹800 under Food & groceries, ₹150 filed under nothing. */
const REPORT: SpendReport = {
  rows: [
    {
      id: 1,
      name: 'Food & groceries',
      parent_id: null,
      kind: 'expense',
      direct_paise: 0,
      total_paise: 80_000,
    },
    {
      id: 2,
      name: 'Groceries',
      parent_id: 1,
      kind: 'expense',
      direct_paise: 60_000,
      total_paise: 60_000,
    },
    {
      id: 3,
      name: 'Eating out',
      parent_id: 1,
      kind: 'expense',
      direct_paise: 20_000,
      total_paise: 20_000,
    },
  ],
  uncategorised_paise: 15_000,
  total_paise: 95_000,
}

const NOTHING: SpendReport = { rows: [], uncategorised_paise: 0, total_paise: 0 }

function renderView() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <SpendView />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(fetchSpend).mockResolvedValue(REPORT)
})

describe('SpendView', () => {
  it('reads the month the day falls in to start with', async () => {
    renderView()

    await screen.findByText(/The period cost/)

    expect(fetchSpend).toHaveBeenCalledWith(PERIOD.from, PERIOD.to)
    expect(screen.getByLabelText('Spending from')).toHaveValue(PERIOD.from)
    expect(screen.getByLabelText('Spending to')).toHaveValue(PERIOD.to)
  })

  it('shows what the period cost, in whole rupees', async () => {
    renderView()

    expect(await screen.findByText(/The period cost/)).toHaveTextContent('₹950.00')
  })

  it('shows each branch with its own names under it', async () => {
    renderView()

    expect(await screen.findByRole('heading', { name: 'Food & groceries' })).toBeInTheDocument()
    expect(screen.getByText('Groceries')).toBeInTheDocument()
    expect(screen.getByText('Eating out')).toBeInTheDocument()
    expect(screen.getByText('₹600.00')).toBeInTheDocument()
    expect(screen.getByText('₹200.00')).toBeInTheDocument()
    expect(screen.getByText('₹150.00')).toBeInTheDocument()
  })

  it('says what share of the period a branch took', async () => {
    renderView()

    await screen.findByRole('heading', { name: 'Food & groceries' })

    // ₹800 of ₹950 is 84%, rounded to a whole percent.
    expect(screen.getByText('84%')).toBeInTheDocument()
  })

  it('shows the money that is filed under nothing, and says what it is', async () => {
    renderView()

    expect(await screen.findByText('Not filed under a category')).toBeInTheDocument()
    expect(screen.getByText(/spending with no name on it/)).toBeInTheDocument()
  })

  it('leaves the uncategorised line out when there is none', async () => {
    vi.mocked(fetchSpend).mockResolvedValue({ ...REPORT, uncategorised_paise: 0 })
    renderView()

    await screen.findByRole('heading', { name: 'Food & groceries' })

    expect(screen.queryByText('Not filed under a category')).not.toBeInTheDocument()
  })

  it('says plainly when nothing was spent in the dates', async () => {
    vi.mocked(fetchSpend).mockResolvedValue(NOTHING)
    renderView()

    expect(await screen.findByText('Nothing was spent in these dates.')).toBeInTheDocument()
  })

  it('reads the dates the user asks for', async () => {
    renderView()
    await screen.findByText(/The period cost/)

    fireEvent.change(screen.getByLabelText('Spending from'), { target: { value: '2026-09-01' } })
    fireEvent.change(screen.getByLabelText('Spending to'), { target: { value: '2026-09-30' } })

    await waitFor(() => expect(fetchSpend).toHaveBeenCalledWith('2026-09-01', '2026-09-30'))
  })

  it('says what the server said when the report cannot be read', async () => {
    vi.mocked(fetchSpend).mockRejectedValue(new Error('Request failed with HTTP 500'))
    renderView()

    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed with HTTP 500')
  })
})
