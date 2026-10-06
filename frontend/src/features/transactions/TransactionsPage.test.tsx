import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchSession } from '../../lib/api'
import { fetchAccounts } from '../accounts/api'
import type { Account } from '../accounts/api'
import TransactionsPage from './TransactionsPage'
import {
  PAGE_SIZE,
  createTransaction,
  deleteTransaction,
  fetchTransactions,
  updateTransaction,
} from './api'
import type { Transaction } from './api'

vi.mock('../../lib/api')
vi.mock('../accounts/api')
// Only the calls are mocked: PAGE_SIZE has to stay the real number.
vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  fetchTransactions: vi.fn(),
  createTransaction: vi.fn(),
  updateTransaction: vi.fn(),
  deleteTransaction: vi.fn(),
}))

const USER = { id: 1, email: 'owner@example.com' }

function account(id: number, name: string): Account {
  return {
    id,
    name,
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
}

const SBI = account(1, 'SBI')
const CENTRAL = account(2, 'Central Bank')

const EXPENSE: Transaction = {
  id: 3,
  transaction_date: '2026-10-04',
  merchant: 'Blinkit',
  note: null,
  source: 'manual',
  postings: [{ id: 5, account_id: 1, amount_paise: -50000, kind: 'expense', category_id: null }],
}

const TRANSFER: Transaction = {
  id: 4,
  transaction_date: '2026-10-03',
  merchant: null,
  note: null,
  source: 'manual',
  postings: [
    { id: 6, account_id: 1, amount_paise: -100000, kind: 'transfer', category_id: null },
    { id: 7, account_id: 2, amount_paise: 100000, kind: 'transfer', category_id: null },
  ],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <TransactionsPage today="2026-10-04" />
    </QueryClientProvider>,
  )
}

