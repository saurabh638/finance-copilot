import { describe, expect, it } from 'vitest'

import type { Suggestion, Transaction } from '../transactions/api'
import { catchUpDays, catchUpNote, filledBy, movementOn, streakWords } from './today'

/** A suggestion as the API returns one. */
function suggestion(overrides: Partial<Suggestion> = {}): Suggestion {
  return {
    merchant: 'Blinkit',
    times_used: 4,
    last_used: '2026-10-01',
    account_id: 2,
    category_id: 11,
    amount_paise: 45_000,
    ...overrides,
  }
}

/** A movement as the list returns one. */
function movement(id: number, transaction_date: string): Transaction {
  return {
    id,
    transaction_date,
    merchant: null,
    note: null,
    source: 'manual',
    postings: [{ id, account_id: 1, amount_paise: -50_000, kind: 'expense', category_id: null }],
  }
}

describe('filledBy', () => {
  it('fills in everything the name was recorded with', () => {
    expect(filledBy(suggestion())).toEqual({
      amount: '₹450.00',
      merchant: 'Blinkit',
      account_id: '2',
      category_id: '11',
    })
  })

  it('leaves the category empty when the name remembers none', () => {
    expect(filledBy(suggestion({ category_id: null }))).toMatchObject({ category_id: '' })
  })

  it('fills an amount the form can read back', () => {
    expect(filledBy(suggestion({ amount_paise: 123_45 })).amount).toBe('₹123.45')
  })
})

describe('streakWords', () => {
  it('offers a start rather than counting what is missing', () => {
    expect(streakWords(0, false)).toBe('Today is a good day to start')
  })

  it('says the day is recorded when it is', () => {
    expect(streakWords(1, true)).toBe('Today is recorded')
  })

  it('says yesterday was recorded when today is not yet', () => {
    expect(streakWords(1, false)).toBe('Yesterday was recorded')
  })

  it('counts a run that includes today', () => {
    expect(streakWords(4, true)).toBe('4 days in a row')
  })

  it('counts a run that ended yesterday without calling it broken', () => {
    expect(streakWords(4, false)).toBe('4 days in a row, up to yesterday')
  })

  it('never scolds, whatever the run is', () => {
    const said = [0, 1, 4].flatMap((days) => [streakWords(days, true), streakWords(days, false)])

    for (const words of said) {
      expect(words.toLowerCase()).not.toContain('missed')
      expect(words.toLowerCase()).not.toContain('lost')
      expect(words.toLowerCase()).not.toContain('broken')
    }
  })
})

describe('catchUpDays', () => {
  it('counts both ends', () => {
    expect(catchUpDays('2026-10-02', '2026-10-06')).toBe(5)
  })

  it('counts a single day as one', () => {
    expect(catchUpDays('2026-10-06', '2026-10-06')).toBe(1)
  })

  it('crosses a month end without losing a day', () => {
    expect(catchUpDays('2026-09-29', '2026-10-02')).toBe(4)
  })

  it('says nothing it cannot read, rather than a wrong number', () => {
    expect(catchUpDays('', '2026-10-06')).toBe(0)
    expect(catchUpDays('not-a-date', '2026-10-06')).toBe(0)
  })

  it('refuses a range that ends before it starts', () => {
    expect(catchUpDays('2026-10-06', '2026-10-02')).toBe(0)
  })
})

describe('catchUpNote', () => {
  it('says how many days the lump covers and up to when', () => {
    expect(catchUpNote('2026-10-02', '2026-10-06')).toBe('Catch-up for 5 days to 6 Oct 2026')
  })

  it('says the day when the lump is one day', () => {
    expect(catchUpNote('2026-10-06', '2026-10-06')).toBe('Catch-up for 6 Oct 2026')
  })

  it('says just what it is when the dates cannot be read', () => {
    expect(catchUpNote('', '')).toBe('Catch-up')
  })
})

describe('movementOn', () => {
  const movements = [
    movement(3, '2026-10-06'),
    movement(2, '2026-10-05'),
    movement(1, '2026-10-05'),
  ]

  it('finds the last thing that happened on a day', () => {
    expect(movementOn(movements, '2026-10-05')?.id).toBe(2)
  })

  it('has nothing to copy when that day is empty', () => {
    expect(movementOn(movements, '2026-10-04')).toBeNull()
  })
})
