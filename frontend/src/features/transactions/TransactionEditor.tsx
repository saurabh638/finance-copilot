import { type FormEvent, useState } from 'react'

import Field, { INPUT_CLASS } from '../../components/Field'
import TextField from '../../components/TextField'
import CategoryPicker from '../categories/CategoryPicker'
import { categoryLabel } from '../categories/tree'
import type { Category } from '../categories/api'
import type { Transaction, TransactionUpdate } from './api'
import {
  amountReason,
  editValues,
  filingKind,
  filingReason,
  hasChanges,
  toUpdate,
  validateEdit,
  type EditFormValues,
  type EditProblems,
} from './edit'

interface TransactionEditorProps {
  transaction: Transaction
  /** The category tree, so a filing can be changed where the API allows it. */
  categories: Category[]
  onSave: (update: TransactionUpdate) => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * The editor for a movement that already exists.
 *
 * The accounts and the kind are fixed, and so is the amount of a movement with
 * two postings: the API refuses to rewrite one side of a transfer, and a split's
 * parts are the amount. The filing can be changed on a movement with one posting
 * and is shown, with its reason, on one that has more.
 */
export default function TransactionEditor({
  transaction,
  categories,
  onSave,
  isSaving,
  errorMessage = null,
}: TransactionEditorProps) {
  const [values, setValues] = useState<EditFormValues>(() => editValues(transaction))
  const [problems, setProblems] = useState<EditProblems>({})
  const fixedAmount = amountReason(transaction)
  const kind = filingKind(transaction)
  const fixedFiling = filingReason(transaction)

  /** What a split is filed under, part by part; a transfer has nothing to list. */
  const partLabels = transaction.postings
    .map((posting) => categoryLabel(categories, posting.category_id))
    .filter((label): label is string => label !== null)

  function change<K extends keyof EditFormValues>(field: K, value: EditFormValues[K]): void {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = validateEdit(values, transaction)
    setProblems(found)
    if (Object.keys(found).length === 0) {
      onSave(toUpdate(values, transaction))
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="mt-3 grid gap-4 border-t border-slate-200 pt-3"
    >
      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      {fixedAmount === null ? (
        <TextField
          label="Amount"
          id="edit-amount"
          value={values.amount}
          inputMode="decimal"
          error={problems.amount}
          onChange={(value) => change('amount', value)}
        />
      ) : (
        <Field label="Amount" htmlFor="edit-amount">
          <input
            id="edit-amount"
            value={values.amount}
            disabled
            aria-describedby="edit-amount-reason"
            className={`${INPUT_CLASS} bg-slate-100 text-slate-600`}
          />
          <p id="edit-amount-reason" className="text-sm text-slate-600">
            {fixedAmount}
          </p>
        </Field>
      )}

      <TextField
        label="Date"
        id="edit-date"
        type="date"
        value={values.transaction_date}
        error={problems.transaction_date}
        onChange={(value) => change('transaction_date', value)}
      />

      {kind !== null ? (
        <CategoryPicker
          id="edit-category"
          label="Category (optional)"
          categories={categories}
          kind={kind}
          value={values.category_id}
          onChange={(value) => change('category_id', value)}
        />
      ) : (
        <Field label="Category" htmlFor="edit-category">
          <p id="edit-category-reason" className="text-sm text-slate-600">
            {fixedFiling}
          </p>
          {partLabels.length > 0 && (
            <p className="text-sm text-slate-600">Filed under: {partLabels.join(', ')}</p>
          )}
        </Field>
      )}

      <TextField
        label="Merchant (optional)"
        id="edit-merchant"
        value={values.merchant}
        error={problems.merchant}
        onChange={(value) => change('merchant', value)}
      />

      <TextField
        label="Note (optional)"
        id="edit-note"
        value={values.note}
        error={problems.note}
        onChange={(value) => change('note', value)}
      />

      <button
        type="submit"
        disabled={isSaving || !hasChanges(values, transaction)}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        {isSaving ? 'Saving…' : 'Save changes'}
      </button>
    </form>
  )
}
