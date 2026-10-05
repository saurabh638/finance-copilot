import { useState } from 'react'

import PageHeader from '../../components/PageHeader'
import { useAccounts } from '../accounts/useAccounts'
import TransactionFilters from './TransactionFilters'
import TransactionForm from './TransactionForm'
import TransactionList from './TransactionList'
import { NO_FILTER, type MovementCreate, type MovementFilter } from './api'
import { todayIso } from './form'
import { useCreateTransaction, useTransactions } from './useTransactions'

interface TransactionsPageProps {
  /** Today, so that a test can hold the clock still. */
  today?: string
}

/**
 * The signed-in screen for recording and reading back movements.
 *
 * Money comes from the API as integer paise and is only ever formatted here.
 */
export default function TransactionsPage({ today = todayIso() }: TransactionsPageProps) {
  const accounts = useAccounts()
  const [filter, setFilter] = useState<MovementFilter>(NO_FILTER)
  const [isRecording, setIsRecording] = useState(false)
  // Bumping the key remounts the form, which is how a saved one is cleared.
  const [formKey, setFormKey] = useState(0)
  const movements = useTransactions(filter)
  const recordMovement = useCreateTransaction()

  const list = accounts.data ?? []
  const names = new Map(list.map((account) => [account.id, account.name]))
  const shown = movements.data?.pages.flat() ?? []
  const isFiltered = filter.accountId !== null || filter.from !== '' || filter.to !== ''

  function handleSubmit(payload: MovementCreate): void {
    recordMovement.mutate(payload, {
      onSuccess: () => {
        setFormKey((current) => current + 1)
      },
    })
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <PageHeader title="Transactions" />

      <button
        type="button"
        aria-expanded={isRecording}
        onClick={() => setIsRecording(!isRecording)}
        className="mt-6 min-h-11 rounded bg-slate-900 px-4 text-white"
      >
        {isRecording ? 'Hide the form' : 'Record a movement'}
      </button>

      {isRecording && (
        <TransactionForm
          key={formKey}
          accounts={list}
          today={today}
          onSubmit={handleSubmit}
          isSaving={recordMovement.isPending}
          errorMessage={recordMovement.isError ? recordMovement.error.message : null}
        />
      )}

      <TransactionFilters accounts={list} filter={filter} onChange={setFilter} />

      {movements.isPending && <p className="mt-6 text-slate-600">Loading your movements…</p>}

      {movements.isError && (
        <p role="alert" className="mt-6 rounded bg-red-50 px-3 py-2 text-red-800">
          Could not load your movements: {movements.error.message}
        </p>
      )}

      {movements.isSuccess &&
        (shown.length === 0 ? (
          <p className="mt-6 text-slate-700">
            {isFiltered
              ? 'No movements match these filters.'
              : 'Nothing recorded yet. Record the first movement above.'}
          </p>
        ) : (
          <TransactionList transactions={shown} names={names} />
        ))}

      {movements.hasNextPage && (
        <button
          type="button"
          onClick={() => void movements.fetchNextPage()}
          disabled={movements.isFetchingNextPage}
          className="mt-4 min-h-11 rounded border border-slate-300 px-4 text-slate-900 disabled:opacity-60"
        >
          {movements.isFetchingNextPage ? 'Loading…' : 'Load more'}
        </button>
      )}
    </main>
  )
}
