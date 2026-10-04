import { describe, expect, it } from 'vitest'

import { InvalidMoneyError, formatPaise, parsePaise } from './money'

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

type ParseCase = [text: string, expected: number]

// Same cases as the backend helper (CODING_STANDARDS section 5).
const parseCases: ParseCase[] = [
  ['0', 0],
  ['1', 100],
  ['500', 50_000],
  ['500.5', 50_050],
  ['500.05', 50_005],
  ['1,23,456.78', 12_345_678],
  ['₹1,23,456.78', 12_345_678],
  [' 500 ', 50_000],
  ['1,00,000', 10_000_000],
  ['1,00,00,000', 1_000_000_000],
  ['1,234,567.89', 123_456_789],
  ['-500', -50_000],
  ['-₹500.00', -50_000],
  ['-0.01', -1],
]

describe('parsePaise', () => {
  it.each(parseCases)('parses %s as %i paise', (text: string, expected: number) => {
    expect(parsePaise(text)).toBe(expected)
  })

  it('returns whole paise and never a float', () => {
    const paise = parsePaise('1,23,456.78')

    expect(Number.isInteger(paise)).toBe(true)
  })

  it.each([
    ['500.505'],
    ['500.5050'],
    ['5,00,0'],
    ['1,23,4567'],
    ['1.2.3'],
    [''],
    ['   '],
    ['₹'],
    ['abc'],
    ['500m'],
    ['1,23,456.78 extra'],
    ['$500'],
    // 15 digits of rupees is past Number.MAX_SAFE_INTEGER once scaled to paise.
    ['99,99,99,99,99,99,999'],
  ])('rejects %s', (text: string) => {
    expect(() => parsePaise(text)).toThrow(InvalidMoneyError)
  })

  it('rejects a value given as a number, so a float can never enter', () => {
    // The form passes text; a number in the pipeline would mean a float did.
    expect(() => parsePaise(500.5 as unknown as string)).toThrow(TypeError)
  })
})
