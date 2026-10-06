import { useState } from 'react'

import PageHeader from '../../components/PageHeader'
import { todayIso } from '../../lib/dates'
import { useAccounts } from '../accounts/useAccounts'
import type { Category } from '../categories/api'
import { categoryLabel } from '../categories/tree'
import { useCategories } from '../categories/useCategories'
import type { MovementCreate } from '../transactions/api'
import { NO_FILTER } from '../transactions/api'
import {
  movementAmountText,
  movementFilings,
  movementParties,
  movementTitle,
} from '../transactions/describe'
import {
  useCreateTransaction,
  useStreak,
  useSuggestions,
  useTransactions,
} from '../transactions/useTransactions'
import CatchUpForm from './CatchUpForm'
import FastEntry from './FastEntry'
import { streakWords } from './today'

interface TodayPageProps {
  /** Today, given by the caller, so the screen never reads the clock itself. */
  today?: string
}

/** The day before a date, counted in UTC so no timezone can shift the answer. */
function dayBefore(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  const earlier = new Date(Date.UTC(year, month - 1, day))
  earlier.setUTCDate(earlier.getUTCDate() - 1)
  return earlier.toISOString().slice(0, 10)
}

/**
 * The daily screen: the run of days, today's money, and the fastest way to record
 * the next entry.
 *
 * The order is deliberate. The run comes first because it is the one thing that
 * asks the user to come back, and it never scolds: a run that ended yesterday is
 * not broken, it simply has not been added to yet. The amount comes next, because
 * it is the one figure the user always knows and nothing else can guess.
 */
export default function TodayPage({ today = todayIso() }: TodayPageProps) {
  const accounts = useAccounts()
  const categories = useCategories()
  const suggestions = useSuggestions()
  const streak = useStreak()
  const [isCatchingUp, setIsCatchingUp] = useState(false)

  const yesterday = dayBefore(today)
  const todays = useTransactions({ accountId: null, from: today, to: today })
  // The shortcuts copy the recent history, which is not the same list as today's
  // entries: "same as yesterday" needs a day this screen does not show.
  const recent = useTransactions(NO_FILTER)
  const recordMovement = useCreateTransaction()

  const accountList = accounts.data ?? []
  const tree: Category[] = categories.data ?? []
  const recorded = todays.data?.pages.flat() ?? []
  const history = recent.data?.pages.flat() ?? []
  const filingLabels = new Map(
    tree.map((category) => [category.id, categoryLabel(tree, category.id) ?? category.name]),
  )
  const names = new Map(accountList.map((account) => [account.id, account.name]))

  function handleSubmit(payload: MovementCreate): void {
    recordMovement.mutate(payload)
  }

  return (
    <>
      <PageHeader title="Today" />

      <section aria-label="Today" className="mt-6 grid gap-4">
        {streak.data !== undefined && (
          <p className="text-slate-700">
            {streakWords(streak.data.days, streak.data.today_recorded)}
          </p>
        )}

        <FastEntry
          accounts={accountList}
          categories={tree}
          suggestions={suggestions.data ?? []}
          movements={history}
          today={today}
          yesterday={yesterday}
          onSubmit={handleSubmit}
          isSaving={recordMovement.isPending}
          errorMessage={recordMovement.isError ? recordMovement.error.message : null}
        />

        <h2 className="mt-4 text-lg font-semibold text-slate-900">Today’s entries</h2>

        {todays.isPending && <p className="text-slate-600">Reading today’s entries…</p>}

        {todays.isError && (
          <p role="alert" className="rounded bg-red-50 px-3 py-2 text-red-800">
            Could not read today’s entries: {todays.error.message}
          </p>
        )}

        {todays.isSuccess && recorded.length === 0 && (
          <p className="text-slate-600">Nothing recorded today yet.</p>
        )}

        {recorded.length > 0 && (
          <ul className="grid gap-2">
            {recorded.map((movement) => {
              const filings = movementFilings(movement, filingLabels)
              return (
                <li
                  key={movement.id}
                  className="grid gap-1 rounded border border-slate-200 bg-white px-3 py-2"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-slate-900">
                      {movementTitle(movement)}
                      <span className="ml-2 text-sm text-slate-600">
                        {movementParties(movement, names)}
                      </span>
                    </span>
                    <span className="text-slate-900">{movementAmountText(movement)}</span>
                  </div>
                  {filings.length > 0 && (
                    <p className="text-sm text-slate-600">Filed under {filings.join(', ')}</p>
                  )}
                </li>
              )
            })}
          </ul>
        )}

        <button
          type="button"
          onClick={() => setIsCatchingUp(!isCatchingUp)}
          className="min-h-11 justify-self-start rounded border border-slate-300 px-4 text-slate-900"
        >
          {isCatchingUp ? 'Hide the catch-up' : 'Catch up on days I missed'}
        </button>

        {isCatchingUp && (
          <CatchUpForm
            accounts={accountList}
            today={today}
            defaultFrom={yesterday}
            onSubmit={handleSubmit}
            isSaving={recordMovement.isPending}
          />
        )}

        <p className="text-sm text-slate-600">
          Correcting or removing a movement happens on the Transactions screen, where the whole
          history is listed.
        </p>
      </section>
    </>
  )
}
