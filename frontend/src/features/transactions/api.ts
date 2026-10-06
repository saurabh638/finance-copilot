/**
 * Transaction calls, and the rule that turns the screen's filters into a query.
 *
 * Every type comes from the generated OpenAPI schema, so a change on the server
 * surfaces here as a type error rather than a surprise at runtime.
 */

import type { components } from '../../lib/api-types'
import { requestJson, requestNoContent } from '../../lib/api'

export type ExpenseCreate = components['schemas']['ExpenseCreate']
export type IncomeCreate = components['schemas']['IncomeCreate']
export type Posting = components['schemas']['PostingResponse']
export type PostingKind = components['schemas']['PostingKind']
export type Streak = components['schemas']['StreakResponse']
export type Suggestion = components['schemas']['SuggestionResponse']
export type Transaction = components['schemas']['TransactionResponse']
export type TransactionUpdate = components['schemas']['TransactionUpdate']
export type TransferCreate = components['schemas']['TransferCreate']

/** What the server accepts when recording a movement, as one of three shapes. */
export type MovementCreate = ExpenseCreate | IncomeCreate | TransferCreate

/** How many movements one page holds. The server's own maximum is 200. */
export const PAGE_SIZE = 50

/** How many names the daily screen offers as chips. */
export const SUGGESTION_LIMIT = 8

const TRANSACTIONS_PATH = '/api/v1/transactions'

/** The names worth offering for fast entry, most used first. */
export function fetchSuggestions(limit: number = SUGGESTION_LIMIT): Promise<Suggestion[]> {
  return requestJson<Suggestion[]>(`${TRANSACTIONS_PATH}/suggestions?limit=${String(limit)}`)
}

/** How many days in a row something has been recorded, and whether today is one. */
export function fetchStreak(): Promise<Streak> {
  return requestJson<Streak>(`${TRANSACTIONS_PATH}/streak`)
}

/** What the screen is currently showing. Empty text means "not filtered". */
export interface TransactionFilters {
  accountId: number | null
  from: string
  to: string
  limit: number
  offset: number
}

/** The three things the screen lets a person filter by. */
export type MovementFilter = Pick<TransactionFilters, 'accountId' | 'from' | 'to'>

/** The filters the screen starts with: everything, from the first page. */
export const NO_FILTER: MovementFilter = { accountId: null, from: '', to: '' }

/**
 * The query string for a set of filters.
 *
 * Only what is set is sent: an empty date or no account is left out entirely
 * rather than sent blank, so the server sees "no filter" instead of an invalid
 * value. The order is fixed, which makes the string easy to read and to test.
 */
export function transactionQuery(filters: TransactionFilters): string {
  const parts: string[] = []

  if (filters.accountId !== null) {
    parts.push(`account_id=${filters.accountId}`)
  }
  if (filters.from !== '') {
    parts.push(`from=${encodeURIComponent(filters.from)}`)
  }
  if (filters.to !== '') {
    parts.push(`to=${encodeURIComponent(filters.to)}`)
  }
  parts.push(`limit=${filters.limit}`, `offset=${filters.offset}`)

  return `?${parts.join('&')}`
}

/** The user's movements, newest first, as the server orders them. */
export function fetchTransactions(filters: TransactionFilters): Promise<Transaction[]> {
  return requestJson<Transaction[]>(`${TRANSACTIONS_PATH}${transactionQuery(filters)}`)
}

/** Record a movement. Money goes over the wire as integer paise. */
export function createTransaction(payload: MovementCreate): Promise<Transaction> {
  return requestJson<Transaction>(TRANSACTIONS_PATH, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Correct a movement.
 *
 * Only what is sent is changed, so an omitted field is left alone. The amount
 * may only be sent when the movement has a single posting; the accounts and the
 * kind can never change.
 */
export function updateTransaction(id: number, update: TransactionUpdate): Promise<Transaction> {
  return requestJson<Transaction>(`${TRANSACTIONS_PATH}/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  })
}

/** Remove a movement. The record is kept; it stops counting towards the balance. */
export function deleteTransaction(id: number): Promise<void> {
  return requestNoContent(`${TRANSACTIONS_PATH}/${id}`, { method: 'DELETE' })
}