describe('TransactionsPage', () => {
  beforeEach(() => {
    vi.mocked(fetchSession).mockResolvedValue(USER)
    vi.mocked(fetchAccounts).mockResolvedValue([SBI, CENTRAL])
    vi.mocked(fetchTransactions).mockResolvedValue([])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('lists the movements the server sent, in the order it sent them', async () => {
    vi.mocked(fetchTransactions).mockResolvedValue([EXPENSE, TRANSFER])
    renderPage()

    const rows = await screen.findAllByRole('listitem')

    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent('Blinkit')
    expect(rows[0]).toHaveTextContent('4 Oct 2026 · Money out · SBI')
    expect(rows[0]).toHaveTextContent('-₹500.00')
    expect(rows[1]).toHaveTextContent('No description')
    expect(rows[1]).toHaveTextContent('3 Oct 2026 · Transfer · SBI → Central Bank')
    expect(rows[1]).toHaveTextContent('₹1,000.00')
  })

  it('says so when nothing has been recorded', async () => {
    renderPage()

    expect(await screen.findByText(/Nothing recorded yet/)).toBeInTheDocument()
  })

  it('says so when a filter matches nothing, and asks for that filter', async () => {
    renderPage()
    await screen.findByText(/Nothing recorded yet/)

    fireEvent.change(screen.getByLabelText('Filter account'), { target: { value: '1' } })

    expect(await screen.findByText('No movements match these filters.')).toBeInTheDocument()
    expect(fetchTransactions).toHaveBeenLastCalledWith(
      expect.objectContaining({ accountId: 1, from: '', to: '', offset: 0 }),
    )
  })

  it('sends both ends of a date range, and clears them again', async () => {
    renderPage()
    await screen.findByText(/Nothing recorded yet/)

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-10-01' } })
    fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-10-31' } })

    expect(fetchTransactions).toHaveBeenLastCalledWith(
      expect.objectContaining({ from: '2026-10-01', to: '2026-10-31' }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))

    expect(fetchTransactions).toHaveBeenLastCalledWith(
      expect.objectContaining({ accountId: null, from: '', to: '' }),
    )
  })

  it('asks for the next page only when there is one', async () => {
    const firstPage = Array.from({ length: PAGE_SIZE }, (_unused, index): Transaction => ({
      ...EXPENSE,
      id: index + 1,
      merchant: `Movement ${index + 1}`,
    }))
    vi.mocked(fetchTransactions).mockResolvedValueOnce(firstPage).mockResolvedValueOnce([TRANSFER])
    renderPage()

    expect(await screen.findByText('Movement 1')).toBeInTheDocument()
    expect(screen.queryByText('No description')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Load more' }))

    expect(await screen.findByText('No description')).toBeInTheDocument()
    expect(fetchTransactions).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: PAGE_SIZE }),
    )
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
  })

  it('records an expense, clears the form, and shows the new row', async () => {
    vi.mocked(fetchTransactions).mockResolvedValueOnce([]).mockResolvedValueOnce([EXPENSE])
    vi.mocked(createTransaction).mockResolvedValue(EXPENSE)
    renderPage()
    await screen.findByText(/Nothing recorded yet/)

    fireEvent.click(screen.getByRole('button', { name: 'Record a movement' }))
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '500' } })
    fireEvent.change(screen.getByLabelText('Account'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Merchant (optional)'), { target: { value: 'Blinkit' } })
    fireEvent.click(screen.getByRole('button', { name: 'Record movement' }))

    // The new row can only appear once the save landed and the list refetched.
    expect(await screen.findByText('Blinkit')).toBeInTheDocument()
    expect(createTransaction).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 1,
      amount_paise: 50000,
      transaction_date: '2026-10-04',
      merchant: 'Blinkit',
      note: null,
    })
    expect(screen.getByLabelText('Amount')).toHaveValue('')
  })

  it('shows what the server said when a save is refused', async () => {
    vi.mocked(createTransaction).mockRejectedValue(
      new Error('Account 9 does not exist or is no longer in use'),
    )
    renderPage()
    await screen.findByText(/Nothing recorded yet/)

    fireEvent.click(screen.getByRole('button', { name: 'Record a movement' }))
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '500' } })
    fireEvent.change(screen.getByLabelText('Account'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Record movement' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Account 9 does not exist or is no longer in use',
    )
  })

  it('reports a list that will not load', async () => {
    vi.mocked(fetchTransactions).mockRejectedValue(new Error('Network down'))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load your movements: Network down',
    )
  })

  it('hides the form again when asked', async () => {
    renderPage()
    await screen.findByText(/Nothing recorded yet/)

    fireEvent.click(screen.getByRole('button', { name: 'Record a movement' }))
    expect(screen.getByLabelText('Amount')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Hide the form' }))
    expect(screen.queryByLabelText('Amount')).not.toBeInTheDocument()
  })

  it('corrects a movement in place, then closes the editor', async () => {
    vi.mocked(fetchTransactions).mockResolvedValue([EXPENSE])
    vi.mocked(updateTransaction).mockResolvedValue({ ...EXPENSE, note: 'bread' })
    renderPage()
    await screen.findByText('Blinkit')

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    fireEvent.change(screen.getByLabelText('Note (optional)'), { target: { value: 'bread' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(updateTransaction).toHaveBeenCalledWith(3, { note: 'bread' }))
    await waitFor(() => expect(screen.queryByLabelText('Date')).not.toBeInTheDocument())
  })

  it('shows why a correction was refused, and keeps it open', async () => {
    vi.mocked(fetchTransactions).mockResolvedValue([EXPENSE])
    vi.mocked(updateTransaction).mockRejectedValue(
      new Error('SBI opened on 2026-04-01, so 2026-03-31 is too early'),
    )
    renderPage()
    await screen.findByText('Blinkit')

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-03-31' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('SBI opened on 2026-04-01')
    expect(screen.getByLabelText('Date')).toHaveValue('2026-03-31')
  })

  it('removes a movement only after the removal is confirmed', async () => {
    vi.mocked(fetchTransactions).mockResolvedValueOnce([EXPENSE]).mockResolvedValueOnce([])
    vi.mocked(deleteTransaction).mockResolvedValue(undefined)
    renderPage()
    await screen.findByText('Blinkit')

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(deleteTransaction).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }))

    await waitFor(() => expect(deleteTransaction).toHaveBeenCalledWith(3))
    expect(await screen.findByText(/Nothing recorded yet/)).toBeInTheDocument()
  })

  it('reports a removal that was refused, and keeps the movement', async () => {
    vi.mocked(fetchTransactions).mockResolvedValue([EXPENSE])
    vi.mocked(deleteTransaction).mockRejectedValue(new Error('Transaction 3 does not exist'))
    renderPage()
    await screen.findByText('Blinkit')

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Transaction 3 does not exist')
    expect(screen.getByText('Blinkit')).toBeInTheDocument()
  })
})
