/**
 * The recurring form's rules, as pure functions.
 *
 * What a rhythm reads like in words, what the form holds while it is being
 * filled in, and what the API is sent: all of it is text, dates and one payload,
 * so it is settled here rather than in a screen that cannot be tested without a
 * browser.
 */

import { formatPaise, parsePaise } from '../../lib/money'
import { displayDate } from '../transactions/describe'
import type {
  DueItem,
  RecurringFrequency,
  RecurringItem,
  RecurringItemCreate,
  RecurringItemUpdate,
  RecurringKind,
} from './api'

export const NAME_MAX = 80

/** The two directions that can repeat. A transfer is not a bill. */
export const KIND_LABELS = {
  expense: 'Money spent',
  income: 'Money received',
} satisfies Record<RecurringKind, string>

export const KINDS = Object.keys(KIND_LABELS) as RecurringKind[]

export const FREQUENCY_LABELS = {
  monthly: 'Every month',
  weekly: 'Every week',
} satisfies Record<RecurringFrequency, string>

export const FREQUENCIES = Object.keys(FREQUENCY_LABELS) as RecurringFrequency[]

/** Monday first, the way the server counts them: Monday is 0 through Sunday 6. */
export const WEEKDAY_NAMES = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
]

/**
 * The order a day of the month is written in.
 *
 * Eleven, twelve and thirteen take "th" even though they end in a 1, 2 or 3, and
 * a month's rent said as "the 11st" is a small thing that reads as carelessness.
 */
export function ordinal(day: number): string {
  const tens = day % 100
  if (tens >= 11 && tens <= 13) {
    return `${String(day)}th`
  }
  switch (day % 10) {
    case 1:
      return `${String(day)}st`
    case 2:
      return `${String(day)}nd`
    case 3:
      return `${String(day)}rd`
    default:
      return `${String(day)}th`
  }
}

/** Days past this one do not exist in every month, so they say what happens then. */
const CLAMPED_FROM = 29

/** How often an item comes round, in words, including the short-month case. */
export function rhythmWords(item: RecurringItem): string {
  if (item.frequency === 'weekly') {
    const name = item.weekday === null ? 'week' : WEEKDAY_NAMES[item.weekday]
    return `Every ${name ?? 'week'}`
  }

  const day = item.day_of_month ?? 1
  const onThatDay = `Every month on the ${ordinal(day)}`
  return day >= CLAMPED_FROM ? `${onThatDay}, or the last day when the month is shorter` : onThatDay
}

/** What the check-in row says about the day it is for. */
export function dueWords(due: DueItem): string {
  return `Owed for ${displayDate(due.due_on)}`
}

/**
 * The form's values, all text.
 *
 * Inputs hold text and nothing is parsed until submit, which is the same rule the
 * movement form follows. `weekday` is a string because it comes from a list.
 */
export interface ItemDraft {
  name: string
  kind: RecurringKind
  amount: string
  account_id: string
  category_id: string
  frequency: RecurringFrequency
  day_of_month: string
  weekday: string
  starts_on: string
  ends_on: string
}

export type ItemProblems = Partial<Record<keyof ItemDraft, string>>

/** An empty form, starting today, with Monday chosen for a weekly item. */
export function blankItem(today: string): ItemDraft {
  return {
    name: '',
    kind: 'expense',
    amount: '',
    account_id: '',
    category_id: '',
    frequency: 'monthly',
    day_of_month: '',
    weekday: '0',
    starts_on: today,
    ends_on: '',
  }
}

/** The form filled in from an item, for changing it. */
export function draftFrom(item: RecurringItem): ItemDraft {
  return {
    name: item.name,
    // The server keeps a posting kind, but only the two that can repeat reach
    // here: the store refuses anything else when the item is planned.
    kind: item.kind === 'income' ? 'income' : 'expense',
    amount: formatPaise(item.amount_paise),
    account_id: String(item.account_id),
    category_id: item.category_id === null ? '' : String(item.category_id),
    frequency: item.frequency,
    day_of_month: item.day_of_month === null ? '' : String(item.day_of_month),
    weekday: item.weekday === null ? '0' : String(item.weekday),
    starts_on: item.starts_on,
    ends_on: item.ends_on ?? '',
  }
}

/** The day of the month as a number, or null when it is missing or nonsense. */
function dayNumber(text: string): number | null {
  if (text.trim() === '') {
    return null
  }
  const day = Number(text)
  return Number.isInteger(day) && day >= 1 && day <= 31 ? day : null
}

/** The weekday as a number, or null when nothing was chosen. */
function weekdayNumber(text: string): number | null {
  if (text.trim() === '') {
    return null
  }
  const weekday = Number(text)
  return Number.isInteger(weekday) && weekday >= 0 && weekday <= 6 ? weekday : null
}

