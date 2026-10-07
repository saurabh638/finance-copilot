/**
 * Recurring item calls.
 *
 * Every type comes from the generated OpenAPI schema, so a change on the server
 * surfaces here as a type error rather than a surprise at runtime.
 */

import type { components } from '../../lib/api-types'
import { requestJson, requestNoContent } from '../../lib/api'

export type RecurringItem = components['schemas']['RecurringItemResponse']
export type RecurringItemCreate = components['schemas']['RecurringItemCreate']
export type RecurringItemUpdate = components['schemas']['RecurringItemUpdate']
export type DueItem = components['schemas']['DueItemResponse']
export type Confirmed = components['schemas']['ConfirmedResponse']
export type RecurringFrequency = RecurringItem['frequency']

/**
 * Only spending and earning can repeat, whatever the schema says the column holds.
 *
 * The server reuses the posting kind for an item and refuses everything else, so
 * the form offers these two and a screen never has to think about the rest.
 */
export type RecurringKind = Extract<RecurringItem['kind'], 'expense' | 'income'>

const ITEMS_PATH = '/api/v1/recurring-items'

/**
 * The query string for a day.
 *
 * Only what is set is sent, as the period queries do it: an empty day means
 * "today", which is the server's own default rather than a blank date for it to
 * refuse.
 */
export function dayQuery(on: string): string {
  return on === '' ? '' : `?on=${encodeURIComponent(on)}`
}

/** Every live item, paused ones included, in the order the API lists them. */
export function fetchItems(): Promise<RecurringItem[]> {
  return requestJson<RecurringItem[]>(ITEMS_PATH)
}

/** What is owed on a day, each with the day it is owed for. */
export function fetchDue(on: string): Promise<DueItem[]> {
  return requestJson<DueItem[]>(`${ITEMS_PATH}/due${dayQuery(on)}`)
}

/** Plan something that repeats. */
export function createItem(payload: RecurringItemCreate): Promise<RecurringItem> {
  return requestJson<RecurringItem>(ITEMS_PATH, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Change an item's plan, which never rewrites money it has already recorded. */
export function updateItem(itemId: number, payload: RecurringItemUpdate): Promise<RecurringItem> {
  return requestJson<RecurringItem>(`${ITEMS_PATH}/${String(itemId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/** Remove an item. The server keeps the periods it already dealt with. */
export function removeItem(itemId: number): Promise<void> {
  return requestNoContent(`${ITEMS_PATH}/${String(itemId)}`, { method: 'DELETE' })
}

/** Stop offering an item, or start offering it again. */
export function setItemActive(itemId: number, isActive: boolean): Promise<RecurringItem> {
  const action = isActive ? 'resume' : 'pause'
  return requestJson<RecurringItem>(`${ITEMS_PATH}/${String(itemId)}/${action}`, {
    method: 'POST',
  })
}

/**
 * Record this period's money.
 *
 * The day is the day asked about, and the server records the movement dated the
 * day the item was owed — not this one. An amount given here is for this period
 * only and leaves the plan alone.
 */
export function confirmItem(itemId: number, on: string, amountPaise?: number): Promise<Confirmed> {
  return requestJson<Confirmed>(`${ITEMS_PATH}/${String(itemId)}/confirm${dayQuery(on)}`, {
    method: 'POST',
    body: amountPaise === undefined ? undefined : JSON.stringify({ amount_paise: amountPaise }),
  })
}

/** Say this period is not happening. Nothing is recorded at all. */
export function skipItem(itemId: number, on: string): Promise<DueItem> {
  return requestJson<DueItem>(`${ITEMS_PATH}/${String(itemId)}/skip${dayQuery(on)}`, {
    method: 'POST',
  })
}
