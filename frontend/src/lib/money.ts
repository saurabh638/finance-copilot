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
