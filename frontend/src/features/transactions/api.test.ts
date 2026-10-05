import { describe, expect, it } from 'vitest'

import { PAGE_SIZE, transactionQuery, type TransactionFilters } from './api'

/** The filters the screen starts with: nothing picked, first page. */
function filters(overrides: Partial<TransactionFilters> = {}): TransactionFilters {
  return { accountId: null, from: '', to: '', limit: PAGE_SIZE, offset: 0, ...overrides }
}

describe('transactionQuery', () => {
  it('asks for the first page when nothing is filtered', () => {
    expect(transactionQuery(filters())).toBe('?limit=50&offset=0')
  })

  it('sends the account when one is picked', () => {
    expect(transactionQuery(filters({ accountId: 2 }))).toContain('account_id=2')
  })

  it('sends both ends of a date range', () => {
    const query = transactionQuery(filters({ from: '2026-10-01', to: '2026-10-31' }))

    expect(query).toContain('from=2026-10-01')
    expect(query).toContain('to=2026-10-31')
  })

  it('leaves out what is not set, rather than sending an empty value', () => {
    const query = transactionQuery(filters({ from: '2026-10-01' }))

    expect(query).not.toContain('account_id')
    expect(query).not.toContain('&to=')
  })

  it('asks for the next page by offset, keeping the same size', () => {
    expect(transactionQuery(filters({ offset: 100 }))).toBe('?limit=50&offset=100')
  })

  it('keeps the filters when the page moves on', () => {
    const query = transactionQuery(filters({ accountId: 1, from: '2026-10-01', offset: 50 }))

    expect(query).toBe('?account_id=1&from=2026-10-01&limit=50&offset=50')
  })
})
