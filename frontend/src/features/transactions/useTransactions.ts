/** Transaction data for the screen: the pages of the list, and recording. */

import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import {
  PAGE_SIZE,
  createTransaction,
  fetchTransactions,
  type MovementCreate,
  type MovementFilter,
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

/** Record a movement; the list refetches from the first page on success. */
export function useCreateTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: MovementCreate) => createTransaction(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [KEY] })
    },
  })
}
