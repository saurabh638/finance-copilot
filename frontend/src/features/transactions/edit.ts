/**
 * The editor's values for a movement that already exists, and the change they
 * describe. Pure: nothing here talks to the API, so every rule is testable.
 */

import { InvalidMoneyError, formatPaise, parsePaise } from '../../lib/money'
import type { Transaction, TransactionUpdate } from './api'

/** What the editor holds while it is open. */
export interface EditFormValues {
  transaction_date: string
  amount: string
  merchant: string
  note: string
}

export type EditProblems = Partial<Record<keyof EditFormValues, string>>

const MERCHANT_MAX = 120
const NOTE_MAX = 500

/** Why a two-sided movement's amount is fixed. */
export const TRANSFER_AMOUNT_REASON =
  'A transfer is two sides that have to keep adding to zero, so its amount cannot be edited here.'

/**
 * True when the movement has a single posting, and so a single amount that can
 * be rewritten. The API refuses an amount change on anything else.
 */
export function canEditAmount(transaction: Transaction): boolean {
  return transaction.postings.length === 1
}

/** The amount the movement moved, as text, however many postings it has. */
function amountText(transaction: Transaction): string {
  const [only] = transaction.postings
  if (transaction.postings.length === 1 && only !== undefined) {
    return formatPaise(Math.abs(only.amount_paise))
  }

  return formatPaise(
    transaction.postings.reduce((total, posting) => total + Math.max(0, posting.amount_paise), 0),
  )
}

/** The form as it opens for a movement that already exists. */
export function editValues(transaction: Transaction): EditFormValues {
  return {
    transaction_date: transaction.transaction_date,
    amount: amountText(transaction),
    merchant: transaction.merchant ?? '',
    note: transaction.note ?? '',
  }
}

/** The amount in paise, refusing zero and negatives. */
function positivePaise(text: string): number {
  const paise = parsePaise(text)
  if (paise <= 0) {
    throw new InvalidMoneyError('an amount must be more than zero')
  }
  return paise
}

/** The server's rules, so a payload it would reject never leaves the form. */
export function validateEdit(values: EditFormValues, original: Transaction): EditProblems {
  const problems: EditProblems = {}

  // A two-sided amount is shown but never sent, so it is not judged here.
  if (canEditAmount(original)) {
    let paise: number | null = null
    try {
      paise = parsePaise(values.amount)
    } catch {
      problems.amount = 'Enter an amount like 1,23,456.78'
    }
    if (paise !== null && paise <= 0) {
      problems.amount = 'The amount must be more than zero'
    }
  }

  if (values.transaction_date === '') {
    problems.transaction_date = 'A date is required'
  }
  if (values.merchant.trim().length > MERCHANT_MAX) {
    problems.merchant = `Keep the merchant under ${MERCHANT_MAX} characters`
  }
  if (values.note.trim().length > NOTE_MAX) {
    problems.note = `Keep the note under ${NOTE_MAX} characters`
  }

  return problems
}

/** Text that is empty once trimmed becomes null: a cleared note is no note. */
function orNull(text: string): string | null {
  const trimmed = text.trim()
  return trimmed === '' ? null : trimmed
}

/**
 * The change to send: only the fields that differ from the movement as it
 * stands, because the API leaves an omitted field alone.
 *
 * The amount is parsed again here, so a caller who skips validation fails loudly
 * rather than sending a wrong number.
 */
export function toUpdate(values: EditFormValues, original: Transaction): TransactionUpdate {
  const update: TransactionUpdate = {}

  if (values.transaction_date !== original.transaction_date) {
    update.transaction_date = values.transaction_date
  }

  const merchant = orNull(values.merchant)
  if (merchant !== (original.merchant ?? null)) {
    update.merchant = merchant
  }

  const note = orNull(values.note)
  if (note !== (original.note ?? null)) {
    update.note = note
  }

  if (canEditAmount(original)) {
    const [only] = original.postings
    const paise = positivePaise(values.amount)
    if (only !== undefined && paise !== Math.abs(only.amount_paise)) {
      update.amount_paise = paise
    }
  }

  return update
}

/** True when there is something to send, and so something to save. */
export function hasChanges(values: EditFormValues, original: Transaction): boolean {
  try {
    return Object.keys(toUpdate(values, original)).length > 0
  } catch (error) {
    // Half-typed money is a change in progress, not a reason to go dead: let it
    // be submitted so the user is told what is wrong with it.
    if (error instanceof InvalidMoneyError) {
      return true
    }
    throw error
  }
}
