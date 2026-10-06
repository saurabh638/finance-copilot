import { useState } from 'react'

import PageHeader from '../../components/PageHeader'
import { todayIso } from '../../lib/dates'
import { useAccounts } from '../accounts/useAccounts'
import { categoryLabel } from '../categories/tree'
import { useCategories } from '../categories/useCategories'
import TransactionEditor from './TransactionEditor'
import TransactionFilters from './TransactionFilters'
import TransactionForm from './TransactionForm'
import TransactionRow from './TransactionRow'
import { NO_FILTER, type MovementCreate, type MovementFilter, type TransactionUpdate } from './api'
import {
  useCreateTransaction,
  useDeleteTransaction,
  useTransactions,
  useUpdateTransaction,
} from './useTransactions'

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
  const categories = useCategories()
  const [filter, setFilter] = useState<MovementFilter>(NO_FILTER)
  const [isRecording, setIsRecording] = useState(false)
  // Bumping the key remounts the form, which is how a saved one is cleared.
  const [formKey, setFormKey] = useState(0)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const movements = useTransactions(filter)
  const recordMovement = useCreateTransaction()
  const updateMovement = useUpdateTransaction()
  const deleteMovement = useDeleteTransaction()

  const list = accounts.data ?? []
  const names = new Map(list.map((account) => [account.id, account.name]))
  const tree = categories.data ?? []
  const filingLabels = new Map(
    tree.map((category) => [category.id, categoryLabel(tree, category.id) ?? category.name]),
  )
  const shown = movements.data?.pages.flat() ?? []
  const isFiltered = filter.accountId !== null || filter.from !== '' || filter.to !== ''

  function handleSubmit(payload: MovementCreate): void {
    recordMovement.mutate(payload, {
      onSuccess: () => {
        setFormKey((current) => current + 1)
      },
    })
  }

  function openEditor(transactionId: number): void {
    setEditError(null)
    setEditingId(editingId === transactionId ? null : transactionId)
  }

  function handleSave(transactionId: number, update: TransactionUpdate): void {
    updateMovement.mutate(
      { id: transactionId, update },
      {
        onSuccess: () => {
          setEditingId(null)
          setEditError(null)
        },
        onError: (error) => setEditError(error.message),
      },
    )
  }

  function handleDelete(transactionId: number): void {
    setDeletingId(transactionId)
    setDeleteError(null)
    deleteMovement.mutate(transactionId, {
      onSuccess: () => setDeletingId(null),
      onError: (error) => {
        setDeletingId(null)
        setDeleteError(error.message)
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
          categories={tree}
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

      {deleteError !== null && (
        <p role="alert" className="mt-4 rounded bg-red-50 px-3 py-2 text-red-800">
          {deleteError}
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
          <ul className="mt-4 divide-y divide-slate-200 overflow-hidden rounded border border-slate-200 bg-white">
            {shown.map((transaction) => (
              <TransactionRow
                key={transaction.id}
                transaction={transaction}
                names={names}
                filingLabels={filingLabels}
                isEditing={editingId === transaction.id}
                isDeleting={deletingId === transaction.id}
                onEdit={() => openEditor(transaction.id)}
                onDelete={() => handleDelete(transaction.id)}
              >
                {editingId === transaction.id && (
                  <TransactionEditor
                    transaction={transaction}
                    categories={tree}
                    onSave={(update) => handleSave(transaction.id, update)}
                    isSaving={updateMovement.isPending}
                    errorMessage={editError}
                  />
                )}
              </TransactionRow>
            ))}
          </ul>
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
