/** Recurring item data for the screens: the plan, and what it is owed today. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useMovementsChanged } from '../transactions/useTransactions'
import {
  confirmItem,
  createItem,
  fetchDue,
  fetchItems,
  removeItem,
  setItemActive,
  skipItem,
  updateItem,
  type RecurringItemCreate,
  type RecurringItemUpdate,
} from './api'

/**
 * The plan is cached under one key.
 *
 * Exported because adding, changing, pausing or removing an item changes what
 * the check-in offers, so the screens that do those things have to drop it.
 */
export const RECURRING_KEY = ['recurring-items'] as const

/**
 * What is owed is cached per day.
 *
 * The prefix is exported because a confirmation or a skip settles a period, and a
 * new movement can settle one without going through an item at all - a rent paid
 * by hand on the Transactions screen has to stop being owed here.
 */
export const DUE_KEY = 'recurring-due'

function dueKey(on: string) {
  return [DUE_KEY, on] as const
}

/** Every live item, paused ones included. */
export function useItems() {
  return useQuery({ queryKey: RECURRING_KEY, queryFn: fetchItems })
}

/** What is owed on a day, each with the day it is owed for. */
export function useDueItems(on: string) {
  return useQuery({ queryKey: dueKey(on), queryFn: () => fetchDue(on) })
}

/**
 * Tell the screens that the plan changed.
 *
 * An item's rhythm, amount or account decides what is owed, so the due list goes
 * with it. Nothing about an item is money, so no balance is dropped here.
 */
function useItemsChanged(): () => void {
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: RECURRING_KEY })
    void queryClient.invalidateQueries({ queryKey: [DUE_KEY] })
  }
}

/**
 * Tell the screens that a period was settled.
 *
 * Confirming writes a movement, so everything a movement changes is dropped;
 * skipping writes nothing, and dropping those caches as well costs one refetch
 * and keeps this to a single path rather than two that drift.
 */
function usePeriodChanged(): () => void {
  const onMovementsChanged = useMovementsChanged()
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: [DUE_KEY] })
    onMovementsChanged()
  }
}

/** Plan something that repeats. */
export function useCreateItem() {
  const onChanged = useItemsChanged()

  return useMutation({
    mutationFn: (payload: RecurringItemCreate) => createItem(payload),
    onSuccess: onChanged,
  })
}

/** Change an item's plan. Money already recorded is left alone. */
export function useUpdateItem() {
  const onChanged = useItemsChanged()

  return useMutation({
    mutationFn: ({ id, update }: { id: number; update: RecurringItemUpdate }) =>
      updateItem(id, update),
    onSuccess: onChanged,
  })
}

/** Remove an item. The periods it already dealt with keep their record. */
export function useRemoveItem() {
  const onChanged = useItemsChanged()

  return useMutation({
    mutationFn: (id: number) => removeItem(id),
    onSuccess: onChanged,
  })
}

/** Pause an item, or start offering it again. */
export function useSetItemActive() {
  const onChanged = useItemsChanged()

  return useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      setItemActive(id, isActive),
    onSuccess: onChanged,
  })
}

/** Confirm a period, optionally for a different amount that one time. */
export function useConfirmItem() {
  const onChanged = usePeriodChanged()

  return useMutation({
    mutationFn: ({ id, on, amountPaise }: { id: number; on: string; amountPaise?: number }) =>
      confirmItem(id, on, amountPaise),
    onSuccess: onChanged,
  })
}

/** Skip a period, which records nothing at all. */
export function useSkipItem() {
  const onChanged = usePeriodChanged()

  return useMutation({
    mutationFn: ({ id, on }: { id: number; on: string }) => skipItem(id, on),
    onSuccess: onChanged,
  })
}
