import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RateHistory from './RateHistory'
import { createRate, deleteRate, fetchRates, type InterestRate } from './api'

vi.mock('./api')

const QUARTERLY: InterestRate = {
  id: 1,
  account_id: 1,
  rate: '7.1000',
  from_date: '2026-04-01',
  frequency: 'quarterly',
  note: null,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

const MONTHLY: InterestRate = {
  ...QUARTERLY,
  id: 2,
  rate: '6.6000',
  from_date: '2026-07-01',
  frequency: 'monthly',
}

function renderHistory() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <RateHistory accountId={1} />
    </QueryClientProvider>,
  )
}

function fillDraft(rate: string, date: string) {
  fireEvent.change(screen.getByLabelText('New rate % a year'), { target: { value: rate } })
  fireEvent.change(screen.getByLabelText('From date'), { target: { value: date } })
  fireEvent.click(screen.getByRole('button', { name: 'Record rate' }))
}

describe('RateHistory', () => {
  beforeEach(() => {
    vi.mocked(fetchRates).mockResolvedValue([MONTHLY, QUARTERLY])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('lists the rates the server sent, in the order it sent them', async () => {
    renderHistory()

    expect(await screen.findByText('6.6000% · Monthly · from 2026-07-01')).toBeInTheDocument()
    expect(screen.getByText('7.1000% · Quarterly · from 2026-04-01')).toBeInTheDocument()
  })

  it('says so when no rate has been recorded', async () => {
    vi.mocked(fetchRates).mockResolvedValue([])
    renderHistory()

    expect(await screen.findByText('No rates recorded yet.')).toBeInTheDocument()
  })

  it('shows a clear error when the history cannot be loaded', async () => {
    vi.mocked(fetchRates).mockRejectedValue(new Error('Request failed with HTTP 500'))
    renderHistory()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load the rates: Request failed with HTTP 500',
    )
  })

  it('records a rate from a date and clears the form', async () => {
    vi.mocked(createRate).mockResolvedValue(QUARTERLY)
    renderHistory()
    await screen.findByText('6.6000% · Monthly · from 2026-07-01')

    fillDraft('7.25', '2026-10-01')

    await waitFor(() => expect(screen.getByLabelText('New rate % a year')).toHaveValue(''))
    expect(vi.mocked(createRate).mock.calls[0]?.[0]).toBe(1)
    expect(vi.mocked(createRate).mock.calls[0]?.[1]).toEqual({
      rate: '7.25',
      frequency: 'quarterly',
      from_date: '2026-10-01',
    })
  })

  it('refuses a rate with five decimals and sends nothing', async () => {
    renderHistory()
    await screen.findByText('6.6000% · Monthly · from 2026-07-01')

    fillDraft('7.12345', '2026-10-01')

    expect(screen.getByText('Use up to four decimals, like 7.1000')).toBeInTheDocument()
    expect(createRate).not.toHaveBeenCalled()
  })

  it('demands both a rate and a date', async () => {
    renderHistory()
    await screen.findByText('6.6000% · Monthly · from 2026-07-01')

    fireEvent.click(screen.getByRole('button', { name: 'Record rate' }))
    expect(screen.getByText('A rate is required')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('New rate % a year'), { target: { value: '7.25' } })
    fireEvent.click(screen.getByRole('button', { name: 'Record rate' }))
    expect(screen.getByText('A start date is required')).toBeInTheDocument()
    expect(createRate).not.toHaveBeenCalled()
  })

  it("shows the server's refusal when that date already has a rate", async () => {
    vi.mocked(createRate).mockRejectedValue(new Error('a rate from 2026-10-01 already exists'))
    renderHistory()
    await screen.findByText('6.6000% · Monthly · from 2026-07-01')

    fillDraft('7.25', '2026-10-01')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'a rate from 2026-10-01 already exists',
    )
  })

  it('asks before removing a rate, and removes it only once confirmed', async () => {
    vi.mocked(deleteRate).mockResolvedValue(undefined)
    renderHistory()
    await screen.findByText('6.6000% · Monthly · from 2026-07-01')

    fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[1])

    expect(screen.getByText('Remove the rate from 2026-04-01?')).toBeInTheDocument()
    expect(deleteRate).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Yes, remove' }))

    await waitFor(() => expect(deleteRate).toHaveBeenCalled())
    expect(vi.mocked(deleteRate).mock.calls[0]).toEqual([1, 1])
  })

  it('leaves the rate alone when the question is dismissed', async () => {
    renderHistory()
    await screen.findByText('6.6000% · Monthly · from 2026-07-01')

    fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[1])
    fireEvent.click(screen.getByRole('button', { name: 'Keep it' }))

    expect(deleteRate).not.toHaveBeenCalled()
    expect(screen.queryByText('Remove the rate from 2026-04-01?')).not.toBeInTheDocument()
    expect(screen.getByText('7.1000% · Quarterly · from 2026-04-01')).toBeInTheDocument()
  })
})
