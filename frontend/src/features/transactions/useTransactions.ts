/** Transaction data for the screen: the pages of the list, and recording. */

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { BALANCES_KEY } from '../accounts/useAccounts'
import { SPEND_KEY } from '../categories/useCategories'
import {
  PAGE_SIZE,
  createTransaction,
  deleteTransaction,
  fetchStreak,
  fetchSuggestions,
  fetchTransactions,
  updateTransaction,
  type MovementCreate,
  type MovementFilter,
  type TransactionUpdate,
} from './api'

const KEY = 'transactions'

/**
 * The movements, newest first, in pages the screen extends on request.
 *
 * The server decides the order; nothing here re-sorts. A page shorter than the
 * page size means there is nothing after it, which is how paging ends.
 */
export function useTransactions(filter: MovementFilter) {
  return useInfiniteQuery({
    queryKey: [KEY, filter],
    queryFn: ({ pageParam }) =>
      fetchTransactions({ ...filter, limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, _pages, lastOffset) =>
      lastPage.length === PAGE_SIZE ? lastOffset + PAGE_SIZE : undefined,
  })
}

/**
 * The names offered for fast entry, and the run of days.
 *
 * Both are read from history, so both are stale the moment a movement is added,
 * corrected or removed: they are cached under their own keys and dropped with it.
 */
export const SUGGESTIONS_KEY = ['suggestions'] as const
export const STREAK_KEY = ['streak'] as const

/** The names worth offering, most used first. */
export function useSuggestions() {
  return useQuery({ queryKey: SUGGESTIONS_KEY, queryFn: () => fetchSuggestions() })
}

/** How many days in a row something has been recorded, and whether today is one. */
export function useStreak() {
  return useQuery({ queryKey: STREAK_KEY, queryFn: fetchStreak })
}

/**
 * Tell the screen that the movements changed.
 *
 * A balance is derived from postings, so it is stale the moment one is added,
 * corrected or removed: both caches are dropped together. The spending report is
 * derived from the same postings, so it goes with them, and so do the suggestions
 * and the streak, which are the history itself.
 */
function useMovementsChanged(): () => void {
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: [KEY] })
    void queryClient.invalidateQueries({ queryKey: [BALANCES_KEY] })
    void queryClient.invalidateQueries({ queryKey: [SPEND_KEY] })
    void queryClient.invalidateQueries({ queryKey: SUGGESTIONS_KEY })
    void queryClient.invalidateQueries({ queryKey: STREAK_KEY })
  }
}

/** Record a movement; the list refetches from the first page on success. */
export function useCreateTransaction() {
  const onChanged = useMovementsChanged()

  return useMutation({
    mutationFn: (payload: MovementCreate) => createTransaction(payload),
    onSuccess: onChanged,
  })
}

/** Correct a movement, then refresh the list and the balances. */
export function useUpdateTransaction() {
  const onChanged = useMovementsChanged()

  return useMutation({
    mutationFn: ({ id, update }: { id: number; update: TransactionUpdate }) =>
      updateTransaction(id, update),
    onSuccess: onChanged,
  })
}

/** Remove a movement, then refresh the list and the balances. */
export function useDeleteTransaction() {
  const onChanged = useMovementsChanged()

  return useMutation({
    mutationFn: (id: number) => deleteTransaction(id),
    onSuccess: onChanged,
  })
}
