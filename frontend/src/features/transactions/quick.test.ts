/**
 * The quick line's grammar, line by line.
 *
 * Read as `line` -> what it must produce. Every line in the approved table is
 * here, plus the things a table cannot say: the paise each money format comes to,
 * and that a line never fills the form with something the form would refuse.
 */

import { describe, expect, it } from 'vitest'

import { parsePaise } from '../../lib/money'
import type { Account } from '../accounts/api'
import type { Category, CategoryKind } from '../categories/api'
import type { Suggestion } from '../transactions/api'
import { blankMovement, validateMovement } from '../transactions/form'
import {
  applyChoice,
  quickSummary,
  readQuickLine,
  withAnswers,
  type QuickChoice,
  type QuickWorld,
} from './quick'

const TODAY = '2026-10-08'
const YESTERDAY = '2026-10-07'

function account(id: number, name: string, alias: string | null = null): Account {
  return {
    id,
    name,
    alias,
    type: 'savings',
    purpose: null,
    capture_mode: 'statement_import',
    parent_id: null,
    opening_balance_paise: 0,
    opening_date: '2026-04-01',
    statement_day: null,
    due_day: null,
    is_active: true,
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  }
}

function category(
  id: number,
  name: string,
  kind: CategoryKind,
  parent_id: number | null = null,
): Category {
  return { id, name, kind, parent_id }
}

function merchant(name: string): Suggestion {
  return {
    merchant: name,
    times_used: 3,
    last_used: '2026-10-05',
    account_id: 1,
    category_id: null,
    amount_paise: 45000,
  }
}

const SBI = account(1, 'SBI')
const CARD = account(2, 'SBI Credit Card', 'hdfc')
const SLICE = account(3, 'slice')
const WALKTHROUGH = account(4, 'Walkthrough')

const ACCOUNTS = [SBI, CARD, SLICE, WALKTHROUGH]

const FOOD = category(10, 'Food & groceries', 'expense')
const EATING_OUT = category(11, 'Eating out', 'expense', 10)
const GROCERIES = category(12, 'Groceries', 'expense', 10)
const HOME = category(20, 'Home', 'expense')
const RENT = category(21, 'Rent', 'expense', 20)
const ELECTRICITY = category(22, 'Electricity', 'expense', 20)
const SALARY = category(30, 'Salary', 'income')

const CATEGORIES = [FOOD, EATING_OUT, GROCERIES, HOME, RENT, ELECTRICITY, SALARY]

const HISTORY = [merchant('Swiggy'), merchant('Big Bazaar'), merchant('More')]

function world(overrides: Partial<QuickWorld> = {}): QuickWorld {
  return {
    accounts: ACCOUNTS,
    categories: CATEGORIES,
    merchants: HISTORY,
    today: TODAY,
    ...overrides,
  }
}

/** The reading of a line in the everyday world. */
function read(line: string, overrides: Partial<QuickWorld> = {}) {
  return readQuickLine(line, world(overrides))
}

function labels(choices: QuickChoice[]): string[] {
  return choices.map((choice) => choice.label)
}

