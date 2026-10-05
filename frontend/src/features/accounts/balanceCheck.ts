/**
 * The balance-check panel's rules, and the words it uses.
 *
 * Wording and validation only: every figure the panel shows comes from the API,
 * because money arithmetic does not belong in the browser. The one subtraction
 * here is a sign, so that a figure can be read as "less than" or "more than".
 */

import { formatPaise, parsePaise } from '../../lib/money'

/**
 * What a large difference might mean, in the words SPEC.md uses.
 *
 * The nudge asks, it does not accuse: a missing entry is usually ordinary life,
 * not carelessness.
 */
export const NUDGE =
  'That is a large difference. Worth a quick look first: a recurring charge you ' +
  'forgot, a statement that is not imported yet, or an account that is not in the app?'

/** The first day of the month a date falls in, which is what the share expects. */
export function monthStart(today: string): string {
  return `${today.slice(0, 7)}-01`
}

/** What, if anything, is wrong with the balance the user typed. */
export function validateStated(text: string): string | undefined {
  if (text.trim() === '') {
    return 'Enter the balance your bank shows'
  }

  try {
    parsePaise(text)
  } catch {
    return 'Enter an amount like 1,23,456.78'
  }

  // Zero is a real balance, and a card's balance is negative. Both are allowed.
  return undefined
}

/** The difference as a sentence. The figure arrives from the API, signed. */
export function differenceSentence(difference_paise: number): string {
  if (difference_paise === 0) {
    return 'The ledger matches the bank exactly.'
  }
  if (difference_paise < 0) {
    return `${formatPaise(-difference_paise)} less than the ledger says.`
  }
  return `${formatPaise(difference_paise)} more than the ledger says.`
}

/**
 * What the one button says, or null when there is nothing to post.
 *
 * Money short is written off; money found is recorded. Both post the same
 * `adjustment` posting, but only one of them is a loss.
 */
export function writeOffLabel(difference_paise: number): string | null {
  if (difference_paise === 0) {
    return null
  }
  if (difference_paise < 0) {
    return `Write off ${formatPaise(-difference_paise)}`
  }
  return `Record ${formatPaise(difference_paise)}`
}
