import { describe, expect, it } from 'vitest'

import { todayIso } from './dates'

describe('todayIso', () => {
  it('reads the local day, not the UTC one', () => {
    // Just after midnight in India is still the previous day in UTC: a date
    // built from toISOString() would silently file the day a day early.
    expect(todayIso(new Date(2026, 9, 4, 0, 30))).toBe('2026-10-04')
  })

  it('pads a single-digit month and day', () => {
    expect(todayIso(new Date(2026, 0, 5, 12, 0))).toBe('2026-01-05')
  })
})