describe('the clear lines', () => {
  it('reads an amount and a known merchant', () => {
    const reading = read('450 swiggy')

    expect(reading.values.amount).toBe('450')
    expect(reading.values.merchant).toBe('Swiggy')
    expect(reading.values.transaction_date).toBe(TODAY)
    expect(reading.values.kind).toBe('expense')
    expect(reading.values.account_id).toBe('')
    expect(reading.questions).toEqual([])
  })

  it('reads a merchant out of history and keeps the rest as the note', () => {
    const reading = read('450 dinner swiggy hdfc')

    expect(reading.values.amount).toBe('450')
    expect(reading.values.merchant).toBe('Swiggy')
    expect(reading.values.note).toBe('dinner')
    expect(reading.values.account_id).toBe(String(CARD.id))
  })

  it('reads a two-word known merchant and a symbol amount', () => {
    const reading = read('₹1,250.50 big bazaar sbi')

    expect(reading.values.amount).toBe('₹1,250.50')
    expect(parsePaise(reading.values.amount)).toBe(125050)
    expect(reading.values.merchant).toBe('Big Bazaar')
    expect(reading.values.account_id).toBe(String(SBI.id))
  })

  it('reads the /- shorthand and a merchant the history does not know', () => {
    const reading = read('450/- auto')

    expect(reading.values.amount).toBe('450')
    expect(parsePaise(reading.values.amount)).toBe(45000)
    expect(reading.values.merchant).toBe('auto')
  })

  it('reads Indian grouping into exact paise', () => {
    const reading = read('1,23,456.78 swiggy')

    expect(parsePaise(reading.values.amount)).toBe(12345678)
  })

  it('reads one decimal place as fifty paise', () => {
    const reading = read('450.5 swiggy')

    expect(parsePaise(reading.values.amount)).toBe(45050)
  })

  it('ignores case when it matches', () => {
    const reading = read('450 SWIGGY SBI')

    expect(reading.values.merchant).toBe('Swiggy')
    expect(reading.values.account_id).toBe(String(SBI.id))
    expect(reading.values.note).toBe('')
  })

  it('reads an amount on its own', () => {
    const reading = read('450')

    expect(reading.values.amount).toBe('450')
    expect(reading.values.merchant).toBe('')
    expect(reading.values.account_id).toBe('')
    expect(reading.questions).toEqual([])
  })

  it('reads nothing out of an empty line', () => {
    const reading = read('')

    expect(reading.values).toEqual(blankMovement(TODAY))
    expect(reading.questions).toEqual([])
    expect(reading.notices).toEqual([])
    expect(reading.problem).toBeNull()
  })
})

describe('the paise every money format comes to', () => {
  const cases: [line: string, paise: number][] = [
    ['450 swiggy', 45000],
    ['₹450 swiggy', 45000],
    ['1,23,456.78 swiggy', 12345678],
    ['450.5 swiggy', 45050],
    ['450/- swiggy', 45000],
    ['50,000 received sbi', 5000000],
  ]

  it.each(cases)('%s is %i paise', (line, paise) => {
    expect(parsePaise(read(line).values.amount)).toBe(paise)
  })
})

describe('the date', () => {
  it('reads yesterday', () => {
    expect(read('450 swiggy yesterday').values.transaction_date).toBe(YESTERDAY)
  })

  it('reads today', () => {
    expect(read('450 swiggy today').values.transaction_date).toBe(TODAY)
  })

  it('reads an ISO date', () => {
    expect(read('450 swiggy 2026-10-05').values.transaction_date).toBe('2026-10-05')
  })

  it('refuses 05/10 rather than guessing the order, and says so', () => {
    const reading = read('450 swiggy 05/10')

    expect(reading.values.transaction_date).toBe(TODAY)
    expect(reading.notices.join(' ')).toContain('05/10')
    // The word stays in the text rather than disappearing.
    expect(reading.values.note).toBe('05/10')
    expect(reading.values.merchant).toBe('Swiggy')
  })
})

describe('the direction', () => {
  it('reads spent as spending', () => {
    const reading = read('450 spent sbi')

    expect(reading.values.kind).toBe('expense')
    expect(reading.values.account_id).toBe(String(SBI.id))
  })

  it('reads received as earning', () => {
    const reading = read('50,000 received sbi')

    expect(reading.values.kind).toBe('income')
    expect(reading.values.account_id).toBe(String(SBI.id))
  })

  it('takes the direction from a category whose kind implies one', () => {
    const reading = read('salary 50,000 sbi')

    expect(reading.values.kind).toBe('income')
    expect(reading.values.category_id).toBe(String(SALARY.id))
    expect(reading.values.amount).toBe('50,000')
  })

  it('does not file a spending line under an earning name, and says why', () => {
    const reading = read('450 swiggy salary')

    expect(reading.values.kind).toBe('expense')
    expect(reading.values.category_id).toBe('')
    expect(reading.notices.join(' ')).toContain('Salary')
    expect(reading.values.merchant).toBe('Swiggy')
    expect(reading.values.note).toBe('salary')
  })
})

