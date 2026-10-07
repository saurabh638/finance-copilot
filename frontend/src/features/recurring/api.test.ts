import { describe, expect, it } from 'vitest'

import { dayQuery } from './api'

describe('dayQuery', () => {
  it('sends nothing when no day was asked about, which means today', () => {
    expect(dayQuery('')).toBe('')
  })

  it('sends the day it was given', () => {
    expect(dayQuery('2026-10-05')).toBe('?on=2026-10-05')
  })
})
