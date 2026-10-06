import { type FormEvent, useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { Account } from '../accounts/api'
import CategoryPicker from '../categories/CategoryPicker'
import type { Category, CategoryKind } from '../categories/api'
import type { MovementCreate } from './api'
import { remainingPaise } from './parts'
import SplitEditor from './SplitEditor'
import {
  KINDS,
  KIND_LABELS,
  blankMovement,
  toPayload,
  validateMovement,
  type MovementFormValues,
  type MovementKind,
  type MovementProblems,
} from './form'

interface TransactionFormProps {
  /** The accounts money can move between. */
  accounts: Account[]
  /** The category tree, so a movement can be filed as it is recorded. */
  categories: Category[]
  /** Today, given by the caller, so the form never reads the clock itself. */
  today: string
  onSubmit: (payload: MovementCreate) => void
  isSaving: boolean
  errorMessage?: string | null
}

/** The recording form. The rules live in form.ts; this renders and submits. */
export default function TransactionForm({
  accounts,
  categories,
  today,
  onSubmit,
  isSaving,
  errorMessage = null,
}: TransactionFormProps) {
  const [values, setValues] = useState<MovementFormValues>(() => blankMovement(today))
  const [problems, setProblems] = useState<MovementProblems>({})

  function change<K extends keyof MovementFormValues>(
    field: K,
    value: MovementFormValues[K],
  ): void {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = validateMovement(values)
    setProblems(found)
    if (Object.keys(found).length === 0) {
      onSubmit(toPayload(values))
    }
  }

  const accountOptions = ['', ...accounts.map((account) => String(account.id))]
  const accountLabels: Record<string, string> = {
    '': 'Choose an account',
    ...Object.fromEntries(accounts.map((account) => [String(account.id), account.name])),
  }

  const isTransfer = values.kind === 'transfer'
  // A transfer moves money without spending or earning it, so it is offered no
  // filing at all rather than an empty one.
  const filingKind: CategoryKind | null = values.kind === 'transfer' ? null : values.kind

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-4 grid gap-4 sm:max-w-md">
      <h2 className="text-lg font-semibold text-slate-900">Record a movement</h2>

      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <SelectField<MovementKind>
        label="Direction"
        id="movement-kind"
        value={values.kind}
        options={KINDS}
        labels={KIND_LABELS}
        onChange={(value) => change('kind', value)}
      />

      <TextField
        label="Amount"
        id="movement-amount"
        value={values.amount}
        inputMode="decimal"
        error={problems.amount}
        onChange={(value) => change('amount', value)}
      />

      <TextField
        label="Date"
        id="movement-date"
        type="date"
        value={values.transaction_date}
        error={problems.transaction_date}
        onChange={(value) => change('transaction_date', value)}
      />

      {isTransfer ? (
        <>
          <SelectField
            label="From account"
            id="movement-from"
            value={values.from_account_id}
            options={accountOptions}
            labels={accountLabels}
            error={problems.account_id}
            onChange={(value) => change('from_account_id', value)}
          />
          <SelectField
            label="To account"
            id="movement-to"
            value={values.to_account_id}
            options={accountOptions}
            labels={accountLabels}
            error={problems.to_account_id}
            onChange={(value) => change('to_account_id', value)}
          />
        </>
      ) : (
        <SelectField
          label="Account"
          id="movement-account"
          value={values.account_id}
          options={accountOptions}
          labels={accountLabels}
          error={problems.account_id}
          onChange={(value) => change('account_id', value)}
        />
      )}

      {filingKind !== null && (
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            id="movement-split"
            type="checkbox"
            checked={values.split}
            onChange={(event) => change('split', event.target.checked)}
            className="h-5 w-5"
          />
          Split this amount between several categories
        </label>
      )}

      {filingKind !== null && !values.split && (
        <CategoryPicker
          id="movement-category"
          label="Category (optional)"
          categories={categories}
          kind={filingKind}
          value={values.category_id}
          onChange={(value) => change('category_id', value)}
        />
      )}

      {filingKind !== null && values.split && (
        <SplitEditor
          parts={values.parts}
          categories={categories}
          kind={filingKind}
          remainingPaise={remainingPaise(values.amount, values.parts)}
          error={problems.parts}
          onChange={(parts) => change('parts', parts)}
        />
      )}

      {!isTransfer && (
        <TextField
          label="Merchant (optional)"
          id="movement-merchant"
          value={values.merchant}
          error={problems.merchant}
          onChange={(value) => change('merchant', value)}
        />
      )}

      <TextField
        label="Note (optional)"
        id="movement-note"
        value={values.note}
        error={problems.note}
        onChange={(value) => change('note', value)}
      />

      <button
        type="submit"
        disabled={isSaving}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        {isSaving ? 'Saving…' : 'Record movement'}
      </button>
    </form>
  )
}
