/**
 * The editor's values for a movement that already exists, and the change they
 * describe. Pure: nothing here talks to the API, so every rule is testable.
 */

import { InvalidMoneyError, formatPaise, parsePaise } from '../../lib/money'
import type { CategoryKind } from '../categories/api'
import type { PostingKind, Transaction, TransactionUpdate } from './api'
import { movementAmountPaise } from './describe'

/** What the editor holds while it is open. */
export interface EditFormValues {
  transaction_date: string
  amount: string
  merchant: string
  note: string
  /** The category as text, or empty text for none. */
  category_id: string
}

export type EditProblems = Partial<Record<keyof EditFormValues, string>>

const MERCHANT_MAX = 120
const NOTE_MAX = 500

/** Why a two-sided movement's amount is fixed. */
export const TRANSFER_AMOUNT_REASON =
  'A transfer is two sides that have to keep adding to zero, so its amount cannot be edited here.'

/** Why a split's amount is fixed: it is the total its parts must add up to. */
export const SPLIT_AMOUNT_REASON =
  'This movement is split between categories, so its parts are the amount; to change it, remove the movement and record it again.'

/** Why a transfer has no filing to change. */
export const TRANSFER_FILING_REASON =
  'A transfer moves money without spending it, so it is filed under nothing.'

/** Why a split's filing cannot be changed here: each part has its own. */
export const SPLIT_FILING_REASON =
  'This movement is split between categories, so its parts are the filing; to change them, remove the movement and record it again.'

/** The kind of name each posting may be filed under, as the server accepts them. */
const FILING_KINDS: Partial<Record<PostingKind, CategoryKind>> = {
  expense: 'expense',
  income: 'income',
  adjustment: 'adjustment',
}

/** Why the filing of a split cannot be changed here. */
export const FILING_REASON =
  'This movement is split between categories, so its parts are the filing; a part is changed by removing the movement and recording it again.'

/**
 * True when the movement has a single posting, and so a single amount that can
 * be rewritten. The API refuses an amount change on anything else.
 */
export function canEditAmount(transaction: Transaction): boolean {
  return transaction.postings.length === 1
}

/**
 * True when the movement's filing can be changed here.
 *
 * A split files each of its postings under its own category, so there is no one
 * answer to change: the API refuses it for the same reason.
 */
export function canEditFiling(transaction: Transaction): boolean {
  return transaction.postings.length === 1
}

/**
 * The kind of name this movement may be filed under, or null when it has no one
 * filing to change: a split files each posting itself, and a transfer files none.
 */
export function filingKind(transaction: Transaction): CategoryKind | null {
  const [only] = transaction.postings
  if (only === undefined || !canEditFiling(transaction)) {
    return null
  }
  return FILING_KINDS[only.kind] ?? null
}

/** Why the amount cannot be rewritten here, or null when it can be. */
export function amountReason(transaction: Transaction): string | null {
  if (canEditAmount(transaction)) {
    return null
  }
  const [first] = transaction.postings
  return first?.kind === 'transfer' ? TRANSFER_AMOUNT_REASON : SPLIT_AMOUNT_REASON
}

/** Why the filing cannot be changed here, or null when it can be. */
export function filingReason(transaction: Transaction): string | null {
  if (canEditFiling(transaction)) {
    return null
  }
  const [first] = transaction.postings
  return first?.kind === 'transfer' ? TRANSFER_FILING_REASON : SPLIT_FILING_REASON
}

/**
 * The amount the movement moved, as text, however many postings it has.
 *
 * The arithmetic lives in `describe.ts`, where the list row reads the same
 * figure: one implementation, so a split can never read as ₹0.00 in one place
 * and as its whole in the other. The editor shows it unsigned, because the
 * field takes a positive figure and the direction is not edited here.
 */
function amountText(transaction: Transaction): string {
  return formatPaise(movementAmountPaise(transaction))
}

/** The form as it opens for a movement that already exists. */
export function editValues(transaction: Transaction): EditFormValues {
  const [only] = transaction.postings
  const filing = canEditFiling(transaction) && only !== undefined ? only.category_id : null

  return {
    transaction_date: transaction.transaction_date,
    amount: amountText(transaction),
    merchant: transaction.merchant ?? '',
    note: transaction.note ?? '',
    category_id: filing === null ? '' : String(filing),
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

  // Clearing the filing is said with an explicit null: the API leaves an omitted
  // field alone, so nothing else could tell it to forget the old category.
  if (canEditFiling(original)) {
    const [only] = original.postings
    const chosen = values.category_id === '' ? null : Number(values.category_id)
    if (only !== undefined && chosen !== only.category_id) {
      update.category_id = chosen
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
