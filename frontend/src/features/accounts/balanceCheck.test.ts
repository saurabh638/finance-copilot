import { describe, expect, it } from 'vitest'

import {
  NUDGE,
  differenceSentence,
  monthStart,
  validateStated,
  writeOffLabel,
} from './balanceCheck'

describe('monthStart', () => {
  it('turns any day into the first of its month', () => {
    expect(monthStart('2026-10-05')).toBe('2026-10-01')
    expect(monthStart('2026-10-01')).toBe('2026-10-01')
    expect(monthStart('2026-12-31')).toBe('2026-12-01')
  })
})

describe('validateStated', () => {
  it('asks for the balance when the field is empty', () => {
    expect(validateStated('')).toBe('Enter the balance your bank shows')
    expect(validateStated('   ')).toBe('Enter the balance your bank shows')
  })

  it('refuses text that is not money', () => {
    expect(validateStated('abc')).toBe('Enter an amount like 1,23,456.78')
    expect(validateStated('10.005')).toBe('Enter an amount like 1,23,456.78')
  })

  it('accepts zero, rupees in words, and an owed balance', () => {
    expect(validateStated('0')).toBeUndefined()
    expect(validateStated('1,23,456.78')).toBeUndefined()
    // A credit card holds a negative balance, and that is a real figure to check.
    expect(validateStated('-9,500')).toBeUndefined()
  })
})

describe('differenceSentence', () => {
  it('says so when the ledger and the bank agree', () => {
    expect(differenceSentence(0)).toBe('The ledger matches the bank exactly.')
  })

  it('reads money short as less than the ledger says', () => {
    expect(differenceSentence(-50_000)).toBe('₹500.00 less than the ledger says.')
  })

  it('reads money found as more than the ledger says', () => {
    expect(differenceSentence(50_000)).toBe('₹500.00 more than the ledger says.')
  })

  it('keeps every paise of a large difference', () => {
    expect(differenceSentence(-123_456_789)).toBe('₹12,34,567.89 less than the ledger says.')
  })
})

describe('writeOffLabel', () => {
  it('writes off what is missing', () => {
    expect(writeOffLabel(-50_000)).toBe('Write off ₹500.00')
  })

  it('records what was found', () => {
    expect(writeOffLabel(25_00_000)).toBe('Record ₹25,000.00')
  })

  it('offers nothing to post when there is no difference', () => {
    expect(writeOffLabel(0)).toBeNull()
  })
})

describe('NUDGE', () => {
  it('asks the questions SPEC.md asks, without accusing anyone', () => {
    expect(NUDGE).toContain('recurring charge')
    expect(NUDGE).toContain('not imported')
  })
})
