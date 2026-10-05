/** The movement form's values, its rules, and the payload they produce. */

import { InvalidMoneyError, parsePaise } from '../../lib/money'
import type { MovementCreate } from './api'

/** The three things a person records by hand. Everything else arrives later. */
export type MovementKind = 'expense' | 'income' | 'transfer'

/**
 * Labels for the directions the form offers.
 *
 * `satisfies Record<..., string>` makes a missing direction a compile error.
 * The wording is plain on purpose: "money spent" needs no explaining.
 */
export const KIND_LABELS = {
  expense: 'Money spent',
  income: 'Money received',
  transfer: 'Transfer between accounts',
} satisfies Record<MovementKind, string>

export const KINDS = Object.keys(KIND_LABELS) as MovementKind[]

/** Every value is text: inputs hold text, and nothing is parsed until submit. */
export interface MovementFormValues {
  kind: MovementKind
  amount: string
  transaction_date: string
  account_id: string
  from_account_id: string
  to_account_id: string
  merchant: string
  note: string
}

/** The local day as `YYYY-MM-DD`.
 *
 * Built from local parts, never from `toISOString()`: that converts to UTC, so
 * an early-morning entry in India would be filed on the previous day.
 */
export function todayIso(now: Date = new Date()): string {
  const year = String(now.getFullYear()).padStart(4, '0')
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** An empty form, dated the day it is opened. */
export function blankMovement(today: string): MovementFormValues {
  return {
    kind: 'expense',
    amount: '',
    transaction_date: today,
    account_id: '',
    from_account_id: '',
    to_account_id: '',
    merchant: '',
    note: '',
  }
}

export type MovementProblems = Partial<Record<keyof MovementFormValues, string>>

const MERCHANT_MAX = 120
const NOTE_MAX = 500

/**
 * The amount in paise, refusing zero and negatives.
 *
 * The API takes a positive amount and reads the direction from the kind, so a
 * minus sign typed here would be a second, disagreeing answer.
 */
function positivePaise(text: string): number {
  const paise = parsePaise(text)
  if (paise <= 0) {
    throw new InvalidMoneyError('an amount must be more than zero')
  }
  return paise
}

/** The server's rules, so a payload it would reject never leaves the form. */
export function validateMovement(values: MovementFormValues): MovementProblems {
  const problems: MovementProblems = {}

  let paise: number | null = null
  try {
    paise = parsePaise(values.amount)
  } catch {
    problems.amount = 'Enter an amount like 1,23,456.78'
  }
  if (paise !== null && paise <= 0) {
    problems.amount = 'The amount must be more than zero'
  }

  if (values.transaction_date === '') {
    problems.transaction_date = 'A date is required'
  }

  if (values.kind === 'transfer') {
    if (values.from_account_id === '') {
      problems.account_id = 'Pick an account'
    }
    if (values.to_account_id === '') {
      problems.to_account_id = 'Pick an account'
    } else if (values.to_account_id === values.from_account_id) {
      problems.to_account_id = 'Pick two different accounts'
    }
  } else if (values.account_id === '') {
    problems.account_id = 'Pick an account'
  }

  if (values.merchant.trim().length > MERCHANT_MAX) {
    problems.merchant = `Keep the merchant under ${MERCHANT_MAX} characters`
  }
  if (values.note.trim().length > NOTE_MAX) {
    problems.note = `Keep the note under ${NOTE_MAX} characters`
  }

  return problems
}

/** Text that is empty once trimmed becomes null: a blank note is no note. */
function orNull(text: string): string | null {
  const trimmed = text.trim()
  return trimmed === '' ? null : trimmed
}

/**
 * The payload for the API.
 *
 * Only called once `validateMovement` is satisfied; the amount is parsed again
 * here so that a caller who skips validation fails loudly rather than sending a
 * wrong number.
 */
export function toPayload(values: MovementFormValues): MovementCreate {
  const amount_paise = positivePaise(values.amount)
  const shared = {
    amount_paise,
    transaction_date: values.transaction_date,
    note: orNull(values.note),
  }

  if (values.kind === 'transfer') {
    return {
      kind: 'transfer',
      from_account_id: Number(values.from_account_id),
      to_account_id: Number(values.to_account_id),
      merchant: null,
      ...shared,
    }
  }

  return {
    kind: values.kind,
    account_id: Number(values.account_id),
    merchant: orNull(values.merchant),
    ...shared,
  }
}
