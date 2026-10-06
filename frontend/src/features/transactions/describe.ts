/** Turning a transaction from the API into the words one row shows. */

import { formatPaise } from '../../lib/money'
import type { PostingKind, Transaction } from './api'

/**
 * Labels for every posting kind the server can send.
 *
 * `satisfies Record<PostingKind, string>` makes a new kind on the server a
 * compile error here, rather than a row with no wording.
 */
export const POSTING_KIND_LABELS = {
  expense: 'Money out',
  income: 'Money in',
  transfer: 'Transfer',
  adjustment: 'Balance adjustment',
  interest: 'Interest',
  fee: 'Fee',
  investment: 'Investment',
} satisfies Record<PostingKind, string>

const UNKNOWN_ACCOUNT = 'Another account'
const NO_DESCRIPTION = 'No description'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** An account's name, or a neutral stand-in when it is not in the list. */
function nameOf(accountId: number, names: Map<number, string>): string {
  return names.get(accountId) ?? UNKNOWN_ACCOUNT
}

/**
 * Which of the three shapes a movement's postings are.
 *
 * One posting is an external flow; postings that sum to zero are a movement
 * between accounts; postings of a single sign are one external flow split
 * between categories. The ledger holds the same three shapes, so the words here
 * say what the ledger means: a split is spending or income, never a transfer.
 */
type MovementShape = 'single' | 'internal' | 'split'

function shapeOf(transaction: Transaction): MovementShape {
  if (transaction.postings.length === 1) {
    return 'single'
  }
  return signedTotal(transaction) === 0 ? 'internal' : 'split'
}

/** The postings added up as they are signed: the whole a movement moved. */
function signedTotal(transaction: Transaction): number {
  return transaction.postings.reduce((total, posting) => total + posting.amount_paise, 0)
}

/** The paise this movement moved, always positive. */
export function movementAmountPaise(transaction: Transaction): number {
  const [only] = transaction.postings
  if (transaction.postings.length === 1 && only !== undefined) {
    return Math.abs(only.amount_paise)
  }

  if (shapeOf(transaction) === 'split') {
    // One flow counted once, however many names it was filed under.
    return Math.abs(signedTotal(transaction))
  }

  // A movement between accounts: what arrived on the other side is what moved.
  return transaction.postings.reduce(
    (total, posting) => total + Math.max(0, posting.amount_paise),
    0,
  )
}

/** What the movement did, in words. */
export function movementLabel(transaction: Transaction): string {
  const [only] = transaction.postings
  if (transaction.postings.length === 1 && only !== undefined) {
    return POSTING_KIND_LABELS[only.kind]
  }

  if (shapeOf(transaction) === 'split' && only !== undefined) {
    return POSTING_KIND_LABELS[only.kind]
  }

  return POSTING_KIND_LABELS.transfer
}

/** The accounts involved: one for an expense, both sides for a transfer. */
export function movementParties(transaction: Transaction, names: Map<number, string>): string {
  const [only] = transaction.postings
  if (transaction.postings.length === 1 && only !== undefined) {
    return nameOf(only.account_id, names)
  }

  if (shapeOf(transaction) === 'split') {
    // A split leaves one account, so its name is said once and not twice.
    const accounts = [...new Set(transaction.postings.map((posting) => posting.account_id))]
    return accounts.map((accountId) => nameOf(accountId, names)).join(' → ')
  }

  const out = transaction.postings
    .filter((posting) => posting.amount_paise < 0)
    .map((posting) => nameOf(posting.account_id, names))
  const arrived = transaction.postings
    .filter((posting) => posting.amount_paise > 0)
    .map((posting) => nameOf(posting.account_id, names))

  return [...out, ...arrived].join(' → ')
}

/**
 * The amount as text.
 *
 * A single posting keeps its sign, so spending can never be mistaken for income.
 * A split is spending or income too, so it keeps the sign of its parts. A
 * transfer is neither, so it shows the amount moved and no sign at all.
 */
export function movementAmountText(transaction: Transaction): string {
  const [only] = transaction.postings
  if (transaction.postings.length === 1 && only !== undefined) {
    return formatPaise(only.amount_paise)
  }

  if (shapeOf(transaction) === 'split') {
    return formatPaise(signedTotal(transaction))
  }

  return formatPaise(movementAmountPaise(transaction))
}

/**
 * The categories a movement is filed under, as labels, without repeats.
 *
 * One name for a movement filed under one category, the parts' names for a split,
 * and nothing at all when there is nothing to say: an unfiled movement, a
 * transfer, or a category that is no longer in the tree. A name said twice would
 * read as two filings, so it is said once.
 */
export function movementFilings(transaction: Transaction, labels: Map<number, string>): string[] {
  const found = transaction.postings
    .map((posting) => (posting.category_id === null ? null : labels.get(posting.category_id)))
    .filter((label): label is string => label !== undefined && label !== null)

  return [...new Set(found)]
}

/** Merchant, else the note, else a neutral line so a row is never blank. */
export function movementTitle(transaction: Transaction): string {
  const merchant = transaction.merchant?.trim() ?? ''
  if (merchant !== '') {
    return merchant
  }

  const note = transaction.note?.trim() ?? ''
  return note === '' ? NO_DESCRIPTION : note
}

/** `2026-10-04` as `4 Oct 2026`. Anything unreadable is handed back as it came. */
export function displayDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  const monthName = MONTHS[Number(month) - 1]
  if (monthName === undefined || day === undefined || year === undefined) {
    return iso
  }

  return `${String(Number(day))} ${monthName} ${year}`
}
