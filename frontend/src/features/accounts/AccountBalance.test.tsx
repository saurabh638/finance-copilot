import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AccountBalance from './AccountBalance'
import { fetchBalance } from './api'

vi.mock('./api')

function renderBalance() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <AccountBalance accountId={1} />
    </QueryClientProvider>,
  )
}

describe('AccountBalance', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the balance, and the two figures it came from', async () => {
    vi.mocked(fetchBalance).mockResolvedValue({
      account_id: 1,
      as_of: null,
      opening_balance_paise: 12_345_678,
      postings_paise: -50_000,
      interest_paise: 0,
      balance_paise: 12_295_678,
    })

    renderBalance()

    expect(await screen.findByText('₹1,22,956.78')).toBeInTheDocument()
    expect(screen.getByText(/Opening ₹1,23,456.78 \+ movements -₹500.00/)).toBeInTheDocument()
    expect(fetchBalance).toHaveBeenCalledWith(1)
  })

  it('says how much of the movements is interest, without adding it to the sum', async () => {
    vi.mocked(fetchBalance).mockResolvedValue({
      account_id: 1,
      as_of: null,
      opening_balance_paise: 12_345_678,
      postings_paise: 8_150,
      interest_paise: 58_150,
      balance_paise: 12_353_828,
    })

    renderBalance()

    expect(await screen.findByText('of which interest ₹581.50')).toBeInTheDocument()
    // The balance is still the opening balance plus the movements, interest
    // included rather than beside them.
    expect(screen.getByText(/\+ movements ₹81.50/)).toBeInTheDocument()
  })

  it('says nothing about interest when none has been credited', async () => {
    vi.mocked(fetchBalance).mockResolvedValue({
      account_id: 1,
      as_of: null,
      opening_balance_paise: 12_345_678,
      postings_paise: -50_000,
      interest_paise: 0,
      balance_paise: 12_295_678,
    })

    renderBalance()

    expect(await screen.findByText('₹1,22,956.78')).toBeInTheDocument()
    expect(screen.queryByText(/of which interest/)).toBeNull()
  })

  it('says it is still working while the figure is on its way', () => {
    vi.mocked(fetchBalance).mockReturnValue(new Promise(() => {}))

    renderBalance()

    expect(screen.getByText('Working out the balance…')).toBeInTheDocument()
  })

  it('says so when the balance cannot be worked out', async () => {
    vi.mocked(fetchBalance).mockRejectedValue(new Error('Network down'))

    renderBalance()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not work out the balance: Network down',
    )
  })
})
