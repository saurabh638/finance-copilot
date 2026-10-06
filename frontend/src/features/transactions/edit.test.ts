import { describe, expect, it } from 'vitest'

import type { Transaction } from './api'
import {
  SPLIT_AMOUNT_REASON,
  SPLIT_FILING_REASON,
  TRANSFER_AMOUNT_REASON,
  TRANSFER_FILING_REASON,
  amountReason,
  canEditAmount,
  canEditFiling,
  editValues,
  filingKind,
  filingReason,
  hasChanges,
  toUpdate,
  validateEdit,
} from './edit'

function movement(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: 7,
    transaction_date: '2026-10-04',
    merchant: 'Blinkit',
    note: 'milk',
    source: 'manual',
    postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense', category_id: null }],
    ...overrides,
  }
}

const TRANSFER = movement({
  id: 8,
  merchant: null,
  note: null,
  postings: [
    { id: 10, account_id: 1, amount_paise: -100000, kind: 'transfer', category_id: null },
    { id: 11, account_id: 2, amount_paise: 100000, kind: 'transfer', category_id: null },
  ],
})

/** A ₹500 shop filed as ₹300 of groceries and ₹200 of household things. */
const SPLIT = movement({
  id: 12,
  postings: [
    { id: 13, account_id: 1, amount_paise: -30000, kind: 'expense', category_id: 11 },
    { id: 14, account_id: 1, amount_paise: -20000, kind: 'expense', category_id: 12 },
  ],
})

/** A movement filed under a category, for the tests that change or clear it. */
function filed(category_id: number | null): Transaction {
  return movement({
    postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense', category_id }],
  })
}

describe('editValues', () => {
  it('opens with what the movement already says', () => {
    expect(editValues(movement())).toEqual({
      transaction_date: '2026-10-04',
      amount: '₹500.00',
      merchant: 'Blinkit',
      note: 'milk',
      category_id: '',
    })
  })

  it('opens with the category the movement is filed under', () => {
    const filed = movement({
      postings: [{ id: 9, account_id: 1, amount_paise: -50000, kind: 'expense', category_id: 7 }],
    })

    expect(editValues(filed).category_id).toBe('7')
  })

  it('opens with no filing for a movement whose postings are its filing', () => {
    expect(editValues(TRANSFER).category_id).toBe('')
  })

  it('opens a split at the whole amount, not at nothing', () => {
    expect(editValues(SPLIT).amount).toBe('₹500.00')
  })

  it('opens a transfer at the amount that moved', () => {
    expect(editValues(TRANSFER).amount).toBe('₹1,000.00')
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

describe('canEditFiling', () => {
  it('allows it when the movement has one posting', () => {
    expect(canEditFiling(filed(null))).toBe(true)
  })

  it('refuses it for a transfer, which has two sides and spends nothing', () => {
    expect(canEditFiling(TRANSFER)).toBe(false)
  })

  it('refuses it for a split, whose parts are the filing', () => {
    expect(canEditFiling(SPLIT)).toBe(false)
  })
})

describe('filingKind', () => {
  it('names the kind a posting is filed under', () => {
    expect(filingKind(filed(null))).toBe('expense')
    expect(
      filingKind(
        movement({
          postings: [
            { id: 9, account_id: 1, amount_paise: -50000, kind: 'adjustment', category_id: 7 },
          ],
        }),
      ),
    ).toBe('adjustment')
  })

  it('has no kind for a transfer or a split, which have no one filing', () => {
    expect(filingKind(TRANSFER)).toBeNull()
    expect(filingKind(SPLIT)).toBeNull()
  })
})

describe('amountReason and filingReason', () => {
  it('give no reason when there is nothing in the way', () => {
    expect(amountReason(filed(null))).toBeNull()
    expect(filingReason(filed(null))).toBeNull()
  })

  it('say what a transfer is, and what a split is', () => {
    expect(amountReason(TRANSFER)).toBe(TRANSFER_AMOUNT_REASON)
    expect(filingReason(TRANSFER)).toBe(TRANSFER_FILING_REASON)
    expect(amountReason(SPLIT)).toBe(SPLIT_AMOUNT_REASON)
    expect(filingReason(SPLIT)).toBe(SPLIT_FILING_REASON)
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

  it('files the movement under a category, and sends nothing when it did not change', () => {
    const original = filed(null)

    expect(toUpdate({ ...editValues(original), category_id: '7' }, original)).toEqual({
      category_id: 7,
    })
    expect(toUpdate({ ...editValues(filed(7)), category_id: '7' }, filed(7))).toEqual({})
  })

  it('unfiles a movement with an explicit null, which is the only way to say it', () => {
    const original = filed(7)

    expect(toUpdate({ ...editValues(original), category_id: '' }, original)).toEqual({
      category_id: null,
    })
  })

  it('counts a change of filing as something to save', () => {
    const original = filed(null)

    expect(hasChanges({ ...editValues(original), category_id: '7' }, original)).toBe(true)
  })

  it('never sends a filing for a movement whose parts are the filing', () => {
    const values = { ...editValues(SPLIT), category_id: '7' }

    // Nor an amount: the parts add up to the total, so the total cannot move
    // without them, and the API refuses one side of a split on its own.
    expect(toUpdate(values, SPLIT)).toEqual({})
    expect(toUpdate({ ...values, amount: '600' }, SPLIT)).toEqual({})
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
