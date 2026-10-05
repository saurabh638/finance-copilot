/** Transaction data for the screen: the pages of the list, and recording. */

import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { BALANCES_KEY } from '../accounts/useAccounts'
import {
  PAGE_SIZE,
  createTransaction,
  deleteTransaction,
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
 * Tell the screen that the movements changed.
 *
 * A balance is derived from postings, so it is stale the moment one is added,
 * corrected or removed: both caches are dropped together.
 */
function useMovementsChanged(): () => void {
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: [KEY] })
    void queryClient.invalidateQueries({ queryKey: [BALANCES_KEY] })
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
