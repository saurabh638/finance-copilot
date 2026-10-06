/**
 * The daily screen's rules, as pure functions.
 *
 * What a suggestion fills in, what the streak says, and what a lump entry claims
 * to cover: all of it is text and dates, so it is settled here rather than in a
 * screen that cannot be tested without a browser.
 */

import { formatPaise } from '../../lib/money'
import { displayDate } from '../transactions/describe'
import type { Suggestion, Transaction } from '../transactions/api'
import type { MovementFormValues } from '../transactions/form'

/** One day as `YYYY-MM-DD`, in the same shape the API takes. */
const ISO = /^(\d{4})-(\d{2})-(\d{2})$/

/**
 * What one tap on a chip fills in.
 *
 * The name, the account, the category and the amount are all taken from how the
 * movement was recorded last, so one tap is one movement. A suggestion that
 * remembers no category leaves the field empty rather than guessing one.
 */
export function filledBy(suggestion: Suggestion): Partial<MovementFormValues> {
  return {
    amount: formatPaise(suggestion.amount_paise),
    merchant: suggestion.merchant,
    account_id: String(suggestion.account_id),
    category_id: suggestion.category_id === null ? '' : String(suggestion.category_id),
  }
}

/**
 * What the run of days says.
 *
 * Nothing here scolds: a run that has ended is not a loss, the day is simply not
 * finished, and the wording always offers the next step rather than counting what
 * was missed. MILESTONES.md asks for exactly that.
 */
export function streakWords(days: number, todayRecorded: boolean): string {
  if (days === 0) {
    return 'Today is a good day to start'
  }
  if (days === 1 && todayRecorded) {
    return 'Today is recorded'
  }
  if (days === 1) {
    return 'Yesterday was recorded'
  }
  return todayRecorded
    ? `${String(days)} days in a row`
    : `${String(days)} days in a row, up to yesterday`
}

/** How many days a lump covers, counting both ends, or 0 when a date is unreadable. */
export function catchUpDays(from: string, to: string): number {
  const start = dayNumber(from)
  const end = dayNumber(to)
  if (start === null || end === null || end < start) {
    return 0
  }
  return end - start + 1
}

/** What the catch-up note says, so a lump explains itself in the list later. */
export function catchUpNote(from: string, to: string): string {
  const days = catchUpDays(from, to)
  if (days === 0) {
    return 'Catch-up'
  }
  if (days === 1) {
    return `Catch-up for ${displayDate(to)}`
  }
  return `Catch-up for ${String(days)} days to ${displayDate(to)}`
}

/** A whole day as a number, for counting between two of them without a clock. */
function dayNumber(iso: string): number | null {
  const parts = ISO.exec(iso)
  if (parts === null) {
    return null
  }
  const [, year, month, day] = parts
  return Date.UTC(Number(year), Number(month) - 1, Number(day)) / (24 * 60 * 60 * 1000)
}

/**
 * The movement to copy for "same as yesterday", or null when that day is empty.
 *
 * The list arrives newest first, so the first one dated that day is the last
 * thing that happened on it — which is what "same as yesterday" means when the
 * day held more than one thing.
 */
export function movementOn(movements: Transaction[], day: string): Transaction | null {
  return movements.find((movement) => movement.transaction_date === day) ?? null
}
