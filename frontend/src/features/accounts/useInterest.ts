/** Interest data for the accounts screen: the plan's arithmetic, and settling it. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useMovementsChanged } from '../transactions/useTransactions'
import { confirmInterest, dropInterest, fetchInterest, proposeInterest } from './api'

/**
 * Interest is cached per account.
 *
 * Exported as a prefix because working a period out, crediting one or throwing one
 * away all change what the panel shows.
 */
export const INTEREST_KEY = 'account-interest'

export function interestKey(accountId: number) {
  return [INTEREST_KEY, accountId] as const
}

/** An account's interest: the credited total, what is waiting, and the history. */
export function useInterest(accountId: number) {
  return useQuery({
    queryKey: interestKey(accountId),
    queryFn: () => fetchInterest(accountId),
  })
}

/**
 * Tell the screens that interest changed.
 *
 * Crediting a period writes a movement, so everything derived from movements is
 * stale with it - the balances, the list, the spending report - and that one list
 * already lives in one place. The interest itself is dropped too, because the
 * period just settled has to stop being offered.
 */
function useInterestChanged(accountId: number): () => void {
  const onMovementsChanged = useMovementsChanged()
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: interestKey(accountId) })
    onMovementsChanged()
  }
}

/** Work out every period that has finished, up to a day. */
export function useProposeInterest(accountId: number) {
  const onChanged = useInterestChanged(accountId)

  return useMutation({
    mutationFn: (through: string) => proposeInterest(accountId, through),
    onSuccess: onChanged,
  })
}

/** Credit a period, for the bank's figure or the ledger's own. */
export function useConfirmInterest(accountId: number) {
  const onChanged = useInterestChanged(accountId)

  return useMutation({
    mutationFn: ({
      creditId,
      on,
      creditedPaise,
    }: {
      creditId: number
      on: string
      creditedPaise?: number
    }) => confirmInterest(accountId, creditId, { on, creditedPaise }),
    onSuccess: onChanged,
  })
}

/** Throw a proposal away. It can be worked out again. */
export function useDropInterest(accountId: number) {
  const onChanged = useInterestChanged(accountId)

  return useMutation({
    mutationFn: (creditId: number) => dropInterest(accountId, creditId),
    onSuccess: onChanged,
  })
}
