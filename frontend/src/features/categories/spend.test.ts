import { describe, expect, it } from 'vitest'

import type { SpendRow } from './api'
import { monthRange, sharePercent, spendLines } from './spend'

/** One row of the report, as the API returns it. */
function row(
  id: number,
  name: string,
  parent_id: number | null,
  direct_paise: number,
  total_paise: number = direct_paise,
): SpendRow {
  return { id, name, parent_id, kind: 'expense', direct_paise, total_paise }
}

const ROWS: SpendRow[] = [
  row(1, 'Food & groceries', null, 0, 80_000),
  row(2, 'Groceries', 1, 60_000),
  row(3, 'Eating out', 1, 20_000),
  row(4, 'Transport', null, 20_000),
]

describe('spendLines', () => {
  it('puts the names under the branch they belong to', () => {
    const lines = spendLines(ROWS, 100_000)

    expect(lines.map((line) => line.row.name)).toEqual(['Food & groceries', 'Transport'])
    expect(lines[0]?.children.map((child) => child.name)).toEqual(['Groceries', 'Eating out'])
    expect(lines[1]?.children).toEqual([])
  })

  it('shows a name whose branch is gone as a line of its own, at the end', () => {
    const orphan = row(9, 'Chemist', 99, 5_000)

    const lines = spendLines([...ROWS, orphan], 100_000)

    expect(lines).toHaveLength(3)
    expect(lines[2]?.row.name).toBe('Chemist')
  })

  it('says nothing at all about an empty report', () => {
    expect(spendLines([], 0)).toEqual([])
  })

  it('gives every line and its children a share of the period', () => {
    const lines = spendLines(ROWS, 100_000)

    expect(lines[0]?.sharePercent).toBe(80)
    expect(lines[1]?.sharePercent).toBe(20)
    expect(lines[0]?.children[0]?.name).toBe('Groceries')
  })
})

describe('sharePercent', () => {
  it('words a share as a whole percent', () => {
    expect(sharePercent(25_000, 1_00_000)).toBe(25)
  })

  it('rounds to the nearest whole percent', () => {
    expect(sharePercent(1, 3)).toBe(33)
    expect(sharePercent(2, 3)).toBe(67)
  })

  it('says nothing about a share of nothing', () => {
    expect(sharePercent(0, 0)).toBe(0)
    expect(sharePercent(5_000, 0)).toBe(0)
  })
})

describe('monthRange', () => {
  it('covers the whole month a day falls in', () => {
    expect(monthRange('2026-10-06')).toEqual({ from: '2026-10-01', to: '2026-10-31' })
  })

  it('covers a month of thirty days', () => {
    expect(monthRange('2026-09-30')).toEqual({ from: '2026-09-01', to: '2026-09-30' })
  })

  it('covers February, with and without a leap day', () => {
    expect(monthRange('2027-02-14')).toEqual({ from: '2027-02-01', to: '2027-02-28' })
    expect(monthRange('2028-02-14')).toEqual({ from: '2028-02-01', to: '2028-02-29' })
  })

  it('hands back nothing it cannot read, rather than a wrong month', () => {
    expect(monthRange('not-a-date')).toEqual({ from: '', to: '' })
  })
})
