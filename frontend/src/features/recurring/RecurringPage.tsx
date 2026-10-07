import { useState } from 'react'

import PageHeader from '../../components/PageHeader'
import { todayIso } from '../../lib/dates'
import { useAccounts } from '../accounts/useAccounts'
import { useCategories } from '../categories/useCategories'
import RecurringForm from './RecurringForm'
import RecurringRow from './RecurringRow'
import {
  useCreateItem,
  useItems,
  useRemoveItem,
  useSetItemActive,
  useUpdateItem,
} from './useRecurring'

interface RecurringPageProps {
  /** Today, given by the caller, so a new plan starts from a date it decides. */
  today?: string
}

/**
 * The repeats screen: what is planned, and what can be done about it.
 *
 * The plans live here; the offer to confirm one lives on the Today screen, where
 * the money actually gets recorded. This screen is for the occasional visit, when
 * a rent goes up or a subscription is cancelled.
 */
export default function RecurringPage({ today = todayIso() }: RecurringPageProps) {
  const accounts = useAccounts()
  const categories = useCategories()
  const items = useItems()

  const create = useCreateItem()
  const update = useUpdateItem()
  const remove = useRemoveItem()
  const setActive = useSetItemActive()

  // A refused change is reported on the row it belongs to, because the row closes
  // its editor as soon as it has asked: what the server still holds is what the
  // user sees when they open the row again.
  const [failure, setFailure] = useState<{ id: number; message: string } | null>(null)

  const accountList = accounts.data ?? []
  const tree = categories.data ?? []
  const planned = items.data ?? []

  return (
    <>
      <PageHeader title="Repeats" />

      <section aria-label="Repeats" className="mt-6 grid gap-4">
        <p className="text-slate-700">
          Things that repeat are offered on the Today screen when their day comes round, so
          recording the rent is a tap rather than a form. Nothing here records money.
        </p>

        {accounts.isPending || categories.isPending || items.isPending ? (
          <p className="text-slate-600">Reading what repeats…</p>
        ) : (
          <>
            <RecurringForm
              accounts={accountList}
              categories={tree}
              today={today}
              onSubmit={(payload) => {
                setFailure(null)
                create.mutate(payload)
              }}
              isSaving={create.isPending}
              errorMessage={create.isError ? create.error.message : null}
            />

            <h2 className="mt-4 text-lg font-semibold text-slate-900">What repeats</h2>

            {planned.length === 0 && (
              <p className="text-slate-600">
                Nothing repeats yet. Rent, an EMI, a subscription or a salary planned above will be
                waiting on the Today screen on its day.
              </p>
            )}

            {planned.length > 0 && (
              <ul className="grid gap-2">
                {planned.map((item) => (
                  <RecurringRow
                    key={item.id}
                    item={item}
                    accounts={accountList}
                    categories={tree}
                    isSaving={
                      (update.isPending && update.variables?.id === item.id) ||
                      (remove.isPending && remove.variables === item.id) ||
                      (setActive.isPending && setActive.variables?.id === item.id)
                    }
                    errorMessage={
                      failure !== null && failure.id === item.id ? failure.message : null
                    }
                    onSave={(changed) => {
                      setFailure(null)
                      update.mutate(
                        { id: item.id, update: changed },
                        {
                          onError: (error) => setFailure({ id: item.id, message: error.message }),
                        },
                      )
                    }}
                    onSetActive={(isActive) => {
                      setFailure(null)
                      setActive.mutate(
                        { id: item.id, isActive },
                        {
                          onError: (error) => setFailure({ id: item.id, message: error.message }),
                        },
                      )
                    }}
                    onRemove={() => {
                      setFailure(null)
                      remove.mutate(item.id, {
                        onError: (error) => setFailure({ id: item.id, message: error.message }),
                      })
                    }}
                  />
                ))}
              </ul>
            )}
          </>
        )}
      </section>
    </>
  )
}
