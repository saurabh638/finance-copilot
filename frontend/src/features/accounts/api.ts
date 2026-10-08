/**
 * Account and interest-rate calls.
 *
 * Every type comes from the generated OpenAPI schema, so a change on the server
 * surfaces here as a type error rather than a surprise at runtime.
 */

import type { components } from '../../lib/api-types'
import { requestJson, requestNoContent } from '../../lib/api'

export type Account = components['schemas']['AccountResponse']
export type AccountCreate = components['schemas']['AccountCreate']
export type AccountType = components['schemas']['AccountType']
export type AccountUpdate = components['schemas']['AccountUpdate']
export type AdjustmentShare = components['schemas']['AdjustmentShareResponse']
export type Balance = components['schemas']['BalanceResponse']
export type BalanceCheck = components['schemas']['BalanceCheckResponse']
export type BalanceCheckCreate = components['schemas']['BalanceCheckCreate']
export type BalanceCheckSummary = components['schemas']['BalanceCheckSummaryResponse']
export type CaptureMode = components['schemas']['CaptureMode']
export type InterestRate = components['schemas']['InterestRateResponse']
export type InterestRateCreate = components['schemas']['InterestRateCreate']
export type RateFrequency = components['schemas']['RateFrequency']
export type InterestCredit = components['schemas']['InterestCreditResponse']
export type AccountInterest = components['schemas']['AccountInterestResponse']

const ACCOUNTS_PATH = '/api/v1/accounts'

/** The signed-in user's live accounts, oldest first. */
export function fetchAccounts(): Promise<Account[]> {
  return requestJson<Account[]>(ACCOUNTS_PATH)
}

/** Create an account. Money goes over the wire as integer paise. */
export function createAccount(payload: AccountCreate): Promise<Account> {
  return requestJson<Account>(ACCOUNTS_PATH, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Record a rate from a date. Earlier rates are never touched. */
export function createRate(accountId: number, payload: InterestRateCreate): Promise<InterestRate> {
  return requestJson<InterestRate>(`${ACCOUNTS_PATH}/${accountId}/interest-rates`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Change an account's editable fields. `type` is not among them. */
export function updateAccount(accountId: number, payload: AccountUpdate): Promise<Account> {
  return requestJson<Account>(`${ACCOUNTS_PATH}/${accountId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/** The account's dated rates, newest first. */
export function fetchRates(accountId: number): Promise<InterestRate[]> {
  return requestJson<InterestRate[]>(`${ACCOUNTS_PATH}/${accountId}/interest-rates`)
}

/** Soft-delete a rate, which frees its start date for a corrected record. */
export function deleteRate(accountId: number, rateId: number): Promise<void> {
  return requestNoContent(`${ACCOUNTS_PATH}/${accountId}/interest-rates/${rateId}`, {
    method: 'DELETE',
  })
}

/**
 * The account's balance, worked out from its opening balance and its postings.
 *
 * The opening balance and the postings total come back with it, so the figure
 * can always be explained rather than merely trusted.
 */
export function fetchBalance(accountId: number): Promise<Balance> {
  return requestJson<Balance>(`${ACCOUNTS_PATH}/${accountId}/balance`)
}

/**
 * Compare the ledger with the bank.
 *
 * Nothing is written off unless `adjust` says so, which is what lets the screen
 * show the figures and the nudge before anything is posted.
 */
export function createBalanceCheck(
  accountId: number,
  payload: BalanceCheckCreate,
): Promise<BalanceCheck> {
  return requestJson<BalanceCheck>(`${ACCOUNTS_PATH}/${accountId}/balance-checks`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Write off the difference a check found earlier, using its recorded figures. */
export function adjustBalanceCheck(accountId: number, checkId: number): Promise<BalanceCheck> {
  return requestJson<BalanceCheck>(
    `${ACCOUNTS_PATH}/${accountId}/balance-checks/${checkId}/adjust`,
    { method: 'POST' },
  )
}

/** Write-offs against the month's spending, for the month given. */
export function fetchAdjustmentShare(accountId: number, month: string): Promise<AdjustmentShare> {
  return requestJson<AdjustmentShare>(
    `${ACCOUNTS_PATH}/${accountId}/adjustment-share?month=${encodeURIComponent(month)}`,
  )
}

/** An account's interest: what is credited, and what is waiting to be. */
export function fetchInterest(accountId: number): Promise<AccountInterest> {
  return requestJson<AccountInterest>(`${ACCOUNTS_PATH}/${accountId}/interest`)
}

/**
 * Work out every period that has finished, up to a day.
 *
 * The same call the daily job makes, so the screen does not have to wait for one
 * in the morning to show what a rate has earned. Running it twice proposes
 * nothing new.
 */
export function proposeInterest(accountId: number, through: string): Promise<InterestCredit[]> {
  return requestJson<InterestCredit[]>(`${ACCOUNTS_PATH}/${accountId}/interest/propose`, {
    method: 'POST',
    body: JSON.stringify({ through }),
  })
}

/**
 * Credit a period, for the figure the bank paid.
 *
 * An omitted figure means the ledger's own, which is the common case. `on` is the
 * day the confirmation was made; the money is dated the day the period ended.
 */
export function confirmInterest(
  accountId: number,
  creditId: number,
  payload: { on: string; creditedPaise?: number },
): Promise<InterestCredit> {
  return requestJson<InterestCredit>(`${ACCOUNTS_PATH}/${accountId}/interest/${creditId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ on: payload.on, credited_paise: payload.creditedPaise ?? null }),
  })
}

/** Throw a proposal away, because it should never have been worked out. */
export function dropInterest(accountId: number, creditId: number): Promise<void> {
  return requestNoContent(`${ACCOUNTS_PATH}/${accountId}/interest/${creditId}`, {
    method: 'DELETE',
  })
}
