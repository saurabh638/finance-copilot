import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { confirmInterest, dropInterest, fetchInterest, proposeInterest } from './api'
import type { AccountInterest, InterestCredit } from './api'
import InterestPanel from './InterestPanel'

vi.mock('./api')

const TODAY = '2026-11-02'

const PROPOSAL: InterestCredit = {
  id: 7,
  account_id: 2,
  period_start: '2026-10-01',
  period_end: '2026-10-31',
  rate_percent: '7.1000',
  computed_paise: 58_139,
  credited_paise: null,
  transaction_id: null,
  confirmed_on: null,
}

const CREDITED: InterestCredit = {
  ...PROPOSAL,
  id: 6,
  credited_paise: 58_150,
  transaction_id: 20,
  confirmed_on: '2026-11-02',
}

const SUMMARY: AccountInterest = {
  credited_paise: 58_150,
  uncredited_paise: 58_139,
  proposals: [PROPOSAL],
  history: [CREDITED],
}

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <InterestPanel accountId={2} today={TODAY} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(fetchInterest).mockResolvedValue(SUMMARY)
  vi.mocked(proposeInterest).mockResolvedValue([])
  vi.mocked(confirmInterest).mockResolvedValue({ ...PROPOSAL, credited_paise: 58_139 })
  vi.mocked(dropInterest).mockResolvedValue(undefined)
})

describe('InterestPanel', () => {
  it('says what has been credited and what is waiting', async () => {
    renderPanel()

    expect(await screen.findByText(/Credited so far/)).toHaveTextContent(
      'Credited so far ₹581.50 · waiting to be confirmed ₹581.39',
    )
  })

  it('lists a period waiting to be confirmed, with its rate and the ledger’s figure', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    const waiting = screen.getByRole('list', { name: 'Waiting to be confirmed' })
    expect(within(waiting).getByText('1 Oct 2026 to 31 Oct 2026 · 7.1% a year')).toBeInTheDocument()
    expect(within(waiting).getByText('₹581.39')).toBeInTheDocument()
  })

  it('credits the ledger’s own figure when no bank figure is typed', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    await waitFor(() => {
      expect(vi.mocked(confirmInterest)).toHaveBeenCalledWith(2, 7, {
        on: TODAY,
        creditedPaise: undefined,
      })
    })
  })

  it('credits the bank’s figure when one is typed', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.change(screen.getByLabelText('What the bank paid (optional)'), {
      target: { value: '581.50' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    await waitFor(() => {
      expect(vi.mocked(confirmInterest)).toHaveBeenCalledWith(2, 7, {
        on: TODAY,
        creditedPaise: 58_150,
      })
    })
  })

  it('refuses a bank figure it cannot read, and sends nothing', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.change(screen.getByLabelText('What the bank paid (optional)'), {
      target: { value: 'about six hundred' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(
      screen.getByText('Enter the figure like 581.50, or leave it empty to use the ledger’s'),
    ).toBeInTheDocument()
    expect(vi.mocked(confirmInterest)).not.toHaveBeenCalled()
  })

  it('asks before throwing a period away, and says it can be worked out again', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.click(screen.getByRole('button', { name: 'Throw it away' }))

    expect(vi.mocked(dropInterest)).not.toHaveBeenCalled()
    expect(
      screen.getByText(
        'Something the ledger worked out wrongly can be worked out again afterwards.',
      ),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Yes, throw it away' }))

    await waitFor(() => {
      expect(vi.mocked(dropInterest)).toHaveBeenCalledWith(2, 7)
    })
  })

  it('keeps a period when the removal is not meant', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.click(screen.getByRole('button', { name: 'Throw it away' }))
    fireEvent.click(screen.getByRole('button', { name: 'Keep it' }))

    expect(screen.queryByRole('button', { name: 'Yes, throw it away' })).toBeNull()
    expect(vi.mocked(dropInterest)).not.toHaveBeenCalled()
  })

  it('works out what has finished, as of today', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.click(screen.getByRole('button', { name: 'Work out what has finished' }))

    await waitFor(() => {
      expect(vi.mocked(proposeInterest)).toHaveBeenCalledWith(2, TODAY)
    })
  })

  it('shows what has been credited, newest first, with the difference where there is one', async () => {
    renderPanel()
    await screen.findByText(/Credited so far/)

    const credited = screen.getByRole('list', { name: 'Credited periods' })
    expect(within(credited).getByText('₹581.50')).toBeInTheDocument()
    expect(
      within(credited).getByText('The bank paid ₹0.11 more than the ledger worked out'),
    ).toBeInTheDocument()
  })

  it('says nothing about a difference when the bank paid what the ledger worked out', async () => {
    vi.mocked(fetchInterest).mockResolvedValue({
      credited_paise: 58_139,
      uncredited_paise: 0,
      proposals: [],
      history: [{ ...CREDITED, credited_paise: 58_139 }],
    })
    renderPanel()

    await screen.findByText(/Credited so far/)
    expect(screen.queryByText(/more than the ledger worked out/)).toBeNull()
  })

  it('says plainly when nothing is waiting', async () => {
    vi.mocked(fetchInterest).mockResolvedValue({
      credited_paise: 0,
      uncredited_paise: 0,
      proposals: [],
      history: [],
    })
    renderPanel()

    expect(await screen.findByText(/Nothing is waiting/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Credited' })).toBeNull()
  })

  it('shows a refusal from the server on the period it belongs to', async () => {
    vi.mocked(confirmInterest).mockRejectedValue(
      new Error('interest to 2026-10-31 was already credited on 2026-11-01'),
    )
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('already credited on 2026-11-01')
  })

  it('says it cannot read the interest when the server refuses', async () => {
    vi.mocked(fetchInterest).mockRejectedValue(new Error('Not found'))
    renderPanel()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not read the interest: Not found',
    )
  })

  it('says it is working while the interest is on its way', async () => {
    vi.mocked(confirmInterest).mockReturnValue(new Promise(() => {}))
    renderPanel()
    await screen.findByText(/Credited so far/)

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(await screen.findByRole('button', { name: 'Crediting…' })).toBeDisabled()
  })
})
