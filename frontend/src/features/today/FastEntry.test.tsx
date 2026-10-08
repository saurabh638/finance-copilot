import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
import type { Category } from '../categories/api'
import type { MovementCreate, Suggestion, Transaction } from '../transactions/api'
import FastEntry from './FastEntry'

const SBI: Account = {
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
}

const CENTRAL: Account = { ...SBI, id: 2, name: 'Central Bank' }

const CATEGORIES: Category[] = [
  { id: 10, name: 'Food & groceries', kind: 'expense', parent_id: null },
  { id: 11, name: 'Groceries', kind: 'expense', parent_id: 10 },
]

const SUGGESTIONS: Suggestion[] = [
  {
    merchant: 'Blinkit',
    times_used: 6,
    last_used: '2026-10-05',
    account_id: 2,
    category_id: 11,
    amount_paise: 45_000,
  },
]

/** A movement recorded yesterday, for the shortcuts that copy it. */
function movement(id: number, transaction_date: string): Transaction {
  return {
    id,
    transaction_date,
    merchant: 'Blinkit',
    note: null,
    source: 'manual',
    postings: [{ id, account_id: 2, amount_paise: -45_000, kind: 'expense', category_id: 11 }],
  }
}

interface RenderOptions {
  suggestions?: Suggestion[]
  movements?: Transaction[]
}

function renderEntry({ suggestions = SUGGESTIONS, movements = [] }: RenderOptions = {}) {
  const onSubmit = vi.fn<(payload: MovementCreate) => void>()
  render(
    <FastEntry
      accounts={[SBI, CENTRAL]}
      categories={CATEGORIES}
      suggestions={suggestions}
      movements={movements}
      today="2026-10-06"
      yesterday="2026-10-05"
      onSubmit={onSubmit}
      isSaving={false}
    />,
  )
  return onSubmit
}

function type(field: string, value: string) {
  fireEvent.change(screen.getByLabelText(field), { target: { value } })
}

describe('FastEntry', () => {
  it('starts on the amount, with the day’s date already filled in', () => {
    renderEntry()

    expect(screen.getByLabelText('Amount')).toHaveFocus()
    expect(screen.getByLabelText('Direction')).toHaveValue('expense')
  })

  it('fills the name, the account and the category when a chip is tapped', () => {
    const onSubmit = renderEntry()
    type('Amount', '450')

    fireEvent.click(screen.getByRole('button', { name: 'Blinkit' }))
    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 2,
      amount_paise: 45_000,
      transaction_date: '2026-10-06',
      merchant: 'Blinkit',
      note: null,
      category_id: 11,
    })
  })

  it('does not overwrite an amount the user already typed', () => {
    const onSubmit = renderEntry()
    type('Amount', '99')

    fireEvent.click(screen.getByRole('button', { name: 'Blinkit' }))
    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(onSubmit.mock.calls[0][0]).toMatchObject({ amount_paise: 9_900 })
  })

  it('fills the amount from the chip when none was typed yet', () => {
    const onSubmit = renderEntry()

    fireEvent.click(screen.getByRole('button', { name: 'Blinkit' }))
    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(onSubmit.mock.calls[0][0]).toMatchObject({ amount_paise: 45_000 })
  })

  it('offers no chips when the history has nothing to offer', () => {
    renderEntry({ suggestions: [] })

    expect(screen.queryByText('Used often')).not.toBeInTheDocument()
  })

  it('copies yesterday’s last movement, amount and all', () => {
    const onSubmit = renderEntry({ movements: [movement(7, '2026-10-05')] })

    fireEvent.click(screen.getByRole('button', { name: 'Same as yesterday' }))
    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 2,
      amount_paise: 45_000,
      transaction_date: '2026-10-06',
      merchant: 'Blinkit',
      note: null,
      category_id: 11,
    })
  })

  it('has nothing to copy when neither yesterday nor today has an entry', () => {
    renderEntry()

    expect(screen.getByRole('button', { name: 'Same as yesterday' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Repeat last' })).toBeDisabled()
  })

  it('offers to repeat the last thing recorded today', () => {
    renderEntry({ movements: [movement(9, '2026-10-06')] })

    expect(screen.getByRole('button', { name: 'Repeat last' })).toBeEnabled()
  })

  it('refuses money that is not money, and sends nothing', () => {
    const onSubmit = renderEntry()
    type('Amount', 'abc')

    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeInTheDocument()
  })

  it('asks for an account when none was chosen', () => {
    const onSubmit = renderEntry()
    type('Amount', '450')

    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Pick an account')).toBeInTheDocument()
  })
})

describe('the quick line', () => {
  it('fills the form from a sentence', () => {
    renderEntry()

    type('Say it in a line (optional)', '450 dinner blinkit sbi')

    expect(screen.getByLabelText('Amount')).toHaveValue('450')
    expect(screen.getByLabelText('Merchant (optional)')).toHaveValue('Blinkit')
    expect(screen.getByLabelText('Note (optional)')).toHaveValue('dinner')
    expect(screen.getByLabelText('Account')).toHaveValue('1')
  })

  it('records through the same payload path as the form', () => {
    const onSubmit = renderEntry()

    type('Say it in a line (optional)', '450 dinner blinkit sbi')
    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 1,
      amount_paise: 45_000,
      transaction_date: '2026-10-06',
      merchant: 'Blinkit',
      note: 'dinner',
    })
  })

  it('starts the line again once the movement is recorded', () => {
    renderEntry()

    type('Say it in a line (optional)', '450 blinkit sbi')
    fireEvent.click(screen.getByRole('button', { name: 'Record it' }))

    expect(screen.getByLabelText('Say it in a line (optional)')).toHaveValue('')
  })

  it('leaves the form alone while the line is empty', () => {
    renderEntry()

    type('Amount', '99')
    type('Say it in a line (optional)', '')

    expect(screen.getByLabelText('Amount')).toHaveValue('99')
  })
})
