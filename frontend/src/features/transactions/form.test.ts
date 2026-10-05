import { describe, expect, it } from 'vitest'

import {
  blankMovement,
  todayIso,
  toPayload,
  validateMovement,
  type MovementFormValues,
} from './form'

/** A filled expense form, so each test changes only what it is about. */
function expense(overrides: Partial<MovementFormValues> = {}): MovementFormValues {
  return { ...blankMovement('2026-10-04'), amount: '500', account_id: '1', ...overrides }
}

function transfer(overrides: Partial<MovementFormValues> = {}): MovementFormValues {
  return {
    ...blankMovement('2026-10-04'),
    amount: '1000',
    kind: 'transfer',
    from_account_id: '1',
    to_account_id: '2',
    ...overrides,
  }
}

describe('todayIso', () => {
  it('reads the local day, not the UTC one', () => {
    // Just after midnight in India is still the previous day in UTC: a date
    // built from toISOString() would silently file the movement a day early.
    expect(todayIso(new Date(2026, 9, 4, 0, 30))).toBe('2026-10-04')
  })

  it('pads a single-digit month and day', () => {
    expect(todayIso(new Date(2026, 0, 5, 12, 0))).toBe('2026-01-05')
  })
})

describe('blankMovement', () => {
  it('starts as an expense dated the day it is given, with nothing filled in', () => {
    expect(blankMovement('2026-10-04')).toEqual({
      kind: 'expense',
      amount: '',
      transaction_date: '2026-10-04',
      account_id: '',
      from_account_id: '',
      to_account_id: '',
      merchant: '',
      note: '',
    })
  })
})

describe('validateMovement', () => {
  it('accepts a filled expense', () => {
    expect(validateMovement(expense())).toEqual({})
  })

  it('asks for an amount rather than sending an empty one', () => {
    expect(validateMovement(expense({ amount: '' })).amount).toBeDefined()
  })

  it('refuses zero and a negative amount', () => {
    expect(validateMovement(expense({ amount: '0' })).amount).toBe(
      'The amount must be more than zero',
    )
    expect(validateMovement(expense({ amount: '-500' })).amount).toBeDefined()
  })

  it('refuses text that is not money, and three decimal places', () => {
    expect(validateMovement(expense({ amount: 'abc' })).amount).toBeDefined()
    expect(validateMovement(expense({ amount: '12.345' })).amount).toBeDefined()
  })

  it('refuses an amount too large to hold exactly, rather than rounding it', () => {
    expect(validateMovement(expense({ amount: '99999999999999999999' })).amount).toBeDefined()
  })

  it('accepts Indian grouping and the rupee symbol', () => {
    expect(validateMovement(expense({ amount: '₹1,23,456.78' })).amount).toBeUndefined()
  })

  it('requires a date', () => {
    expect(validateMovement(expense({ transaction_date: '' })).transaction_date).toBe(
      'A date is required',
    )
  })

  it('requires one account for an expense or an income', () => {
    expect(validateMovement(expense({ account_id: '' })).account_id).toBe('Pick an account')
    expect(validateMovement(expense({ kind: 'income', account_id: '' })).account_id).toBe(
      'Pick an account',
    )
  })

  it('requires both sides of a transfer, and two different accounts', () => {
    expect(validateMovement(transfer({ from_account_id: '' })).account_id).toBe('Pick an account')
    expect(validateMovement(transfer({ to_account_id: '' })).to_account_id).toBe('Pick an account')
    expect(validateMovement(transfer({ to_account_id: '1' })).to_account_id).toBe(
      'Pick two different accounts',
    )
  })

  it('keeps the merchant and the note inside the column sizes', () => {
    expect(validateMovement(expense({ merchant: 'x'.repeat(121) })).merchant).toBeDefined()
    expect(validateMovement(expense({ note: 'x'.repeat(501) })).note).toBeDefined()
    expect(validateMovement(expense({ merchant: 'x'.repeat(120) })).merchant).toBeUndefined()
  })
})

describe('toPayload', () => {
  it('sends an expense as positive paise with the account and the day', () => {
    expect(
      toPayload(expense({ amount: '1,234.56', merchant: '  Blinkit  ', note: ' milk ' })),
    ).toEqual({
      kind: 'expense',
      account_id: 1,
      amount_paise: 123456,
      transaction_date: '2026-10-04',
      merchant: 'Blinkit',
      note: 'milk',
    })
  })

  it('sends an income the same way, with its own kind', () => {
    expect(toPayload(expense({ kind: 'income', amount: '20000' }))).toMatchObject({
      kind: 'income',
      account_id: 1,
      amount_paise: 2000000,
    })
  })

  it('sends a blank merchant and note as null, not as empty text', () => {
    expect(toPayload(expense())).toMatchObject({ merchant: null, note: null })
  })

  it('sends a transfer as two accounts and no single account', () => {
    const payload = toPayload(transfer({ amount: '1000', note: 'to savings' }))

    expect(payload).toEqual({
      kind: 'transfer',
      from_account_id: 1,
      to_account_id: 2,
      amount_paise: 100000,
      transaction_date: '2026-10-04',
      note: 'to savings',
      merchant: null,
    })
    expect(payload).not.toHaveProperty('account_id')
  })

  it('keeps every paise of a large amount exactly', () => {
    expect(toPayload(expense({ amount: '12,34,567.89' }))).toMatchObject({
      amount_paise: 123456789,
    })
  })

  it('never lets a negative amount through as a smaller number', () => {
    expect(() => toPayload(expense({ amount: '-500' }))).toThrow()
  })
})
