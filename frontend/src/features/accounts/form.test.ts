import { describe, expect, it } from 'vitest'

import type { Account } from './api'
import {
  EMPTY_ACCOUNT_FORM,
  type AccountFormValues,
  accountToFormValues,
  toAccountUpdate,
  toNewAccount,
  validateAccountForm,
} from './form'

const SAVINGS: Account = {
  id: 1,
  name: 'SBI',
  alias: 'hdfc',
  type: 'savings',
  purpose: 'salary',
  capture_mode: 'statement_import',
  parent_id: null,
  opening_balance_paise: 12_345_678,
  opening_date: '2026-04-01',
  statement_day: null,
  due_day: null,
  is_active: true,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

const FILLED: AccountFormValues = {
  ...EMPTY_ACCOUNT_FORM,
  name: 'SBI',
  opening_balance: '₹1,23,456.78',
  opening_date: '2026-04-01',
}

describe('accountToFormValues', () => {
  it('shows the balance the way the list does', () => {
    expect(accountToFormValues(SAVINGS).opening_balance).toBe('₹1,23,456.78')
  })

  it('round-trips the balance back to exactly the same paise', () => {
    const values = accountToFormValues(SAVINGS)

    expect(toNewAccount(values).account.opening_balance_paise).toBe(SAVINGS.opening_balance_paise)
    expect(toAccountUpdate(values, true).opening_balance_paise).toBe(SAVINGS.opening_balance_paise)
  })

  it('leaves an unset card day and parent empty rather than "0" or "null"', () => {
    const values = accountToFormValues(SAVINGS)

    expect(values.statement_day).toBe('')
    expect(values.due_day).toBe('')
    expect(values.parent_id).toBe('')
  })

  it('seeds a pot with its parent as text', () => {
    const values = accountToFormValues({ ...SAVINGS, type: 'pot', parent_id: 7 })

    expect(values.parent_id).toBe('7')
  })

  it('never carries a rate over, because a rate is appended, not edited', () => {
    expect(accountToFormValues(SAVINGS).rate).toBe('')
  })
})

describe('toNewAccount', () => {
  it('sends null, never day zero, for a card day left empty', () => {
    const values = { ...FILLED, type: 'credit_card' as const }

    const account = toNewAccount(values).account

    expect(account.statement_day).toBeNull()
    expect(account.due_day).toBeNull()
  })

  it('keeps the first of the month as day 1, not null', () => {
    const values = { ...FILLED, type: 'credit_card' as const, statement_day: '1' }

    expect(toNewAccount(values).account.statement_day).toBe(1)
  })
})

describe('toAccountUpdate', () => {
  it('never sends a type, because the server will not change one', () => {
    expect(Object.keys(toAccountUpdate(FILLED, true))).not.toContain('type')
  })

  it('sends the active flag and paise, and nothing about a rate', () => {
    const update = toAccountUpdate(FILLED, false)

    expect(update.is_active).toBe(false)
    expect(update.opening_balance_paise).toBe(12_345_678)
    expect(Object.keys(update)).not.toContain('rate')
  })

  it('keeps card days for a card and clears them for anything else', () => {
    const card = toAccountUpdate(
      { ...FILLED, type: 'credit_card', statement_day: '5', due_day: '' },
      true,
    )
    const savings = toAccountUpdate({ ...FILLED, statement_day: '5' }, true)

    expect(card.statement_day).toBe(5)
    expect(card.due_day).toBeNull()
    expect(savings.statement_day).toBeNull()
  })

  it('refuses an amount the money parser would refuse', () => {
    expect(() => toAccountUpdate({ ...FILLED, opening_balance: '10.005' }, true)).toThrow()
  })
})

describe('validateAccountForm', () => {
  it('accepts a complete account', () => {
    expect(validateAccountForm(FILLED)).toEqual({})
  })
})

describe('the alias', () => {
  it('starts blank, because an alias is optional', () => {
    expect(EMPTY_ACCOUNT_FORM.alias).toBe('')
  })

  it('seeds the edit form from the account', () => {
    expect(accountToFormValues(SAVINGS).alias).toBe('hdfc')
  })

  it('shows a blank box for an account that has no alias', () => {
    expect(accountToFormValues({ ...SAVINGS, alias: null }).alias).toBe('')
  })

  it('goes over the wire trimmed', () => {
    const values = { ...FILLED, alias: '  hdfc  ' }

    expect(toNewAccount(values).account.alias).toBe('hdfc')
    expect(toAccountUpdate(values, true).alias).toBe('hdfc')
  })

  it('sends no alias at all when the box is empty', () => {
    const values = { ...FILLED, alias: '   ' }

    expect(toNewAccount(values).account.alias).toBeNull()
    expect(toAccountUpdate(values, true).alias).toBeNull()
  })

  it('refuses an alias longer than the server takes', () => {
    expect(validateAccountForm({ ...FILLED, alias: 'x'.repeat(41) }).alias).toBe(
      'Keep the alias under 40 characters',
    )
    expect(validateAccountForm({ ...FILLED, alias: 'x'.repeat(40) }).alias).toBeUndefined()
  })
})
