import { type FormEvent, useState } from 'react'

import Field, { INPUT_CLASS } from '../../components/Field'
import TextField from '../../components/TextField'
import type { Transaction, TransactionUpdate } from './api'
import {
  TRANSFER_AMOUNT_REASON,
  canEditAmount,
  editValues,
  hasChanges,
  toUpdate,
  validateEdit,
  type EditFormValues,
  type EditProblems,
} from './edit'

interface TransactionEditorProps {
  transaction: Transaction
  onSave: (update: TransactionUpdate) => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * The editor for a movement that already exists.
 *
 * The accounts and the kind are fixed, and so is the amount of a two-sided
 * movement: the API refuses to rewrite one side of a transfer, so the field is
 * shown, disabled, with the reason beside it.
 */
export default function TransactionEditor({
  transaction,
  onSave,
  isSaving,
  errorMessage = null,
}: TransactionEditorProps) {
  const [values, setValues] = useState<EditFormValues>(() => editValues(transaction))
  const [problems, setProblems] = useState<EditProblems>({})
  const isAmountEditable = canEditAmount(transaction)

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

      {isAmountEditable ? (
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
            {TRANSFER_AMOUNT_REASON}
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
