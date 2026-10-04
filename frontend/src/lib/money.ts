export const RUPEE_SYMBOL = '₹'

/**
 * Format a whole number of paise as Indian-grouped text, e.g. `₹1,23,456.78`.
 *
 * Amounts are integers only; there is no floating-point arithmetic here. The
 * paise are split into rupees and the last two paise by string slicing.
 */
export function formatPaise(paise: number): string {
  if (!Number.isInteger(paise)) {
    throw new TypeError(`money must be whole paise, got ${paise}`)
  }

  const sign = paise < 0 ? '-' : ''
  const digits = String(Math.abs(paise)).padStart(3, '0')
  const rupees = digits.slice(0, -2)
  const fraction = digits.slice(-2)
  return `${sign}${RUPEE_SYMBOL}${groupIndian(rupees)}.${fraction}`
}

/** Group digits Indian-style: last three, then groups of two. */
function groupIndian(rupees: string): string {
  if (rupees.length <= 3) {
    return rupees
  }

  const tail = rupees.slice(-3)
  let head = rupees.slice(0, -3)
  const groups: string[] = []
  while (head.length > 2) {
    groups.unshift(head.slice(-2))
    head = head.slice(0, -2)
  }
  if (head.length > 0) {
    groups.unshift(head)
  }
  groups.push(tail)
  return groups.join(',')
}

/** Raised when text cannot be read as a money amount. */
export class InvalidMoneyError extends Error {}

const PAISE_PER_RUPEE = 100

// The integer part is either plain digits or comma-separated groups, where the
// first group has 1-3 digits and later groups have 2-3, so Indian and Western
// grouping both parse. At most two decimal places: more is rejected, never
// rounded. This is backend/app/core/money.py's rule, kept identical on purpose.
const AMOUNT_PATTERN = /^(?:\d+|\d{1,3}(?:,\d{2,3})*)(?:\.\d{1,2})?$/

/**
 * Parse money text into whole paise, e.g. `₹1,23,456.78` into 12345678.
 *
 * Mirrors the backend's `parse_paise`, so the form and the API agree on what a
 * valid amount is. Integers only: nothing here goes through a float, and an
 * amount too large to hold exactly is rejected rather than silently rounded.
 */
export function parsePaise(text: string): number {
  if (typeof text !== 'string') {
    throw new TypeError(`money must be parsed from text, never from a number: ${typeof text}`)
  }

  let cleaned = text.trim()
  let sign = 1
  if (cleaned.startsWith('-')) {
    sign = -1
    cleaned = cleaned.slice(1).trimStart()
  }
  if (cleaned.startsWith(RUPEE_SYMBOL)) {
    cleaned = cleaned.slice(RUPEE_SYMBOL.length).trim()
  }
  if (!AMOUNT_PATTERN.test(cleaned)) {
    throw new InvalidMoneyError(`not a valid money amount: ${text}`)
  }

  // Sliced by string, so the digits are never a float on the way in.
  const dot = cleaned.indexOf('.')
  const rupeesText = dot === -1 ? cleaned : cleaned.slice(0, dot)
  const fractionText = dot === -1 ? '' : cleaned.slice(dot + 1)
  const rupees = Number(rupeesText.replaceAll(',', ''))
  const paise = sign * (rupees * PAISE_PER_RUPEE + Number(fractionText.padEnd(2, '0')))

  if (!Number.isSafeInteger(paise)) {
    throw new InvalidMoneyError(`amount is too large to hold exactly: ${text}`)
  }
  return paise
}
