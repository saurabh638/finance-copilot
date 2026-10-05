import { describe, expect, it } from 'vitest'

import type { Transaction } from './api'
import {
  displayDate,
  movementAmountPaise,
  movementAmountText,
  movementLabel,
  movementParties,
  movementTitle,
} from './describe'

const NAMES = new Map([
  [1, 'SBI'],
  [2, 'Central Bank'],
])

function movement(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: 1,
    transaction_date: '2026-10-04',
    merchant: 'Blinkit',
    note: null,
    source: 'manual',
    postings: [{ id: 1, account_id: 1, amount_paise: -50000, kind: 'expense' }],
    ...overrides,
  }
}

const TRANSFER: Transaction = {
  id: 2,
  transaction_date: '2026-10-04',
  merchant: null,
  note: null,
  source: 'manual',
  postings: [
    { id: 2, account_id: 1, amount_paise: -100000, kind: 'transfer' },
    { id: 3, account_id: 2, amount_paise: 100000, kind: 'transfer' },
  ],
}

describe('movementAmountText', () => {
  it('shows money that left an account with a minus, in rupees', () => {
    expect(movementAmountText(movement())).toBe('-₹500.00')
  })

  it('shows money that arrived without a sign of its own', () => {
    const income = movement({
      postings: [{ id: 1, account_id: 1, amount_paise: 2000000, kind: 'income' }],
    })

    expect(movementAmountText(income)).toBe('₹20,000.00')
  })

  it('shows a transfer as the amount moved, never as two amounts', () => {
    expect(movementAmountText(TRANSFER)).toBe('₹1,000.00')
  })

  it('keeps every paise of a large amount', () => {
    const large = movement({
      postings: [{ id: 1, account_id: 1, amount_paise: -123456789, kind: 'expense' }],
    })

    expect(movementAmountText(large)).toBe('-₹12,34,567.89')
  })
})

describe('movementAmountPaise', () => {
  it('reports an expense as a positive amount', () => {
    expect(movementAmountPaise(movement())).toBe(50000)
  })

  it('reports the amount a transfer moved', () => {
    expect(movementAmountPaise(TRANSFER)).toBe(100000)
  })
})

describe('movementLabel', () => {
  it('names the direction of a single posting', () => {
    expect(movementLabel(movement())).toBe('Money out')
    expect(
      movementLabel(
        movement({ postings: [{ id: 1, account_id: 1, amount_paise: 100, kind: 'income' }] }),
      ),
    ).toBe('Money in')
  })

  it('calls two postings a transfer, not spending', () => {
    expect(movementLabel(TRANSFER)).toBe('Transfer')
  })
})

describe('movementParties', () => {
  it('names the one account an expense touched', () => {
    expect(movementParties(movement(), NAMES)).toBe('SBI')
  })

  it('names both sides of a transfer, the money out first', () => {
    expect(movementParties(TRANSFER, NAMES)).toBe('SBI → Central Bank')
  })

  it('stands in for an account that is no longer in the list', () => {
    const gone = movement({
      postings: [{ id: 1, account_id: 9, amount_paise: -50000, kind: 'expense' }],
    })

    expect(movementParties(gone, NAMES)).toBe('Another account')
  })
})

describe('movementTitle', () => {
  it('prefers the merchant', () => {
    expect(movementTitle(movement({ note: 'milk' }))).toBe('Blinkit')
  })

  it('falls back to the note when there is no merchant', () => {
    expect(movementTitle(movement({ merchant: null, note: 'milk' }))).toBe('milk')
  })

  it('never leaves a row blank', () => {
    expect(movementTitle(movement({ merchant: '   ', note: null }))).toBe('No description')
  })
})

describe('displayDate', () => {
  it('writes the day the way a person reads it', () => {
    expect(displayDate('2026-10-04')).toBe('4 Oct 2026')
    expect(displayDate('2026-01-31')).toBe('31 Jan 2026')
  })

  it('hands back anything it cannot read, rather than inventing a date', () => {
    expect(displayDate('not a date')).toBe('not a date')
  })
})
