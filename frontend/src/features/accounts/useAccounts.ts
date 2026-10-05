/** Account data for the accounts screen: reads and writes, through TanStack Query. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  type Account,
  type AccountCreate,
  type AccountUpdate,
  type InterestRateCreate,
  createAccount,
  createRate,
  deleteRate,
  fetchAccounts,
  fetchBalance,
  fetchRates,
  updateAccount,
} from './api'

const ACCOUNTS_KEY = ['accounts'] as const

/**
 * Balances are cached per account.
 *
 * The prefix is exported because a balance is derived from postings: recording,
 * correcting or removing a movement has to drop every one of these caches.
 */
export const BALANCES_KEY = 'account-balance'

export function balanceKey(accountId: number) {
  return [BALANCES_KEY, accountId] as const
}

/** Rates are cached per account, and only asked for when a panel opens. */
function ratesKey(accountId: number) {
  return ['interest-rates', accountId] as const
}

/** A new account, with the first rate the form collected (if it did). */
export interface NewAccount {
  account: AccountCreate
  /** Recorded from the account's opening date, so no date is asked twice. */
  rate: Omit<InterestRateCreate, 'from_date'> | null
}

/** What came back: the account always exists, the rate may not have saved. */
export interface CreatedAccount {
  account: Account
  rateError: string | null
}

/** Every account, straight from the query cache. */
export function useAccounts() {
  return useQuery({ queryKey: ACCOUNTS_KEY, queryFn: fetchAccounts })
}

/**
 * Create an account, and its first rate when the form supplied one.
 *
 * The account is the object that matters, so it is created first: if the rate
 * then fails, the account still exists and the caller is told exactly what did
 * not save rather than losing both.
 */
export function useCreateAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ account, rate }: NewAccount): Promise<CreatedAccount> => {
      const created = await createAccount(account)
      if (rate === null) {
        return { account: created, rateError: null }
      }

      try {
        await createRate(created.id, { ...rate, from_date: account.opening_date })
        return { account: created, rateError: null }
      } catch (error) {
        return { account: created, rateError: messageOf(error) }
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
    },
  })
}

/** The account's dated rates, newest first. Mount it only when a panel is open. */
export function useRates(accountId: number) {
  return useQuery({ queryKey: ratesKey(accountId), queryFn: () => fetchRates(accountId) })
}

/** One account's balance, refreshed whenever a movement touches its postings. */
export function useBalance(accountId: number) {
  return useQuery({ queryKey: balanceKey(accountId), queryFn: () => fetchBalance(accountId) })
}

/** Save an account's editable fields; the list refetches on success. */
export function useUpdateAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ accountId, update }: { accountId: number; update: AccountUpdate }) =>
      updateAccount(accountId, update),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY })
    },
  })
}

/** Append a rate. The older records are left exactly as they were. */
export function useAddRate(accountId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: InterestRateCreate) => createRate(accountId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ratesKey(accountId) })
    },
  })
}

/** Soft-delete a rate, which frees its start date for a corrected record. */
export function useDeleteRate(accountId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (rateId: number) => deleteRate(accountId, rateId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ratesKey(accountId) })
    },
  })
}

/** A readable message from anything thrown, without leaking a shape assumption. */
function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'the rate was not saved'
}
