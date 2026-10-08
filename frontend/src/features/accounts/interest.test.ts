/**
 * The interest panel's rules, as pure functions.
 *
 * What a period reads like, what a rate reads like, and how the bank's figure is
 * described when it differs from the ledger's own: all of it is text and one
 * field, so it is settled here rather than in a screen that cannot be tested
 * without a browser.
 */

import { describe, expect, it } from 'vitest'

import type { InterestCredit } from './api'
import { bankFigureProblem, differenceWords, periodWords, rateWords } from './interest'

function credit(overrides: Partial<InterestCredit> = {}): InterestCredit {
  return {
    id: 1,
    account_id: 2,
    period_start: '2026-10-01',
    period_end: '2026-10-31',
    rate_percent: '7.1000',
    computed_paise: 58_139,
    credited_paise: null,
    transaction_id: null,
    confirmed_on: null,
    ...overrides,
  }
}

describe('periodWords', () => {
  it('says a month as its two ends', () => {
    expect(periodWords(credit())).toBe('1 Oct 2026 to 31 Oct 2026')
  })

  it('says a single day once', () => {
    expect(periodWords(credit({ period_start: '2026-10-31', period_end: '2026-10-31' }))).toBe(
      '31 Oct 2026',
    )
  })

  it('says a quarter as its two ends', () => {
    expect(periodWords(credit({ period_start: '2026-10-01', period_end: '2026-12-31' }))).toBe(
      '1 Oct 2026 to 31 Dec 2026',
    )
  })
})

describe('rateWords', () => {
  it('drops the stored zeros from a rate', () => {
    expect(rateWords('7.1000')).toBe('7.1% a year')
    expect(rateWords('8.0000')).toBe('8% a year')
    expect(rateWords('7.0000')).toBe('7% a year')
    expect(rateWords('0.5000')).toBe('0.5% a year')
    expect(rateWords('6.6500')).toBe('6.65% a year')
  })

  it('copes with a rate that has no point at all', () => {
    expect(rateWords('7')).toBe('7% a year')
  })
})

describe('differenceWords', () => {
  it('says nothing about a period that has not been credited', () => {
    expect(differenceWords(credit())).toBeNull()
  })

  it('says nothing when the bank paid exactly what the ledger worked out', () => {
    expect(differenceWords(credit({ credited_paise: 58_139 }))).toBeNull()
  })

  it('says how much more the bank paid', () => {
    expect(differenceWords(credit({ credited_paise: 58_150 }))).toBe(
      'The bank paid ₹0.11 more than the ledger worked out',
    )
  })

  it('says how much less the bank paid', () => {
    expect(differenceWords(credit({ credited_paise: 58_000 }))).toBe(
      'The bank paid ₹1.39 less than the ledger worked out',
    )
  })
})

describe('bankFigureProblem', () => {
  it('accepts an empty field, which means the ledger’s own figure', () => {
    expect(bankFigureProblem('')).toBeNull()
    expect(bankFigureProblem('   ')).toBeNull()
  })

  it('accepts a figure the way a bank statement writes one', () => {
    expect(bankFigureProblem('581.50')).toBeNull()
    expect(bankFigureProblem('₹581.50')).toBeNull()
    expect(bankFigureProblem('1,234.56')).toBeNull()
  })

  it('refuses something it cannot read', () => {
    expect(bankFigureProblem('about six hundred')).toBe(
      'Enter the figure like 581.50, or leave it empty to use the ledger’s',
    )
    expect(bankFigureProblem('581.505')).toBe(
      'Enter the figure like 581.50, or leave it empty to use the ledger’s',
    )
  })

  it('refuses nothing at all, because a credit of nothing is not a credit', () => {
    expect(bankFigureProblem('0')).toBe('The bank’s figure must be more than zero')
    expect(bankFigureProblem('-5')).toBe('The bank’s figure must be more than zero')
  })
})
