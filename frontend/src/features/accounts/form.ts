/** The account form's values, its rules, and the payload they produce. */

import { parsePaise } from '../../lib/money'
import type { AccountType, CaptureMode, RateFrequency } from './api'
import type { NewAccount } from './useAccounts'

/**
 * Labels for every member the server accepts.
 *
 * `satisfies Record<..., string>` makes a missing member a compile error, so the
 * options cannot quietly drift behind the generated OpenAPI schema.
 */
export const ACCOUNT_TYPE_LABELS = {
  savings: 'Savings',
  current: 'Current',
  credit_card: 'Credit card',
  wallet: 'Wallet',
  cash: 'Cash',
  fd: 'Fixed deposit',
  rd: 'Recurring deposit',
  loan: 'Loan',
  pot: 'Pot (a sub-balance of another account)',
} satisfies Record<AccountType, string>

export const CAPTURE_MODE_LABELS = {
  statement_import: 'Statement import',
  manual_only: 'Manual only',
  hybrid: 'Both',
} satisfies Record<CaptureMode, string>

export const RATE_FREQUENCY_LABELS = {
  daily: 'Daily',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  yearly: 'Yearly',
} satisfies Record<RateFrequency, string>

export const ACCOUNT_TYPES = Object.keys(ACCOUNT_TYPE_LABELS) as AccountType[]
export const CAPTURE_MODES = Object.keys(CAPTURE_MODE_LABELS) as CaptureMode[]
export const RATE_FREQUENCIES = Object.keys(RATE_FREQUENCY_LABELS) as RateFrequency[]

/** Every value is text: inputs hold text, and nothing is parsed until submit. */
export interface AccountFormValues {
  name: string
  type: AccountType
  capture_mode: CaptureMode
  purpose: string
  parent_id: string
  opening_balance: string
  opening_date: string
  statement_day: string
  due_day: string
  rate: string
  frequency: RateFrequency
}

export const EMPTY_ACCOUNT_FORM: AccountFormValues = {
  name: '',
  type: 'savings',
  capture_mode: 'statement_import',
  purpose: '',
  parent_id: '',
  opening_balance: '',
  opening_date: '',
  statement_day: '',
  due_day: '',
  rate: '',
  frequency: 'quarterly',
}

export type AccountFormErrors = Partial<Record<keyof AccountFormValues, string>>

// Up to three digits before the point and four after: NUMERIC(7, 4) on the server.
const RATE_PATTERN = /^\d{1,3}(\.\d{1,4})?$/

/** The server's rules, so a payload it would reject never leaves the form. */
export function validateAccountForm(values: AccountFormValues): AccountFormErrors {
  const errors: AccountFormErrors = {}

  if (values.name.trim() === '') {
    errors.name = 'A name is required'
  } else if (values.name.trim().length > 100) {
    errors.name = 'Keep the name under 100 characters'
  }

  if (values.purpose.trim().length > 100) {
    errors.purpose = 'Keep the purpose under 100 characters'
  }

  try {
    parsePaise(values.opening_balance)
  } catch {
    errors.opening_balance = 'Enter an amount like 1,23,456.78'
  }

  if (values.opening_date === '') {
    errors.opening_date = 'An opening date is required'
  }

  if (values.type === 'pot' && values.parent_id === '') {
    errors.parent_id = 'A pot needs a parent account'
  }

  if (values.type === 'credit_card') {
    if (!isDayOfMonth(values.statement_day)) {
      errors.statement_day = 'Use a day between 1 and 31'
    }
    if (!isDayOfMonth(values.due_day)) {
      errors.due_day = 'Use a day between 1 and 31'
    }
  }

  if (values.rate.trim() !== '' && !RATE_PATTERN.test(values.rate.trim())) {
    errors.rate = 'Use up to four decimals, like 7.1000'
  }

  return errors
}

/** Build the request payload. Call it only once validation is clean. */
export function toNewAccount(values: AccountFormValues): NewAccount {
  const isCard = values.type === 'credit_card'
  const isPot = values.type === 'pot'

  return {
    account: {
      name: values.name.trim(),
      type: values.type,
      capture_mode: values.capture_mode,
      purpose: values.purpose.trim() === '' ? null : values.purpose.trim(),
      parent_id: isPot ? Number(values.parent_id) : null,
      opening_balance_paise: parsePaise(values.opening_balance),
      opening_date: values.opening_date,
      statement_day: isCard ? Number(values.statement_day) : null,
      due_day: isCard ? Number(values.due_day) : null,
      is_active: true,
    },
    // The rate starts on the account's opening date, so no date is asked twice.
    rate:
      values.rate.trim() === '' ? null : { rate: values.rate.trim(), frequency: values.frequency },
  }
}

/** Both card days are optional, so empty is fine; anything else must be a day. */
function isDayOfMonth(text: string): boolean {
  if (text === '') {
    return true
  }
  const day = Number(text)
  return Number.isInteger(day) && day >= 1 && day <= 31
}
