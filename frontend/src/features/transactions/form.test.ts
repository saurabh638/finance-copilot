import { describe, expect, it } from 'vitest'

import { blankMovement, toPayload, validateMovement, type MovementFormValues } from './form'

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

describe('blankMovement', () => {
  it('starts as an expense dated the day it is given, with nothing filled in', () => {
    expect(blankMovement('2026-10-04')).toEqual({
      kind: 'expense',
      amount: '',
      transaction_date: '2026-10-04',
      account_id: '',
      from_account_id: '',
      to_account_id: '',
      category_id: '',
      split: false,
      parts: [
        { amount: '', category_id: '' },
        { amount: '', category_id: '' },
      ],
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

  it('refuses a split whose parts do not add up to the amount', () => {
    expect(
      validateMovement(
        expense({
          amount: '500',
          split: true,
          parts: [
            { amount: '300', category_id: '11' },
            { amount: '100', category_id: '12' },
          ],
        }),
      ).parts,
    ).toBe('The parts must add up to ₹500.00; ₹100.00 is still to allocate')
  })

  it('refuses a split with a part that has no category', () => {
    expect(
      validateMovement(
        expense({
          amount: '500',
          split: true,
          parts: [
            { amount: '300', category_id: '11' },
            { amount: '200', category_id: '' },
          ],
        }),
      ).parts,
    ).toBe('Every part needs a category')
  })

  it('says nothing about the parts when the split mode is off', () => {
    expect(validateMovement(expense({ amount: '500' })).parts).toBeUndefined()
  })

  it('says nothing about the parts until the amount itself is money', () => {
    const problems = validateMovement(
      expense({
        amount: 'abc',
        split: true,
        parts: [
          { amount: '300', category_id: '11' },
          { amount: '200', category_id: '12' },
        ],
      }),
    )

    expect(problems.parts).toBeUndefined()
    expect(problems.amount).toBeDefined()
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

  it('files money spent under the category chosen', () => {
    expect(toPayload(expense({ category_id: '7' }))).toMatchObject({
      kind: 'expense',
      category_id: 7,
    })
  })

  it('files money received under an earning category', () => {
    expect(toPayload(expense({ kind: 'income', category_id: '4' }))).toMatchObject({
      kind: 'income',
      category_id: 4,
    })
  })

  it('leaves the filing out when no category is chosen, rather than sending null', () => {
    expect(toPayload(expense())).not.toHaveProperty('category_id')
  })

  it('never files a transfer under a category, whatever the form was left holding', () => {
    const payload = toPayload(transfer({ category_id: '7' }))

    expect(payload.kind).toBe('transfer')
    expect(payload).not.toHaveProperty('category_id')
  })

  it('sends a split as the parts and the whole amount, with no single category', () => {
    const payload = toPayload(
      expense({
        amount: '500',
        category_id: '7',
        split: true,
        parts: [
          { amount: '300', category_id: '11' },
          { amount: '200', category_id: '12' },
        ],
      }),
    )

    expect(payload).toMatchObject({
      kind: 'expense',
      amount_paise: 50000,
      parts: [
        { amount_paise: 30000, category_id: 11 },
        { amount_paise: 20000, category_id: 12 },
      ],
    })
    expect(payload).not.toHaveProperty('category_id')
  })

  it('leaves a split’s parts behind when the split mode is off', () => {
    const payload = toPayload(
      expense({
        category_id: '7',
        split: false,
        parts: [{ amount: '500', category_id: '11' }],
      }),
    )

    expect(payload).toMatchObject({ category_id: 7 })
    expect(payload).not.toHaveProperty('parts')
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