describe('names matched as runs of words', () => {
  it('files under a two-word child', () => {
    const reading = read('450 eating out swiggy')

    expect(reading.values.category_id).toBe(String(EATING_OUT.id))
    expect(reading.values.merchant).toBe('Swiggy')
  })

  it('reads a branch and its child as the screen writes them', () => {
    const reading = read('450 home rent sbi')

    expect(reading.values.category_id).toBe(String(RENT.id))
    expect(reading.values.account_id).toBe(String(SBI.id))
    expect(reading.values.merchant).toBe('')
  })

  it('files under a one-word child', () => {
    const reading = read('450 electricity sbi')

    expect(reading.values.category_id).toBe(String(ELECTRICITY.id))
    expect(reading.values.merchant).toBe('')
  })

  it('files under a branch itself', () => {
    const reading = read('450 food & groceries sbi')

    expect(reading.values.category_id).toBe(String(FOOD.id))
    expect(reading.values.merchant).toBe('')
  })
})

describe('what it must ask rather than guess', () => {
  it('asks which account when two match, and fills neither', () => {
    const reading = read('450 swiggy sbi hdfc')

    expect(reading.values.account_id).toBe('')
    expect(reading.questions).toHaveLength(1)
    expect(labels(reading.questions[0]?.choices ?? [])).toEqual([SBI.name, CARD.name])
  })

  it('asks whether a word that is both a category and a merchant is the filing', () => {
    const reading = read('450 rent sbi', { merchants: [...HISTORY, merchant('Rent')] })

    expect(reading.values.category_id).toBe('')
    expect(reading.values.merchant).toBe('')
    expect(reading.questions).toHaveLength(1)
    expect(labels(reading.questions[0]?.choices ?? [])).toEqual([
      'File it under Home · Rent',
      'Use rent as the merchant',
    ])
  })

  it('asks which merchant when two known ones appear', () => {
    const reading = read('450 more big bazaar')

    expect(reading.values.merchant).toBe('')
    expect(reading.questions).toHaveLength(1)
    expect(labels(reading.questions[0]?.choices ?? [])).toEqual(['More', 'Big Bazaar'])
  })

  it('asks when a longer known merchant contains a shorter one', () => {
    const reading = read('450 dinner swiggy', {
      merchants: [merchant('Swiggy'), merchant('dinner swiggy')],
    })

    expect(reading.values.merchant).toBe('')
    expect(reading.questions).toHaveLength(1)
    expect(labels(reading.questions[0]?.choices ?? [])).toEqual(['dinner swiggy', 'Swiggy'])
  })

  it('asks which one when two categories share a name', () => {
    const reading = read('450 groceries sbi', {
      categories: [...CATEGORIES, category(40, 'Groceries', 'expense', 20)],
    })

    expect(reading.values.category_id).toBe('')
    expect(labels(reading.questions[0]?.choices ?? [])).toEqual([
      'File it under Food & groceries · Groceries',
      'File it under Home · Groceries',
    ])
  })

  it('does not ask about the merchant when there is no merchant to choose', () => {
    const reading = read('450 home rent sbi', { merchants: [...HISTORY, merchant('Rent')] })

    expect(reading.questions).toEqual([])
    expect(reading.values.category_id).toBe(String(RENT.id))
  })
})

describe('words nothing matched', () => {
  it('keeps a name the history has never seen, as typed', () => {
    const reading = read('450 blinka sbi')

    expect(reading.values.merchant).toBe('blinka')
    expect(reading.values.account_id).toBe(String(SBI.id))
    expect(reading.values.note).toBe('')
  })

  it('takes the first amount and says the later one was not money', () => {
    const reading = read('450 500 swiggy')

    expect(reading.values.amount).toBe('450')
    expect(reading.notices.join(' ')).toContain('500')
    expect(reading.values.merchant).toBe('Swiggy')
  })

  it('treats zero as nothing at all', () => {
    const reading = read('0 swiggy')

    expect(reading.values.amount).toBe('')
    expect(reading.values.merchant).toBe('Swiggy')
    expect(reading.notices.join(' ')).toContain('0')
  })
})

