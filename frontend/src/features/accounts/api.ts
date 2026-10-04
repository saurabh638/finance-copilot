/**
 * Account and interest-rate calls.
 *
 * Every type comes from the generated OpenAPI schema, so a change on the server
 * surfaces here as a type error rather than a surprise at runtime.
 */

import type { components } from '../../lib/api-types'
import { requestJson } from '../../lib/api'

export type Account = components['schemas']['AccountResponse']
export type AccountCreate = components['schemas']['AccountCreate']
export type AccountType = components['schemas']['AccountType']
export type CaptureMode = components['schemas']['CaptureMode']
export type InterestRate = components['schemas']['InterestRateResponse']
export type InterestRateCreate = components['schemas']['InterestRateCreate']
export type RateFrequency = components['schemas']['RateFrequency']

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
