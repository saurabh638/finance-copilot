import { describe, expect, it } from 'vitest'

import { formatPaise } from './money'

type Case = [paise: number, expected: string]

// Same cases as the backend helper (CODING_STANDARDS section 5).
const cases: Case[] = [
  [0, '₹0.00'],
  [1, '₹0.01'],
  [50, '₹0.50'],
  [100, '₹1.00'],
  [50_000, '₹500.00'],
  [12_345_678, '₹1,23,456.78'],
  [100_000_000, '₹10,00,000.00'],
  [1_000_000_000, '₹1,00,00,000.00'],
  [-50_000, '-₹500.00'],
  [-12_345_678, '-₹1,23,456.78'],
]

describe('formatPaise', () => {
  it.each(cases)('formats %i paise as %s', (paise: number, expected: string) => {
    expect(formatPaise(paise)).toBe(expected)
  })

  it('throws for a value that is not whole paise', () => {
    expect(() => formatPaise(500.5)).toThrow(TypeError)
  })
})
