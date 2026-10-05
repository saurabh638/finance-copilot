import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import BalanceCheckPanel from './BalanceCheckPanel'
import { adjustBalanceCheck, createBalanceCheck, fetchAdjustmentShare } from './api'
import type { BalanceCheck } from './api'

vi.mock('./api')

const TODAY = '2026-10-05'

/** The ledger holds ₹1,51,500; the bank says ₹1,51,000: ₹500 is missing. */
const SHORT: BalanceCheck = {
  id: 5,
  account_id: 1,
  checked_on: TODAY,
  computed_balance_paise: 15_150_000,
  stated_balance_paise: 15_100_000,
  difference_paise: -50_000,
  adjustment_transaction_id: null,
  warning: false,
  threshold_paise: 1_00_000,
}

const SHARE = {
  month: '2026-10-01',
  spend_paise: 2_50_000,
  adjustments_paise: 50_000,
  share_percent: 20,
}

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <BalanceCheckPanel accountId={1} today={TODAY} />
    </QueryClientProvider>,
  )
}

function typeBalance(value: string) {
  fireEvent.change(screen.getByLabelText('Balance your bank shows'), { target: { value } })
}

function compare() {
  fireEvent.click(screen.getByRole('button', { name: /Compare|Checking/ }))
}

describe('BalanceCheckPanel', () => {
  beforeEach(() => {
    vi.mocked(fetchAdjustmentShare).mockResolvedValue(SHARE)
    vi.mocked(createBalanceCheck).mockResolvedValue(SHORT)
    vi.mocked(adjustBalanceCheck).mockResolvedValue({ ...SHORT, adjustment_transaction_id: 12 })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('asks for the balance the bank shows, with the field ready', async () => {
    renderPanel()

    expect(screen.getByLabelText('Balance your bank shows')).toHaveValue('')
    expect(screen.getByLabelText('Balance your bank shows')).toHaveFocus()
    expect(await screen.findByText(/₹500.00 of ₹2,500.00 spent \(20%\)/)).toBeInTheDocument()
    expect(fetchAdjustmentShare).toHaveBeenCalledWith(1, '2026-10-01')
  })

  it('will not compare an empty balance', () => {
    renderPanel()

    compare()

    expect(screen.getByText('Enter the balance your bank shows')).toBeInTheDocument()
    expect(createBalanceCheck).not.toHaveBeenCalled()
  })

  it('will not compare something that is not money', () => {
    renderPanel()
    typeBalance('abc')

    compare()

    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeInTheDocument()
    expect(createBalanceCheck).not.toHaveBeenCalled()
  })

  it('compares in exact paise, and asks for no write-off yet', async () => {
    renderPanel()
    typeBalance('1,51,000')

    compare()

    await waitFor(() =>
      expect(createBalanceCheck).toHaveBeenCalledWith(1, {
        on: TODAY,
        stated_balance_paise: 15_100_000,
        adjust: false,
      }),
    )
  })

  it('shows what the ledger says, what the bank says, and the difference', async () => {
    renderPanel()
    typeBalance('1,51,000')
    compare()

    expect(await screen.findByText('The ledger says ₹1,51,500.00')).toBeInTheDocument()
    expect(screen.getByText('Your bank says ₹1,51,000.00')).toBeInTheDocument()
    expect(screen.getByText('₹500.00 less than the ledger says.')).toBeInTheDocument()
  })

  it('offers nothing to post when the two agree', async () => {
    vi.mocked(createBalanceCheck).mockResolvedValue({
      ...SHORT,
      stated_balance_paise: 15_150_000,
      difference_paise: 0,
    })
    renderPanel()
    typeBalance('1,51,500')

    compare()

    expect(await screen.findByText('The ledger matches the bank exactly.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Write off|Record/ })).not.toBeInTheDocument()
  })

  it('calls money found a record, not a write-off', async () => {
    vi.mocked(createBalanceCheck).mockResolvedValue({
      ...SHORT,
      stated_balance_paise: 15_200_000,
      difference_paise: 50_000,
    })
    renderPanel()
    typeBalance('1,52,000')

    compare()

    expect(await screen.findByRole('button', { name: 'Record ₹500.00' })).toBeInTheDocument()
  })

  it('asks the SPEC.md questions when the difference is large, without blocking', async () => {
    vi.mocked(createBalanceCheck).mockResolvedValue({
      ...SHORT,
      warning: true,
      difference_paise: -5_00_000,
    })
    renderPanel()
    typeBalance('1,46,500')

    compare()

    expect(await screen.findByText(/recurring charge you forgot/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Write off ₹5,000.00' })).toBeEnabled()
  })

  it('writes off the recorded check, not a fresh reading', async () => {
    renderPanel()
    typeBalance('1,51,000')
    compare()
    await screen.findByText('₹500.00 less than the ledger says.')

    fireEvent.click(screen.getByRole('button', { name: 'Write off ₹500.00' }))

    await waitFor(() => expect(adjustBalanceCheck).toHaveBeenCalledWith(1, 5))
    expect(createBalanceCheck).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('Written off.')).toBeInTheDocument()
  })

  it('shows why a write-off was refused, and offers it again', async () => {
    vi.mocked(adjustBalanceCheck).mockRejectedValue(
      new Error('this check has nothing to write off'),
    )
    renderPanel()
    typeBalance('1,51,000')
    compare()
    await screen.findByText('₹500.00 less than the ledger says.')

    fireEvent.click(screen.getByRole('button', { name: 'Write off ₹500.00' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'this check has nothing to write off',
    )
    expect(screen.getByRole('button', { name: 'Write off ₹500.00' })).toBeInTheDocument()
  })

  it('lets the check be put away again', async () => {
    renderPanel()
    typeBalance('1,51,000')
    compare()
    await screen.findByText('₹500.00 less than the ledger says.')

    fireEvent.click(screen.getByRole('button', { name: 'Done' }))

    expect(screen.queryByText('₹500.00 less than the ledger says.')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Balance your bank shows')).toHaveValue('')
  })
})
