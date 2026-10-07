/**
 * The recurring form's rules, checked without a browser.
 *
 * What a rhythm reads like, what the form holds while it is being filled in, and
 * what the API is sent: all of it is text, dates and one payload, so it is
 * settled here where it can be tested properly.
 */

import { describe, expect, it } from 'vitest'

import type { DueItem, RecurringItem } from './api'
import {
  blankItem,
  draftFrom,
  dueWords,
  itemPayload,
  ordinal,
  rhythmWords,
  updatePayload,
  validateItem,
} from './recurring'

const TODAY = '2026-10-07'

function item(overrides: Partial<RecurringItem> = {}): RecurringItem {
  return {
    id: 1,
    name: 'Rent',
    kind: 'expense',
    amount_paise: 1_800_000,
    account_id: 2,
    category_id: 3,
    frequency: 'monthly',
    day_of_month: 5,
    weekday: null,
    starts_on: '2026-04-01',
    ends_on: null,
    is_active: true,
    ...overrides,
  }
}

describe('ordinal', () => {
  it('says the ordinary days', () => {
    expect(ordinal(1)).toBe('1st')
    expect(ordinal(2)).toBe('2nd')
    expect(ordinal(3)).toBe('3rd')
    expect(ordinal(4)).toBe('4th')
    expect(ordinal(21)).toBe('21st')
    expect(ordinal(22)).toBe('22nd')
    expect(ordinal(23)).toBe('23rd')
    expect(ordinal(31)).toBe('31st')
  })

  it('does not say 11st, 12nd or 13rd', () => {
    expect(ordinal(11)).toBe('11th')
    expect(ordinal(12)).toBe('12th')
    expect(ordinal(13)).toBe('13th')
  })
})

describe('rhythmWords', () => {
  it('says a monthly item by its day', () => {
    expect(rhythmWords(item({ day_of_month: 5 }))).toBe('Every month on the 5th')
    expect(rhythmWords(item({ day_of_month: 28 }))).toBe('Every month on the 28th')
  })

  it('says what happens in a month too short for the day', () => {
    expect(rhythmWords(item({ day_of_month: 31 }))).toBe(
      'Every month on the 31st, or the last day when the month is shorter',
    )
    expect(rhythmWords(item({ day_of_month: 29 }))).toBe(
      'Every month on the 29th, or the last day when the month is shorter',
    )
  })

  it('names a weekly item by its weekday', () => {
    expect(rhythmWords(item({ frequency: 'weekly', day_of_month: null, weekday: 0 }))).toBe(
      'Every Monday',
    )
    expect(rhythmWords(item({ frequency: 'weekly', day_of_month: null, weekday: 6 }))).toBe(
      'Every Sunday',
    )
  })
})

describe('dueWords', () => {
  it('names the day the item is owed for', () => {
    const due: DueItem = { item: item({ day_of_month: 1 }), due_on: '2026-10-01' }

    expect(dueWords(due)).toBe('Owed for 1 Oct 2026')
  })
})

describe('blankItem', () => {
  it('is a monthly spending item dated today, with nothing filled in', () => {
    expect(blankItem(TODAY)).toEqual({
      name: '',
      kind: 'expense',
      amount: '',
      account_id: '',
      category_id: '',
      frequency: 'monthly',
      day_of_month: '',
      weekday: '0',
      starts_on: TODAY,
      ends_on: '',
    })
  })
})

describe('validateItem', () => {
  it('is satisfied by a filled-in monthly item', () => {
    const draft = {
      ...blankItem(TODAY),
      name: 'Rent',
      amount: '18,000',
      account_id: '2',
      day_of_month: '5',
    }

    expect(validateItem(draft)).toEqual({})
  })

  it('is satisfied by a weekly item with a weekday and no day of the month', () => {
    const draft = {
      ...blankItem(TODAY),
      name: 'Household help',
      amount: '2000',
      account_id: '2',
      frequency: 'weekly' as const,
      day_of_month: '',
      weekday: '0',
    }

    expect(validateItem(draft)).toEqual({})
  })

  it('asks for a name', () => {
    const draft = { ...blankItem(TODAY), amount: '100', account_id: '2', day_of_month: '5' }

    expect(validateItem(draft).name).toBe('A name is required')
  })

  it('refuses a name longer than the server takes', () => {
    const draft = {
      ...blankItem(TODAY),
      name: 'x'.repeat(81),
      amount: '100',
      account_id: '2',
      day_of_month: '5',
    }

    expect(validateItem(draft).name).toBe('Keep the name under 80 characters')
  })

  it('refuses an amount it cannot read, and an amount that is not more than zero', () => {
    const unreadable = {
      ...blankItem(TODAY),
      name: 'Rent',
      amount: 'about a thousand',
      day_of_month: '5',
    }
    expect(validateItem(unreadable).amount).toBe('Enter an amount like 1,23,456.78')

    const zero = { ...blankItem(TODAY), name: 'Rent', amount: '0', day_of_month: '5' }
    expect(validateItem(zero).amount).toBe('The amount must be more than zero')
  })

  it('asks for an account and a start date', () => {
    const draft = {
      ...blankItem(TODAY),
      name: 'Rent',
      amount: '100',
      day_of_month: '5',
      starts_on: '',
    }

    expect(validateItem(draft).account_id).toBe('Pick an account')
    expect(validateItem(draft).starts_on).toBe('A start date is required')
  })

  it('asks a monthly item for a day of the month, and refuses one past the 31st', () => {
    const missing = { ...blankItem(TODAY), name: 'Rent', amount: '100', account_id: '2' }
    expect(validateItem(missing).day_of_month).toBe('A monthly item needs a day of the month')

    const tooBig = { ...missing, day_of_month: '32' }
    expect(validateItem(tooBig).day_of_month).toBe('A day of the month runs from 1 to 31')
  })

  it('asks a weekly item for a weekday', () => {
    const draft = {
      ...blankItem(TODAY),
      name: 'Household help',
      amount: '100',
      account_id: '2',
      frequency: 'weekly' as const,
      day_of_month: '',
      weekday: '',
    }

    expect(validateItem(draft).weekday).toBe('A weekly item needs a weekday')
  })

  it('refuses an end before the start', () => {
    const draft = {
      ...blankItem(TODAY),
      name: 'Rent',
      amount: '100',
      account_id: '2',
      day_of_month: '5',
      starts_on: '2026-10-07',
      ends_on: '2026-09-30',
    }

    expect(validateItem(draft).ends_on).toBe('The end cannot be before the start')
  })
})