/**
 * The server's rules, so a payload it would reject never leaves the form.
 *
 * The rhythm is the part worth stating twice: a monthly item has a day of the
 * month and no weekday, a weekly one the other way round, and a form that sent
 * both halves would be asking the server to guess.
 */
export function validateItem(draft: ItemDraft): ItemProblems {
  const problems: ItemProblems = {}

  if (draft.name.trim() === '') {
    problems.name = 'A name is required'
  } else if (draft.name.trim().length > NAME_MAX) {
    problems.name = `Keep the name under ${NAME_MAX} characters`
  }

  let paise: number | null = null
  try {
    paise = parsePaise(draft.amount)
  } catch {
    problems.amount = 'Enter an amount like 1,23,456.78'
  }
  if (paise !== null && paise <= 0) {
    problems.amount = 'The amount must be more than zero'
  }

  if (draft.account_id === '') {
    problems.account_id = 'Pick an account'
  }

  if (draft.starts_on === '') {
    problems.starts_on = 'A start date is required'
  }

  if (draft.frequency === 'monthly') {
    if (dayNumber(draft.day_of_month) === null) {
      problems.day_of_month =
        draft.day_of_month.trim() === ''
          ? 'A monthly item needs a day of the month'
          : 'A day of the month runs from 1 to 31'
    }
  } else if (weekdayNumber(draft.weekday) === null) {
    problems.weekday = 'A weekly item needs a weekday'
  }

  if (draft.ends_on !== '' && draft.starts_on !== '' && draft.ends_on < draft.starts_on) {
    problems.ends_on = 'The end cannot be before the start'
  }

  return problems
}

/** Text that is empty once trimmed becomes null: a blank name is no name. */
function orNull(text: string): string | null {
  const trimmed = text.trim()
  return trimmed === '' ? null : trimmed
}

/**
 * The payload for a new item.
 *
 * Only the half of the rhythm the frequency asks for is sent, so the server is
 * never given both a day and a weekday to choose between. A filing nobody chose
 * and an end nobody gave are left out rather than sent as nulls.
 */
export function itemPayload(draft: ItemDraft): RecurringItemCreate {
  const amount_paise = parsePaise(draft.amount)
  const payload: RecurringItemCreate = {
    name: (orNull(draft.name) ?? '').trim(),
    kind: draft.kind,
    amount_paise,
    account_id: Number(draft.account_id),
    frequency: draft.frequency,
    starts_on: draft.starts_on,
  }

  if (draft.frequency === 'monthly') {
    payload.day_of_month = dayNumber(draft.day_of_month)
  } else {
    payload.weekday = weekdayNumber(draft.weekday)
  }

  if (draft.category_id !== '') {
    payload.category_id = Number(draft.category_id)
  }
  if (draft.ends_on !== '') {
    payload.ends_on = draft.ends_on
  }

  return payload
}

/** Whether the draft's rhythm is the one the item already has. */
function sameRhythm(draft: ItemDraft, item: RecurringItem): boolean {
  if (draft.frequency !== item.frequency) {
    return false
  }
  return draft.frequency === 'monthly'
    ? dayNumber(draft.day_of_month) === item.day_of_month
    : weekdayNumber(draft.weekday) === item.weekday
}

/**
 * The payload for a change: only what is different from the item.
 *
 * An omitted field is left alone by the API, so sending everything back would
 * overwrite a change made elsewhere with whatever the form was opened with. The
 * rhythm goes as a whole because its two halves have to move together, and a
 * cleared filing is sent as an explicit null, which is the only way to say it.
 */
export function updatePayload(draft: ItemDraft, item: RecurringItem): RecurringItemUpdate {
  const payload: RecurringItemUpdate = {}
  const name = (orNull(draft.name) ?? '').trim()

  if (name !== item.name) {
    payload.name = name
  }
  if (parsePaise(draft.amount) !== item.amount_paise) {
    payload.amount_paise = parsePaise(draft.amount)
  }
  if (Number(draft.account_id) !== item.account_id) {
    payload.account_id = Number(draft.account_id)
  }
  if (draft.category_id !== (item.category_id === null ? '' : String(item.category_id))) {
    payload.category_id = draft.category_id === '' ? null : Number(draft.category_id)
  }
  if (!sameRhythm(draft, item)) {
    payload.frequency = draft.frequency
    payload.day_of_month = draft.frequency === 'monthly' ? dayNumber(draft.day_of_month) : null
    payload.weekday = draft.frequency === 'weekly' ? weekdayNumber(draft.weekday) : null
  }
  if (draft.starts_on !== item.starts_on) {
    payload.starts_on = draft.starts_on
  }
  if (draft.ends_on !== '' && draft.ends_on !== item.ends_on) {
    payload.ends_on = draft.ends_on
  }

  return payload
}
