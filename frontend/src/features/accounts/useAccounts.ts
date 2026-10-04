/** Account data for the accounts screen: reads and writes, through TanStack Query. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  type Account,
  type AccountCreate,
  type InterestRateCreate,
  createAccount,
  createRate,
  fetchAccounts,
} from './api'

const ACCOUNTS_KEY = ['accounts'] as const

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

/** A readable message from anything thrown, without leaking a shape assumption. */
function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'the rate was not saved'
}
