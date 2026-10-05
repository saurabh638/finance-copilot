/**
 * The balance check's data: the comparison, the write-off and the month's share.
 *
 * A write-off moves a balance, other balances' caches and the transaction list,
 * so it drops all of them at once rather than leaving two screens disagreeing.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  adjustBalanceCheck,
  createBalanceCheck,
  fetchAdjustmentShare,
  type BalanceCheck,
  type BalanceCheckCreate,
} from './api'
import { BALANCES_KEY } from './useAccounts'

/** The share is cached per account and month; the prefix drops them together. */
export const SHARES_KEY = 'adjustment-share'

export function shareKey(accountId: number, month: string) {
  return [SHARES_KEY, accountId, month] as const
}

/** Everything a write-off can make stale. */
function useLedgerChanged(): () => void {
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: [BALANCES_KEY] })
    void queryClient.invalidateQueries({ queryKey: ['transactions'] })
    void queryClient.invalidateQueries({ queryKey: [SHARES_KEY] })
  }
}

/** Compare the account with the bank. Posts nothing unless the payload says to. */
export function useCreateBalanceCheck(accountId: number) {
  const onChanged = useLedgerChanged()

  return useMutation({
    mutationFn: (payload: BalanceCheckCreate) => createBalanceCheck(accountId, payload),
    onSuccess: (check: BalanceCheck) => {
      // The comparison alone changes nothing; only a write-off does.
      if (check.adjustment_transaction_id !== null) {
        onChanged()
      }
    },
  })
}

/** Write off the difference a check found earlier. */
export function useAdjustBalanceCheck(accountId: number) {
  const onChanged = useLedgerChanged()

  return useMutation({
    mutationFn: (checkId: number) => adjustBalanceCheck(accountId, checkId),
    onSuccess: onChanged,
  })
}

/** Mount it only while the panel is open. */
export function useAdjustmentShare(accountId: number, month: string) {
  return useQuery({
    queryKey: shareKey(accountId, month),
    queryFn: () => fetchAdjustmentShare(accountId, month),
  })
}
