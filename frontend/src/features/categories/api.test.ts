import { describe, expect, it } from 'vitest'

import { spendQuery } from './api'

describe('spendQuery', () => {
  it('is empty when the period is open at both ends', () => {
    expect(spendQuery('', '')).toBe('')
  })

  it('sends only the end that is set', () => {
    expect(spendQuery('2026-10-01', '')).toBe('?from=2026-10-01')
    expect(spendQuery('', '2026-10-31')).toBe('?to=2026-10-31')
  })

  it('sends both ends, the start first', () => {
    expect(spendQuery('2026-10-01', '2026-10-31')).toBe('?from=2026-10-01&to=2026-10-31')
  })
})
