/** Dates the screens need, kept in one place. */

/**
 * The local day as `YYYY-MM-DD`.
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
