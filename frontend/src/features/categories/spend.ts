/**
 * Reading the spend report, as pure functions.
 *
 * The figures come from the server; what happens here is which line follows which,
 * how a share is worded, and which days a month covers. All of it is arithmetic
 * and dates, so it is tested without a browser and never touches a float.
 */

import type { SpendRow } from './api'

/** A branch, the names filed under it, and the share of the period it took. */
export interface SpendLine {
  row: SpendRow
  children: SpendRow[]
  /** Whole percent of the period's spending, for the bar. */
  sharePercent: number
}

/**
 * The report as lines: each branch with its own names under it.
 *
 * A name whose branch was removed still has money filed under it, so it is shown
 * as a line of its own rather than dropped - the same rule the tree follows.
 */
export function spendLines(rows: SpendRow[], totalPaise: number): SpendLine[] {
  const children = new Map<number, SpendRow[]>()
  for (const row of rows) {
    if (row.parent_id !== null) {
      children.set(row.parent_id, [...(children.get(row.parent_id) ?? []), row])
    }
  }

  const lines: SpendLine[] = rows
    .filter((row) => row.parent_id === null)
    .map((row) => line(row, children.get(row.id) ?? [], totalPaise))

  const placed = new Set(lines.flatMap((entry) => [entry.row, ...entry.children]))
  for (const row of rows) {
    if (!placed.has(row)) {
      lines.push(line(row, [], totalPaise))
    }
  }
  return lines
}

function line(row: SpendRow, children: SpendRow[], totalPaise: number): SpendLine {
  return { row, children, sharePercent: sharePercent(row.total_paise, totalPaise) }
}

/**
 * One figure as a whole percent of another.
 *
 * Integer arithmetic only, so a bar drawn from it cannot disagree with the figure
 * beside it, and nothing is said about a share of nothing.
 */
export function sharePercent(partPaise: number, wholePaise: number): number {
  if (wholePaise === 0) {
    return 0
  }
  return Math.round((partPaise * 100) / wholePaise)
}

/** The first and last day of the month a date falls in, as `YYYY-MM-DD`. */
export function monthRange(today: string): { from: string; to: string } {
  const [year, month] = today.split('-')
  const yearNumber = Number(year)
  const monthNumber = Number(month)

  if (!Number.isInteger(yearNumber) || !Number.isInteger(monthNumber)) {
    return { from: '', to: '' }
  }

  const last = daysInMonth(yearNumber, monthNumber)
  return { from: `${year}-${month}-01`, to: `${year}-${month}-${String(last).padStart(2, '0')}` }
}

/** How many days a month has, leap years included. */
function daysInMonth(year: number, month: number): number {
  // Day zero of the next month is the last day of this one, in UTC so that no
  // timezone can shift the answer by a day.
  return new Date(Date.UTC(year, month, 0)).getUTCDate()
}
