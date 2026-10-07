import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
import type { Category } from '../categories/api'
import type { RecurringItemCreate } from './api'
import RecurringForm from './RecurringForm'

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

const CENTRAL: Account = { ...SBI, id: 2, name: 'Central Bank' }

const CATEGORIES: Category[] = [
  { id: 10, name: 'Home', kind: 'expense', parent_id: null },
  { id: 11, name: 'Rent', kind: 'expense', parent_id: 10 },
  { id: 20, name: 'Salary', kind: 'income', parent_id: null },
]

function renderForm() {
  const onSubmit = vi.fn<(payload: RecurringItemCreate) => void>()
  render(
    <RecurringForm
      accounts={[SBI, CENTRAL]}
      categories={CATEGORIES}
      today={TODAY}
      onSubmit={onSubmit}
      isSaving={false}
    />,
  )
  return onSubmit
}

function fill(name: string, value: string): void {
  fireEvent.change(screen.getByLabelText(name), { target: { value } })
}

describe('RecurringForm', () => {
  it('plans a monthly item with the day it chose', () => {
    const onSubmit = renderForm()

    fill('Name', 'Rent')
    fill('Amount', '18,000')
    fill('Account', '1')
    fill('Filed under', '11')
    fill('Day of the month', '5')
    fill('Starts on', '2026-04-01')
    fireEvent.click(screen.getByRole('button', { name: 'Plan it' }))

    expect(onSubmit).toHaveBeenCalledWith({
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

  it('offers a weekday instead of a day of the month for a weekly item', () => {
    const onSubmit = renderForm()

    expect(screen.getByLabelText('Day of the month')).toBeDefined()
    fireEvent.change(screen.getByLabelText('How often'), { target: { value: 'weekly' } })

    expect(screen.queryByLabelText('Day of the month')).toBeNull()
    fill('Name', 'Household help')
    fill('Amount', '2000')
    fill('Account', '2')
    fill('Weekday', '2')
    fireEvent.click(screen.getByRole('button', { name: 'Plan it' }))

    expect(onSubmit).toHaveBeenCalledWith({
      name: 'Household help',
      kind: 'expense',
      amount_paise: 200_000,
      account_id: 2,
      frequency: 'weekly',
      weekday: 2,
      starts_on: TODAY,
    })
  })

  it('plans money arriving as an earning', () => {
    const onSubmit = renderForm()

    fill('Name', 'Salary')
    fireEvent.change(screen.getByLabelText('What it is'), { target: { value: 'income' } })
    fill('Amount', '5,00,000')
    fill('Account', '1')
    fill('Filed under', '20')
    fill('Day of the month', '1')
    fireEvent.click(screen.getByRole('button', { name: 'Plan it' }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'income', amount_paise: 5_00_000_00, category_id: 20 }),
    )
  })

  it('says what is wrong under the field instead of sending it', () => {
    const onSubmit = renderForm()

    fireEvent.click(screen.getByRole('button', { name: 'Plan it' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('A name is required')).toBeDefined()
    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeDefined()
    // The account list's own first option says the same thing as the refusal, so
    // this one is looked for among the paragraphs.
    expect(screen.getByText('Pick an account', { selector: 'p' })).toBeDefined()
    expect(screen.getByText('A monthly item needs a day of the month')).toBeDefined()
  })

  it('refuses an end before the start', () => {
    const onSubmit = renderForm()

    fill('Name', 'Rent')
    fill('Amount', '18,000')
    fill('Account', '1')
    fill('Day of the month', '5')
    fill('Starts on', '2026-10-07')
    fill('Ends on (optional)', '2026-09-30')
    fireEvent.click(screen.getByRole('button', { name: 'Plan it' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('The end cannot be before the start')).toBeDefined()
  })

  it('empties itself after a plan is sent, so the next one starts clean', () => {
    renderForm()

    fill('Name', 'Rent')
    fill('Amount', '18,000')
    fill('Account', '1')
    fill('Day of the month', '5')
    fireEvent.click(screen.getByRole('button', { name: 'Plan it' }))

    expect((screen.getByLabelText('Name') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('Amount') as HTMLInputElement).value).toBe('')
  })

  it('shows the server’s refusal above the fields', () => {
    render(
      <RecurringForm
        accounts={[SBI]}
        categories={CATEGORIES}
        today={TODAY}
        onSubmit={vi.fn()}
        isSaving={false}
        errorMessage="Rent is for spending, not earning"
      />,
    )

    expect(screen.getByRole('alert').textContent).toBe('Rent is for spending, not earning')
  })

  it('says it is saving while the plan is being sent', () => {
    render(
      <RecurringForm
        accounts={[SBI]}
        categories={CATEGORIES}
        today={TODAY}
        onSubmit={vi.fn()}
        isSaving
      />,
    )

    expect(screen.getByRole('button', { name: 'Planning…' })).toBeDefined()
  })
})