describe('transfers', () => {
  it('reads a transfer with the word in it', () => {
    const reading = read('500 transfer sbi to slice')

    expect(reading.values.kind).toBe('transfer')
    expect(reading.values.from_account_id).toBe(String(SBI.id))
    expect(reading.values.to_account_id).toBe(String(SLICE.id))
    expect(reading.values.note).toBe('')
    expect(reading.values.merchant).toBe('')
    expect(reading.questions).toEqual([])
  })

  it('reads a transfer without the word transfer', () => {
    const reading = read('500 sbi to slice')

    expect(reading.values.kind).toBe('transfer')
    expect(reading.values.from_account_id).toBe(String(SBI.id))
    expect(reading.values.to_account_id).toBe(String(SLICE.id))
  })

  it('keeps the leftover words as the transfer note', () => {
    const reading = read('250 moved slice to sbi dinner')

    expect(reading.values.kind).toBe('transfer')
    expect(reading.values.from_account_id).toBe(String(SLICE.id))
    expect(reading.values.to_account_id).toBe(String(SBI.id))
    expect(reading.values.note).toBe('dinner')
  })

  it('asks where the money went when only the source is named', () => {
    const reading = read('500 transfer from sbi')

    expect(reading.values.from_account_id).toBe(String(SBI.id))
    expect(reading.values.to_account_id).toBe('')
    expect(reading.questions).toHaveLength(1)
    expect(reading.questions[0]?.field).toBe('to_account_id')
    expect(labels(reading.questions[0]?.choices ?? [])).not.toContain(SBI.name)
    expect(labels(reading.questions[0]?.choices ?? [])).toContain(SLICE.name)
  })

  it('asks where the money came from when only the destination is named', () => {
    const reading = read('500 transfer to slice')

    expect(reading.values.to_account_id).toBe(String(SLICE.id))
    expect(reading.values.from_account_id).toBe('')
    expect(reading.questions).toHaveLength(1)
    expect(reading.questions[0]?.field).toBe('from_account_id')
    expect(labels(reading.questions[0]?.choices ?? [])).not.toContain(SLICE.name)
  })

  it('refuses a transfer between one account and itself', () => {
    const reading = read('500 transfer sbi sbi')

    expect(reading.problem).toBe('A transfer needs two different accounts')
    expect(reading.values.kind).toBe('transfer')
  })

  it('will not file a transfer under a category, and says so', () => {
    const reading = read('500 transfer sbi to slice groceries')

    expect(reading.values.category_id).toBe('')
    expect(reading.notices.join(' ')).toContain('category')
    expect(reading.values.note).toBe('groceries')
  })

  it('asks for both accounts when neither is named', () => {
    const reading = read('500 transfer')

    expect(reading.values.kind).toBe('transfer')
    expect(reading.questions.map((question) => question.field)).toEqual([
      'from_account_id',
      'to_account_id',
    ])
  })
})

describe('answering a question', () => {
  it('fills the account when the account question is answered', () => {
    const reading = read('450 swiggy sbi hdfc')
    const chosen = reading.questions[0]?.choices[1]

    const values = applyChoice(reading.values, chosen as QuickChoice)

    expect(values.account_id).toBe(String(CARD.id))
  })

  it('files under the category when the filing is chosen', () => {
    const reading = read('450 rent sbi', { merchants: [...HISTORY, merchant('Rent')] })
    const chosen = reading.questions[0]?.choices[0]

    const values = applyChoice(reading.values, chosen as QuickChoice)

    expect(values.category_id).toBe(String(RENT.id))
    expect(values.merchant).toBe('')
  })

  it('uses the word as the merchant when that is chosen', () => {
    const reading = read('450 rent sbi', { merchants: [...HISTORY, merchant('Rent')] })
    const chosen = reading.questions[0]?.choices[1]

    const values = applyChoice(reading.values, chosen as QuickChoice)

    expect(values.category_id).toBe('')
    expect(values.merchant).toBe('rent')
  })

  it('takes the longer known merchant, note and all, when that is chosen', () => {
    const reading = read('450 dinner swiggy', {
      merchants: [merchant('Swiggy'), merchant('dinner swiggy')],
    })
    const chosen = reading.questions[0]?.choices[0]

    const values = applyChoice(reading.values, chosen as QuickChoice)

    expect(values.merchant).toBe('dinner swiggy')
    expect(values.note).toBe('')
  })
})

