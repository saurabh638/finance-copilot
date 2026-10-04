import { type FormEvent, useState } from 'react'

import type { Account } from './api'
import RateFields from './RateFields'
import SelectField from './SelectField'
import TextField from './TextField'
import {
  ACCOUNT_TYPES,
  ACCOUNT_TYPE_LABELS,
  CAPTURE_MODES,
  CAPTURE_MODE_LABELS,
  EMPTY_ACCOUNT_FORM,
  type AccountFormErrors,
  type AccountFormValues,
  toNewAccount,
  validateAccountForm,
} from './form'
import type { NewAccount } from './useAccounts'

interface AccountFormProps {
  /** Accounts a pot may hang from. The caller passes only non-pots. */
  parents: Account[]
  onSubmit: (payload: NewAccount) => void
  isSaving: boolean
  errorMessage?: string | null
}

/** The add-account form. The rules live in form.ts; this renders and submits. */
export default function AccountForm({
  parents,
  onSubmit,
  isSaving,
  errorMessage = null,
}: AccountFormProps) {
  const [values, setValues] = useState<AccountFormValues>(EMPTY_ACCOUNT_FORM)
  const [errors, setErrors] = useState<AccountFormErrors>({})

  const isCard = values.type === 'credit_card'
  const isPot = values.type === 'pot'
  const parentOptions = ['', ...parents.map((account) => String(account.id))]
  const parentLabels = {
    '': 'Choose an account',
    ...Object.fromEntries(parents.map((account) => [String(account.id), account.name])),
  }

  function change<K extends keyof AccountFormValues>(field: K, value: AccountFormValues[K]): void {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = validateAccountForm(values)
    setErrors(found)
    if (Object.keys(found).length === 0) {
      onSubmit(toNewAccount(values))
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-4 grid gap-4 sm:max-w-md">
      <h2 className="text-lg font-semibold text-slate-900">Add an account</h2>

      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <TextField
        label="Name"
        id="account-name"
        value={values.name}
        error={errors.name}
        onChange={(value) => change('name', value)}
      />
      <SelectField
        label="Type"
        id="account-type"
        value={values.type}
        options={ACCOUNT_TYPES}
        labels={ACCOUNT_TYPE_LABELS}
        onChange={(value) => change('type', value)}
      />
      <SelectField
        label="Capture mode"
        id="account-capture_mode"
        value={values.capture_mode}
        options={CAPTURE_MODES}
        labels={CAPTURE_MODE_LABELS}
        onChange={(value) => change('capture_mode', value)}
      />
      <TextField
        label="Purpose (optional)"
        id="account-purpose"
        value={values.purpose}
        error={errors.purpose}
        onChange={(value) => change('purpose', value)}
      />

      {isPot && (
        <SelectField
          label="Parent account"
          id="account-parent_id"
          value={values.parent_id}
          options={parentOptions}
          labels={parentLabels}
          error={errors.parent_id}
          onChange={(value) => change('parent_id', value)}
        />
      )}

      <TextField
        label="Opening balance"
        id="account-opening_balance"
        value={values.opening_balance}
        error={errors.opening_balance}
        inputMode="decimal"
        onChange={(value) => change('opening_balance', value)}
      />
      <TextField
        label="Opening date"
        id="account-opening_date"
        value={values.opening_date}
        error={errors.opening_date}
        type="date"
        onChange={(value) => change('opening_date', value)}
      />

      {isCard && (
        <>
          <TextField
            label="Statement day"
            id="account-statement_day"
            value={values.statement_day}
            error={errors.statement_day}
            inputMode="numeric"
            onChange={(value) => change('statement_day', value)}
          />
          <TextField
            label="Due day"
            id="account-due_day"
            value={values.due_day}
            error={errors.due_day}
            inputMode="numeric"
            onChange={(value) => change('due_day', value)}
          />
        </>
      )}

      <RateFields
        rate={values.rate}
        frequency={values.frequency}
        error={errors.rate}
        onRateChange={(value) => change('rate', value)}
        onFrequencyChange={(value) => change('frequency', value)}
      />

      <button
        type="submit"
        disabled={isSaving}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        {isSaving ? 'Saving…' : 'Add account'}
      </button>
    </form>
  )
}
