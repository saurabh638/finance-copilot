/**
 * The interest panel's rules, as pure functions.
 *
 * What a period reads like, what a rate reads like, and how the bank's figure is
 * described when it differs from the ledger's own. Nothing here works out interest:
 * the arithmetic is the server's, and this only says what it means.
 */

import { formatPaise, parsePaise } from '../../lib/money'
import { displayDate } from '../transactions/describe'
import type { InterestCredit } from './api'

/** One period in words: a single day once, anything longer as its two ends. */
export function periodWords(credit: InterestCredit): string {
  if (credit.period_start === credit.period_end) {
    return displayDate(credit.period_start)
  }
  return `${displayDate(credit.period_start)} to ${displayDate(credit.period_end)}`
}

/**
 * A rate in words.
 *
 * The server stores it at the column's scale, so 7.1 arrives as "7.1000". The
 * zeros are trimmed as text rather than by turning the rate into a number, so the
 * exact value reaches the screen untouched.
 */
export function rateWords(percent: string): string {
  const trimmed = percent.includes('.') ? percent.replace(/0+$/, '').replace(/\.$/, '') : percent
  return `${trimmed}% a year`
}

/**
 * What to say when the bank paid something other than the ledger worked out.
 *
 * Nothing at all when the period has not been credited, and nothing when the two
 * figures agree: silence is the right answer for agreement, and the difference is
 * the only place where the stated day-count convention can be seen to be wrong.
 */
export function differenceWords(credit: InterestCredit): string | null {
  const credited = credit.credited_paise
  if (credited === null || credited === credit.computed_paise) {
    return null
  }

  const gap = credited - credit.computed_paise
  const amount = formatPaise(Math.abs(gap))
  return gap > 0
    ? `The bank paid ${amount} more than the ledger worked out`
    : `The bank paid ${amount} less than the ledger worked out`
}

/**
 * What is wrong with the figure typed for the bank's credit, or null when it is
 * usable.
 *
 * An empty field is not a problem: it means the ledger's own figure is the one to
 * credit, which is the common case. A figure has to be readable and more than
 * nothing, because a credit of zero is not a credit and the server would refuse it.
 */
export function bankFigureProblem(text: string): string | null {
  if (text.trim() === '') {
    return null
  }

  try {
    if (parsePaise(text) <= 0) {
      return 'The bank’s figure must be more than zero'
    }
    return null
  } catch {
    return 'Enter the figure like 581.50, or leave it empty to use the ledger’s'
  }
}
