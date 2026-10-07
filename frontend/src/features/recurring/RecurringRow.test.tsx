import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
import type { Category } from '../categories/api'
import type { RecurringItem, RecurringItemUpdate } from './api'
import RecurringRow from './RecurringRow'

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

const CATEGORIES: Category[] = [
  { id: 10, name: 'Home', kind: 'expense', parent_id: null },
  { id: 11, name: 'Rent', kind: 'expense', parent_id: 10 },
]

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

interface Handlers {
  onSave: ReturnType<typeof vi.fn<(update: RecurringItemUpdate) => void>>
  onSetActive: ReturnType<typeof vi.fn<(isActive: boolean) => void>>
  onRemove: ReturnType<typeof vi.fn<() => void>>
}

function renderRow(item: RecurringItem = RENT, errorMessage: string | null = null): Handlers {
  const handlers: Handlers = {
    onSave: vi.fn<(update: RecurringItemUpdate) => void>(),
    onSetActive: vi.fn<(isActive: boolean) => void>(),
    onRemove: vi.fn<() => void>(),
  }

  render(
    <RecurringRow
      item={item}
      accounts={[SBI]}
      categories={CATEGORIES}
      isSaving={false}
      errorMessage={errorMessage}
      onSave={handlers.onSave}
      onSetActive={handlers.onSetActive}
      onRemove={handlers.onRemove}
    />,
  )

  return handlers
}

describe('RecurringRow', () => {
  it('says what the item is, how much, out of where, and how often', () => {
    renderRow()

    expect(screen.getByText('Rent')).toBeDefined()
    expect(screen.getByText('₹18,000.00')).toBeDefined()
    expect(screen.getByText('SBI')).toBeDefined()
    expect(screen.getByText('Filed under Home · Rent')).toBeDefined()
    expect(screen.getByText('Every month on the 5th')).toBeDefined()
  })

  it('says when an item is paused, and offers to start it again', () => {
    const handlers = renderRow({ ...RENT, is_active: false })

    expect(screen.getByText('Paused')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Start it again' }))

    expect(handlers.onSetActive).toHaveBeenCalledWith(true)
  })

  it('pauses a running item', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))

    expect(handlers.onSetActive).toHaveBeenCalledWith(false)
  })

  it('asks before removing, and says what stays behind', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))

    expect(handlers.onRemove).not.toHaveBeenCalled()
    expect(
      screen.getByText('Remove Rent? The movements it has already recorded stay in the ledger.'),
    ).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: 'Yes, remove it' }))

    expect(handlers.onRemove).toHaveBeenCalled()
  })

  it('puts the removal away when it is not meant', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    fireEvent.click(screen.getByRole('button', { name: 'Keep it' }))

    expect(handlers.onRemove).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Yes, remove it' })).toBeNull()
  })

  it('opens filled in, and sends only what changed', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))

    expect((screen.getByLabelText('Amount') as HTMLInputElement).value).toBe('₹18,000.00')
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '20,000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(handlers.onSave).toHaveBeenCalledWith({ amount_paise: 2_000_000 })
  })

  it('sends the whole rhythm when only the day changed', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))
    fireEvent.change(screen.getByLabelText('Day of the month'), { target: { value: '9' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(handlers.onSave).toHaveBeenCalledWith({
      frequency: 'monthly',
      day_of_month: 9,
      weekday: null,
    })
  })

  it('clears the filing when none is chosen', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))
    fireEvent.change(screen.getByLabelText('Filed under'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(handlers.onSave).toHaveBeenCalledWith({ category_id: null })
  })

  it('refuses what the server would refuse, without sending it', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: 'nothing' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(handlers.onSave).not.toHaveBeenCalled()
    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeDefined()
  })

  it('shows the server’s refusal when the change did not take', () => {
    renderRow(RENT, 'Rent is for spending, not earning')

    expect(screen.getByRole('alert').textContent).toBe('Rent is for spending, not earning')
  })

  it('puts the editor away without sending anything', () => {
    const handlers = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Change' }))
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '20,000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Never mind' }))

    expect(handlers.onSave).not.toHaveBeenCalled()
    expect(screen.queryByLabelText('Amount')).toBeNull()
  })
})