describe('itemPayload', () => {
  it('sends a monthly item with a day and no weekday', () => {
    const draft = {
      ...blankItem(TODAY),
      name: '  Rent ',
      amount: '18,000',
      account_id: '2',
      category_id: '3',
      day_of_month: '5',
      starts_on: '2026-04-01',
    }

    expect(itemPayload(draft)).toEqual({
      name: 'Rent',
      kind: 'expense',
      amount_paise: 1_800_000,
      account_id: 2,
      category_id: 3,
      frequency: 'monthly',
      day_of_month: 5,
      starts_on: '2026-04-01',
    })
  })

  it('sends a weekly item with a weekday and no day of the month', () => {
    const draft = {
      ...blankItem(TODAY),
      name: 'Household help',
      kind: 'income' as const,
      amount: '2000',
      account_id: '4',
      frequency: 'weekly' as const,
      day_of_month: '',
      weekday: '6',
    }

    expect(itemPayload(draft)).toEqual({
      name: 'Household help',
      kind: 'income',
      amount_paise: 200_000,
      account_id: 4,
      frequency: 'weekly',
      weekday: 6,
      starts_on: TODAY,
    })
  })

  it('leaves out a filing that was not chosen, and an end that was not given', () => {
    const payload = itemPayload({
      ...blankItem(TODAY),
      name: 'Rent',
      amount: '100',
      account_id: '2',
      day_of_month: '5',
    })

    expect('category_id' in payload).toBe(false)
    expect('ends_on' in payload).toBe(false)
  })
})

describe('draftFrom', () => {
  it('fills the form from an item, ready to be sent back unchanged', () => {
    const stored = item({ name: 'Rent', amount_paise: 1_800_000, day_of_month: 5 })
    const draft = draftFrom(stored)

    expect(draft.name).toBe('Rent')
    // The same text the movement editor opens with, symbol and all: the parser
    // takes it back either way, and one convention is easier to keep.
    expect(draft.amount).toBe('₹18,000.00')
    expect(draft.account_id).toBe('2')
    expect(draft.category_id).toBe('3')
    expect(draft.day_of_month).toBe('5')
    expect(itemPayload(draft)).toEqual({
      name: 'Rent',
      kind: 'expense',
      amount_paise: 1_800_000,
      account_id: 2,
      category_id: 3,
      frequency: 'monthly',
      day_of_month: 5,
      starts_on: '2026-04-01',
    })
  })

  it('keeps a weekly item on its weekday', () => {
    const draft = draftFrom(item({ frequency: 'weekly', day_of_month: null, weekday: 2 }))

    expect(draft.weekday).toBe('2')
    expect(itemPayload(draft).weekday).toBe(2)
  })
})

describe('updatePayload', () => {
  it('sends nothing when nothing changed', () => {
    const stored = item()

    expect(updatePayload(draftFrom(stored), stored)).toEqual({})
  })

  it('sends the amount when only the amount changed', () => {
    const stored = item()
    const draft = { ...draftFrom(stored), amount: '20,000' }

    expect(updatePayload(draft, stored)).toEqual({ amount_paise: 2_000_000 })
  })

  it('sends the whole rhythm when the day changed', () => {
    const stored = item()
    const draft = { ...draftFrom(stored), day_of_month: '9' }

    expect(updatePayload(draft, stored)).toEqual({
      frequency: 'monthly',
      day_of_month: 9,
      weekday: null,
    })
  })

  it('sends the whole rhythm when the frequency changed', () => {
    const stored = item()
    const draft = { ...draftFrom(stored), frequency: 'weekly' as const, weekday: '3' }

    expect(updatePayload(draft, stored)).toEqual({
      frequency: 'weekly',
      day_of_month: null,
      weekday: 3,
    })
  })

  it('clears the filing by sending null', () => {
    const stored = item()
    const draft = { ...draftFrom(stored), category_id: '' }

    expect(updatePayload(draft, stored)).toEqual({ category_id: null })
  })

  it('sends the name when it was trimmed to something else', () => {
    const stored = item()
    const draft = { ...draftFrom(stored), name: '  House rent ' }

    expect(updatePayload(draft, stored)).toEqual({ name: 'House rent' })
  })
})
