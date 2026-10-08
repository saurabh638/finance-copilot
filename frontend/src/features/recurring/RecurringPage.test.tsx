import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchAccounts } from '../accounts/api'
import { fetchCategories } from '../categories/api'
import { createItem, fetchItems, removeItem, updateItem } from './api'
import type { RecurringItem } from './api'
import RecurringPage from './RecurringPage'

vi.mock('../accounts/api')
vi.mock('../categories/api')
vi.mock('./api')

const TODAY = '2026-10-07'

const RENT: RecurringItem = {
  id: 7,
  name: 'Rent',
  kind: 'expense',
  amount_paise: 1_800_000,
  account_id: 1,
  category_id: 11,
  frequency: 'monthly',
  day_of_month: 5,
  weekday: null,
  starts_on: '2026-04-01',
  ends_on: null,
  is_active: true,
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <RecurringPage today={TODAY} />
    </QueryClientProvider>,
  )
}

async function ready() {
  await screen.findByRole('heading', { name: 'What repeats' })
}

beforeEach(() => {
  vi.mocked(fetchAccounts).mockResolvedValue([
    {
      id: 1,
      name: 'SBI',
      alias: null,
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
    },
  ])
  vi.mocked(fetchCategories).mockResolvedValue([
    { id: 10, name: 'Home', kind: 'expense', parent_id: null },
    { id: 11, name: 'Rent', kind: 'expense', parent_id: 10 },
  ])
  vi.mocked(fetchItems).mockResolvedValue([])
  vi.mocked(createItem).mockResolvedValue(RENT)
  vi.mocked(updateItem).mockResolvedValue(RENT)
  vi.mocked(removeItem).mockResolvedValue(undefined)
})

describe('RecurringPage', () => {
  it('lists what repeats, in the words it will come round in', async () => {
    vi.mocked(fetchItems).mockResolvedValue([RENT])
    renderPage()
    await ready()

    expect(screen.getByText('Rent')).toBeInTheDocument()
    expect(screen.getByText('₹18,000.00')).toBeInTheDocument()
    expect(screen.getByText('Every month on the 5th')).toBeInTheDocument()
  })

  it('says plainly when nothing repeats yet', async () => {
    renderPage()
    await ready()

    expect(screen.getByText(/Nothing repeats yet/)).toBeInTheDocument()
  })

  it('says what the screen is for, and that it records nothing itself', async () => {
    renderPage()
    await ready()

    expect(screen.getByText(/offered on the Today screen/)).toBeInTheDocument()
  })

  it('plans something that repeats', async () => {
    renderPage()
    await ready()

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Rent' } })
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '18,000' } })
    fireEvent.change(screen.getByLabelText('Account'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Filed under'), { target: { value: '11' } })
    fireEvent.change(screen.getByLabelText('Day of the month'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Starts on'), { target: { value: '2026-04-01' } })
    fireEvent.click(screen.getByRole('button', { name: 'Plan it' }))

    await waitFor(() => {
      expect(vi.mocked(createItem)).toHaveBeenCalledWith({
        name: 'Rent',
        kind: 'expense',
        amount_paise: 1_800_000,
        account_id: 1,
        category_id: 11,
        frequency: 'monthly',
        day_of_month: 5,
        starts_on: '2026-04-01',
      })
    })
  })

  it('shows the server’s refusal when a change did not take', async () => {
    vi.mocked(fetchItems).mockResolvedValue([RENT])
    vi.mocked(updateItem).mockRejectedValue(new Error('Rent is for spending, not earning'))
    renderPage()
    await ready()

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))
    const editor = screen.getByRole('group', { name: 'Change Rent' })
    fireEvent.change(within(editor).getByLabelText('Amount'), { target: { value: '20,000' } })
    fireEvent.click(within(editor).getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Rent is for spending, not earning')
  })

  it('changes only what was changed', async () => {
    vi.mocked(fetchItems).mockResolvedValue([RENT])
    renderPage()
    await ready()

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))
    const editor = screen.getByRole('group', { name: 'Change Rent' })
    fireEvent.change(within(editor).getByLabelText('Amount'), { target: { value: '20,000' } })
    fireEvent.click(within(editor).getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(vi.mocked(updateItem)).toHaveBeenCalledWith(7, { amount_paise: 2_000_000 })
    })
  })

  it('removes an item only after being asked twice', async () => {
    vi.mocked(fetchItems).mockResolvedValue([RENT])
    renderPage()
    await ready()

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(vi.mocked(removeItem)).not.toHaveBeenCalled()

    const question = screen.getByRole('group', { name: 'Remove Rent' })
    fireEvent.click(within(question).getByRole('button', { name: 'Yes, remove it' }))

    await waitFor(() => {
      expect(vi.mocked(removeItem)).toHaveBeenCalledWith(7)
    })
  })
})
