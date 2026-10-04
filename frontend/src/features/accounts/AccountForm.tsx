import { type FormEvent, useState } from 'react'

import type { Account } from './api'
import AccountFields from './AccountFields'
import RateFields from './RateFields'
import {
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

      <AccountFields
        values={values}
        errors={errors}
        parents={parents}
        isTypeEditable
        onChange={change}
      />

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
