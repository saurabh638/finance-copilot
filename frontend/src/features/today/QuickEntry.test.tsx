import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
import type { Category, CategoryKind } from '../categories/api'
import type { Suggestion } from '../transactions/api'
import QuickEntry from './QuickEntry'

const TODAY = '2026-10-08'

function account(id: number, name: string, alias: string | null = null): Account {
  return {
    id,
    name,
    alias,
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

function category(
  id: number,
  name: string,
  kind: CategoryKind,
  parent_id: number | null = null,
): Category {
  return { id, name, kind, parent_id }
}

function merchant(name: string): Suggestion {
  return {
    merchant: name,
    times_used: 3,
    last_used: '2026-10-05',
    account_id: 1,
    category_id: null,
    amount_paise: 45000,
  }
}

const SBI = account(1, 'SBI')
const CARD = account(2, 'SBI Credit Card', 'hdfc')
const SLICE = account(3, 'slice')

const RENT = category(21, 'Rent', 'expense', 20)
const HOME = category(20, 'Home', 'expense')

function renderEntry(overrides: { resetToken?: number } = {}) {
  const onFill = vi.fn()
  render(
    <QuickEntry
      accounts={[SBI, CARD, SLICE]}
      categories={[HOME, RENT]}
      suggestions={[merchant('Swiggy')]}
      today={TODAY}
      onFill={onFill}
      resetToken={overrides.resetToken ?? 0}
    />,
  )
  return { onFill }
}

function type(line: string): void {
  fireEvent.change(screen.getByLabelText('Say it in a line (optional)'), {
    target: { value: line },
  })
}

describe('QuickEntry', () => {
  it('says nothing it did not read', () => {
    renderEntry()

    expect(screen.queryByRole('list', { name: 'What was understood' })).not.toBeInTheDocument()
  })

  it('names what it understood, part by part', () => {
    renderEntry()

    type('450 dinner swiggy hdfc')

    for (const item of [
      '₹450.00',
      'Money spent',
      'Out of SBI Credit Card',
      'Merchant Swiggy',
      'Note dinner',
    ]) {
      expect(screen.getByText(item)).toBeInTheDocument()
    }
  })

  it('hands the reading to the form without recording anything', () => {
    const { onFill } = renderEntry()

    type('450 dinner swiggy hdfc')

    expect(onFill).toHaveBeenCalledWith(
      expect.objectContaining({
        amount: '450',
        merchant: 'Swiggy',
        note: 'dinner',
        account_id: String(CARD.id),
        kind: 'expense',
      }),
    )
  })

  it('says what it refused to guess', () => {
    renderEntry()

    type('450 swiggy 05/10')

    expect(screen.getByText(/05\/10 was not read as a date/)).toBeInTheDocument()
  })

  it('shows a word it could not place as the merchant', () => {
    renderEntry()

    type('450 blinka sbi')

    expect(screen.getByText('Merchant blinka')).toBeInTheDocument()
  })

  it('asks rather than choosing when two accounts match', () => {
    renderEntry()

    type('450 swiggy sbi hdfc')

    expect(screen.getByText('Which account was this out of?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: CARD.name })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: SBI.name })).toBeInTheDocument()
  })

  it('fills the account and stops asking when the question is answered', () => {
    const { onFill } = renderEntry()
    type('450 swiggy sbi hdfc')

    fireEvent.click(screen.getByRole('button', { name: CARD.name }))

    expect(screen.queryByText('Which account was this out of?')).not.toBeInTheDocument()
    expect(screen.getByText('Out of SBI Credit Card')).toBeInTheDocument()
    expect(onFill).toHaveBeenLastCalledWith(
      expect.objectContaining({ account_id: String(CARD.id) }),
    )
  })

  it('asks which of two readings a word is', () => {
    const onFill = vi.fn()
    render(
      <QuickEntry
        accounts={[SBI, CARD, SLICE]}
        categories={[HOME, RENT]}
        suggestions={[merchant('Swiggy'), merchant('Rent')]}
        today={TODAY}
        onFill={onFill}
        resetToken={0}
      />,
    )

    type('450 rent sbi')

    expect(screen.getByText('Is rent what this was, or where it is filed?')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'File it under Home · Rent' }))

    expect(onFill).toHaveBeenLastCalledWith(
      expect.objectContaining({ category_id: String(RENT.id) }),
    )
    expect(screen.getByText('Filed under Home · Rent')).toBeInTheDocument()
  })

  it('refuses a transfer between one account and itself', () => {
    renderEntry()

    type('500 transfer sbi sbi')

    expect(screen.getByRole('alert')).toHaveTextContent('A transfer needs two different accounts')
  })

  it('reads a transfer as two accounts', () => {
    renderEntry()

    type('500 sbi to slice')

    expect(screen.getByText('From SBI to slice')).toBeInTheDocument()
  })

  it('asks for the account a transfer is missing', () => {
    renderEntry()

    type('500 transfer to slice')

    expect(screen.getByText('Which account did the money come from?')).toBeInTheDocument()
  })

  it('stays out of the way while the line is empty', () => {
    const { onFill } = renderEntry()

    type('450 swiggy')
    onFill.mockClear()
    type('')

    expect(onFill).not.toHaveBeenCalled()
  })

  it('starts again once the movement is recorded', () => {
    const onFill = vi.fn()
    const entry = (resetToken: number) => (
      <QuickEntry
        accounts={[SBI, CARD, SLICE]}
        categories={[HOME, RENT]}
        suggestions={[merchant('Swiggy')]}
        today={TODAY}
        onFill={onFill}
        resetToken={resetToken}
      />
    )
    const { rerender } = render(entry(0))

    type('450 swiggy')
    expect(screen.getByText('Merchant Swiggy')).toBeInTheDocument()

    rerender(entry(1))

    expect(screen.queryByText('Merchant Swiggy')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Say it in a line (optional)')).toHaveValue('')
  })
})
