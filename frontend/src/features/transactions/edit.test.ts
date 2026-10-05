import { describe, expect, it } from 'vitest'

import type { Transaction } from './api'
import { canEditAmount, editValues, hasChanges, toUpdate, validateEdit } from './edit'

function movement(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: 7,
    transaction_date: '2026-10-04',
    merchant: 'Blinkit',
    note: 'milk',
    source: 'manual',
    postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense' }],
    ...overrides,
  }
}

const TRANSFER = movement({
  id: 8,
  merchant: null,
  note: null,
  postings: [
    { id: 10, account_id: 1, amount_paise: -100000, kind: 'transfer' },
    { id: 11, account_id: 2, amount_paise: 100000, kind: 'transfer' },
  ],
})

describe('editValues', () => {
  it('opens with what the movement already says', () => {
    expect(editValues(movement())).toEqual({
      transaction_date: '2026-10-04',
      amount: '₹500.00',
      merchant: 'Blinkit',
      note: 'milk',
    })
  })

  it('opens a missing merchant and note as empty text', () => {
    expect(editValues(TRANSFER)).toMatchObject({ merchant: '', note: '', amount: '₹1,000.00' })
  })
})

describe('canEditAmount', () => {
  it('allows it when the movement has one posting', () => {
    expect(canEditAmount(movement())).toBe(true)
  })

  it('refuses it for a two-sided movement', () => {
    expect(canEditAmount(TRANSFER)).toBe(false)
  })
})

describe('validateEdit', () => {
  it('accepts an unchanged form', () => {
    expect(validateEdit(editValues(movement()), movement())).toEqual({})
  })

  it('refuses an amount that is not money, zero, or negative', () => {
    const original = movement()
    expect(validateEdit({ ...editValues(original), amount: 'abc' }, original).amount).toBeDefined()
    expect(validateEdit({ ...editValues(original), amount: '0' }, original).amount).toBe(
      'The amount must be more than zero',
    )
    expect(validateEdit({ ...editValues(original), amount: '-1' }, original).amount).toBeDefined()
  })

  it('leaves a two-sided amount alone, because it can never be sent', () => {
    const values = { ...editValues(TRANSFER), amount: 'not money at all' }

    expect(validateEdit(values, TRANSFER).amount).toBeUndefined()
  })

  it('requires a date', () => {
    const original = movement()

    expect(validateEdit({ ...editValues(original), transaction_date: '' }, original)).toEqual({
      transaction_date: 'A date is required',
    })
  })

  it('keeps the merchant and the note inside the column sizes', () => {
    const original = movement()

    expect(
      validateEdit({ ...editValues(original), merchant: 'x'.repeat(121) }, original).merchant,
    ).toBeDefined()
    expect(
      validateEdit({ ...editValues(original), note: 'x'.repeat(501) }, original).note,
    ).toBeDefined()
  })
})

describe('toUpdate', () => {
  it('sends nothing when nothing changed', () => {
    const original = movement()

    expect(toUpdate(editValues(original), original)).toEqual({})
    expect(hasChanges(editValues(original), original)).toBe(false)
  })

  it('sends only the field that changed', () => {
    const original = movement()
    const values = { ...editValues(original), transaction_date: '2026-10-02' }

    expect(toUpdate(values, original)).toEqual({ transaction_date: '2026-10-02' })
    expect(hasChanges(values, original)).toBe(true)
  })

  it('sends an amount as exact paise, and only when it really changed', () => {
    const original = movement()

    expect(toUpdate({ ...editValues(original), amount: '1,234.56' }, original)).toEqual({
      amount_paise: 123456,
    })
    expect(toUpdate({ ...editValues(original), amount: '500.00' }, original)).toEqual({})
  })

  it('clears a merchant or a note with null, and sends nothing for an untouched one', () => {
    const original = movement()

    expect(toUpdate({ ...editValues(original), note: '   ' }, original)).toEqual({ note: null })
    expect(toUpdate({ ...editValues(original), merchant: '' }, original)).toEqual({
      merchant: null,
    })
    expect(toUpdate({ ...editValues(original), merchant: 'Blinkit' }, original)).toEqual({})
  })

  it('trims what it sends', () => {
    const original = movement()

    expect(toUpdate({ ...editValues(original), note: '  bread  ' }, original)).toEqual({
      note: 'bread',
    })
  })

  it('never sends an amount for a two-sided movement', () => {
    const values = { ...editValues(TRANSFER), amount: '999', transaction_date: '2026-10-01' }

    expect(toUpdate(values, TRANSFER)).toEqual({ transaction_date: '2026-10-01' })
  })

  it('fails loudly rather than sending a wrong number', () => {
    const original = movement()

    expect(() => toUpdate({ ...editValues(original), amount: '10.005' }, original)).toThrow()
  })
})