describe('what a line never does', () => {
  const lines = [
    '450 swiggy',
    '450 dinner swiggy hdfc',
    '₹1,250.50 big bazaar sbi',
    '450/- auto',
    '450.5 swiggy',
    '450 swiggy 05/10',
    'salary 50,000 sbi',
    '450 swiggy salary',
    '450 blinka sbi',
    '450 500 swiggy',
    '0 swiggy',
    '500 transfer sbi to slice',
    '250 moved slice to sbi dinner',
  ]

  it.each(lines)('%s fills only values the form accepts', (line) => {
    const reading = read(line)
    const problems = validateMovement(reading.values)

    // A line with no amount leaves the box empty for the form to ask about;
    // an amount the line did read must be one the form accepts.
    if (reading.values.amount !== '') {
      expect(problems.amount).toBeUndefined()
    }
    expect(problems.transaction_date).toBeUndefined()
    expect(problems.merchant).toBeUndefined()
    expect(problems.note).toBeUndefined()
  })

  it('leaves the amount for the form to ask about when the line has none', () => {
    const reading = read('0 swiggy')

    expect(reading.values.amount).toBe('')
    expect(validateMovement(reading.values).amount).toBe('Enter an amount like 1,23,456.78')
  })

  it('cuts a merchant the form would refuse, and says so', () => {
    const reading = read(`450 ${'x'.repeat(200)}`)

    expect(reading.values.merchant).toHaveLength(120)
    expect(validateMovement(reading.values).merchant).toBeUndefined()
    expect(reading.notices.join(' ')).toContain('shortened')
  })

  it('leaves the split parts alone', () => {
    const reading = read('450 swiggy sbi')

    expect(reading.values.split).toBe(false)
    expect(reading.values.parts).toEqual(blankMovement(TODAY).parts)
  })
})

describe('the summary of what was understood', () => {
  it('names every part the line decided', () => {
    const reading = read('450 dinner swiggy hdfc')

    expect(quickSummary(reading, world())).toEqual([
      '₹450.00',
      'Money spent',
      'Out of SBI Credit Card',
      'Merchant Swiggy',
      'Note dinner',
    ])
  })

  it('names a filing and a date that is not today', () => {
    const reading = read('450 home rent sbi yesterday')

    expect(quickSummary(reading, world())).toEqual([
      '₹450.00',
      'Money spent',
      'Out of SBI',
      'Filed under Home · Rent',
      'Dated 2026-10-07',
    ])
  })

  it('names both ends of a transfer', () => {
    const reading = read('500 transfer sbi to slice')

    expect(quickSummary(reading, world())).toEqual([
      '₹500.00',
      'Transfer between accounts',
      'From SBI to slice',
    ])
  })

  it('says nothing about a line that is empty', () => {
    const reading = read('')

    expect(quickSummary(reading, world())).toEqual(['Money spent'])
  })
})

describe('keeping an answer', () => {
  it('applies the answer and stops asking', () => {
    const reading = read('450 swiggy sbi hdfc')
    const answer = reading.questions[0]?.choices[1]

    const kept = withAnswers(reading, { account_id: answer as QuickChoice })

    expect(kept.questions).toEqual([])
    expect(kept.values.account_id).toBe(String(CARD.id))
  })

  it('leaves a question open until it is answered', () => {
    const reading = read('500 transfer')

    expect(withAnswers(reading, {}).questions).toHaveLength(2)
  })
})
