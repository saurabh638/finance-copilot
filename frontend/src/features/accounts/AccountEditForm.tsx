import { type FormEvent, useState } from 'react'

import type { Account, AccountUpdate } from './api'
import AccountFields from './AccountFields'
import {
  type AccountFormErrors,
  type AccountFormValues,
  accountToFormValues,
  toAccountUpdate,
  validateAccountForm,
} from './form'

interface AccountEditFormProps {
  account: Account
  /** Accounts a pot may hang from. The caller passes only non-pots. */
  parents: Account[]
  onSubmit: (update: AccountUpdate) => void
  onCancel: () => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * Change an account's settings.
 *
 * The type is shown read-only: the server will not change it, because postings
 * and importers key off it. Rates are managed separately, because a rate is a
 * dated record that is appended, never edited.
 */
export default function AccountEditForm({
  account,
  parents,
  onSubmit,
  onCancel,
  isSaving,
  errorMessage = null,
}: AccountEditFormProps) {
  const [values, setValues] = useState<AccountFormValues>(() => accountToFormValues(account))
  const [errors, setErrors] = useState<AccountFormErrors>({})
  const [isActive, setIsActive] = useState(account.is_active)

  function change<K extends keyof AccountFormValues>(field: K, value: AccountFormValues[K]): void {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = validateAccountForm(values)
    setErrors(found)
    if (Object.keys(found).length === 0) {
      onSubmit(toAccountUpdate(values, isActive))
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-4 grid gap-4">
      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <AccountFields
        values={values}
        errors={errors}
        parents={parents}
        isTypeEditable={false}
        onChange={change}
      />

      <div className="flex items-center gap-3">
        <input
          id="account-is_active"
          type="checkbox"
          checked={isActive}
          onChange={(event) => setIsActive(event.target.checked)}
          className="h-5 w-5"
        />
        <label htmlFor="account-is_active" className="text-sm font-medium text-slate-800">
          In active use
        </label>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={isSaving}
          className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
        >
          {isSaving ? 'Saving…' : 'Save changes'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 rounded border border-slate-300 bg-white px-4 text-slate-900"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
