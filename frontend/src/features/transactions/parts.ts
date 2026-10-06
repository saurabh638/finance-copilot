/**
 * Splitting one amount between several categories.
 *
 * The user states one figure, because that is what the statement says, and files
 * it under as many names as it really was. The parts have to add up to that
 * figure exactly: the server refuses anything else, and the ledger counts the
 * money once. All of it is arithmetic over text, so it is tested here rather than
 * through a browser.
 */

import { InvalidMoneyError, formatPaise, parsePaise } from '../../lib/money'

/** A split needs two parts: one part is simply the whole amount. */
export const PARTS_MIN = 2

/** One part of a movement that was really several things. Text, as it was typed. */
export interface MovementPart {
  amount: string
  category_id: string
}

/** The amount in whole paise, or null while it is not money that can be used. */
function paiseOrNull(text: string): number | null {
  let paise: number
  try {
    paise = parsePaise(text)
  } catch (error) {
    if (error instanceof InvalidMoneyError) {
      return null
    }
    throw error
  }
  return paise > 0 ? paise : null
}

/** The amount again, but refused loudly: only called once validation has passed. */
function paise(text: string): number {
  const found = paiseOrNull(text)
  if (found === null) {
    throw new InvalidMoneyError('a part needs an amount of more than zero')
  }
  return found
}

/** A blank part: no amount and no category. */
export function blankPart(): MovementPart {
  return { amount: '', category_id: '' }
}

/** A split starts with two blank parts. */
export function blankParts(): MovementPart[] {
  return [blankPart(), blankPart()]
}

/** One more blank part at the end. */
export function addPart(parts: MovementPart[]): MovementPart[] {
  return [...parts, blankPart()]
}

/** Take one part away. With two left there is nothing to take away: that is the whole. */
export function removePart(parts: MovementPart[], index: number): MovementPart[] {
  if (parts.length <= PARTS_MIN) {
    return parts
  }
  return parts.filter((_, at) => at !== index)
}

/** One part's amount in whole paise, or null while it is not money to use yet. */
export function partPaise(part: MovementPart): number | null {
  return paiseOrNull(part.amount)
}

/** What the parts add up to so far. A part not written yet counts as nothing. */
export function allocatedPaise(parts: MovementPart[]): number {
  return parts.reduce((total, part) => total + (partPaise(part) ?? 0), 0)
}

/**
 * What is left of the amount after the parts, or null until the amount is money.
 *
 * This is the figure a new part is offered, and it goes negative when the parts
 * ask for more than the whole - which validation then refuses.
 */
export function remainingPaise(amount: string, parts: MovementPart[]): number | null {
  const whole = paiseOrNull(amount)
  return whole === null ? null : whole - allocatedPaise(parts)
}

/**
 * The trouble with a split, or null when the parts are ready to send.
 *
 * One message at a time, because the first thing that is wrong is the thing to
 * fix. An amount that is not money yet says nothing here: the amount field
 * already says it, and two messages about one number would be noise.
 */
export function validateParts(amount: string, parts: MovementPart[]): string | null {
  const whole = paiseOrNull(amount)
  if (whole === null) {
    return null
  }

  if (parts.length < PARTS_MIN) {
    // Spelled out, because a sentence with a word in it reads better than one
    // with a digit; the constant above still holds the rule itself.
    return 'A split needs at least two parts'
  }
  if (parts.some((part) => partPaise(part) === null)) {
    return 'Every part needs an amount'
  }
  if (parts.some((part) => part.category_id === '')) {
    return 'Every part needs a category'
  }

  const difference = whole - allocatedPaise(parts)
  if (difference > 0) {
    return `The parts must add up to ${formatPaise(whole)}; ${formatPaise(difference)} is still to allocate`
  }
  if (difference < 0) {
    return `The parts must add up to ${formatPaise(whole)}; ${formatPaise(-difference)} too much`
  }
  return null
}

/** The parts as the API takes them: paise and a category, in the order given. */
export function partsPayload(
  parts: MovementPart[],
): { amount_paise: number; category_id: number }[] {
  return parts.map((part) => ({
    amount_paise: paise(part.amount),
    category_id: Number(part.category_id),
  }))
}
