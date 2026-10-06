import { describe, expect, it } from 'vitest'

import {
  addPart,
  allocatedPaise,
  blankParts,
  partPaise,
  partsPayload,
  remainingPaise,
  removePart,
  validateParts,
} from './parts'

const GROCERIES = '11'
const HOUSEHOLD = '12'

/** The ₹500 shop that became the example everywhere else. */
const FILLED = [
  { amount: '300', category_id: GROCERIES },
  { amount: '200', category_id: HOUSEHOLD },
]

describe('blankParts', () => {
  it('starts a split with two parts, because one part is simply the whole', () => {
    expect(blankParts()).toEqual([
      { amount: '', category_id: '' },
      { amount: '', category_id: '' },
    ])
  })
})

describe('addPart and removePart', () => {
  it('adds an empty part at the end', () => {
    expect(addPart(FILLED)).toEqual([...FILLED, { amount: '', category_id: '' }])
  })

  it('removes the part at the position given', () => {
    expect(removePart([...FILLED, { amount: '100', category_id: GROCERIES }], 1)).toEqual([
      FILLED[0],
      { amount: '100', category_id: GROCERIES },
    ])
  })

  it('keeps two parts, because fewer is not a split', () => {
    expect(removePart(FILLED, 0)).toEqual(FILLED)
  })
})

describe('partPaise', () => {
  it('reads an amount as whole paise', () => {
    expect(partPaise({ amount: '1,234.56', category_id: GROCERIES })).toBe(123456)
  })

  it('has nothing to read from an amount that is not money yet', () => {
    expect(partPaise({ amount: '', category_id: GROCERIES })).toBeNull()
    expect(partPaise({ amount: 'abc', category_id: GROCERIES })).toBeNull()
    expect(partPaise({ amount: '-5', category_id: GROCERIES })).toBeNull()
    expect(partPaise({ amount: '0', category_id: GROCERIES })).toBeNull()
  })

  it('refuses more decimal places than paise rather than rounding them', () => {
    expect(partPaise({ amount: '300.005', category_id: GROCERIES })).toBeNull()
  })
})

describe('allocatedPaise and remainingPaise', () => {
  it('adds up what has been given a category so far', () => {
    expect(allocatedPaise(FILLED)).toBe(50000)
  })

  it('counts a part that is not money yet as nothing', () => {
    expect(allocatedPaise([FILLED[0], { amount: '', category_id: HOUSEHOLD }])).toBe(30000)
  })

  it('says how much is still to be allocated', () => {
    expect(remainingPaise('500', [FILLED[0]])).toBe(20000)
  })

  it('goes negative when the parts ask for more than the amount', () => {
    expect(remainingPaise('500', [...FILLED, { amount: '100', category_id: GROCERIES }])).toBe(
      -10000,
    )
  })

  it('has nothing to say until the amount is money', () => {
    expect(remainingPaise('', FILLED)).toBeNull()
    expect(remainingPaise('abc', FILLED)).toBeNull()
  })
})

describe('validateParts', () => {
  it('accepts parts that add up to the amount exactly', () => {
    expect(validateParts('500', FILLED)).toBeNull()
  })

  it('accepts parts that add up once the amount is written with grouping', () => {
    expect(
      validateParts('1,234.56', [
        { amount: '1,000', category_id: GROCERIES },
        { amount: '234.56', category_id: HOUSEHOLD },
      ]),
    ).toBeNull()
  })

  it('says by how much the parts miss the amount', () => {
    expect(
      validateParts('500', [
        { amount: '300', category_id: GROCERIES },
        { amount: '100', category_id: HOUSEHOLD },
      ]),
    ).toBe('The parts must add up to ₹500.00; ₹100.00 is still to allocate')
  })

  it('says when the parts ask for more than the amount', () => {
    expect(
      validateParts('500', [
        { amount: '300', category_id: GROCERIES },
        { amount: '300', category_id: HOUSEHOLD },
      ]),
    ).toBe('The parts must add up to ₹500.00; ₹100.00 too much')
  })

  it('refuses a part that has no amount', () => {
    expect(
      validateParts('500', [
        { amount: '300', category_id: GROCERIES },
        { amount: '', category_id: HOUSEHOLD },
      ]),
    ).toBe('Every part needs an amount')
  })

  it('refuses a part that has no category', () => {
    expect(
      validateParts('500', [
        { amount: '300', category_id: GROCERIES },
        { amount: '200', category_id: '' },
      ]),
    ).toBe('Every part needs a category')
  })

  it('asks for two parts at least, since one part is the whole', () => {
    expect(validateParts('500', [{ amount: '500', category_id: GROCERIES }])).toBe(
      'A split needs at least two parts',
    )
  })

  it('says nothing about the parts until the amount itself is money', () => {
    expect(validateParts('', FILLED)).toBeNull()
    expect(validateParts('abc', FILLED)).toBeNull()
  })
})

describe('partsPayload', () => {
  it('sends each part as paise and a category, in the order given', () => {
    expect(partsPayload(FILLED)).toEqual([
      { amount_paise: 30000, category_id: 11 },
      { amount_paise: 20000, category_id: 12 },
    ])
  })

  it('fails loudly rather than sending a part that was never validated', () => {
    expect(() => partsPayload([{ amount: 'abc', category_id: GROCERIES }])).toThrow()
  })
})
