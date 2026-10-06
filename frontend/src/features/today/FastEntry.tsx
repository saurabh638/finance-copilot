import { type FormEvent, useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { Account } from '../accounts/api'
import CategoryPicker from '../categories/CategoryPicker'
import type { Category } from '../categories/api'
import type { MovementCreate, Suggestion, Transaction } from '../transactions/api'
import {
  KINDS,
  KIND_LABELS,
  blankMovement,
  toPayload,
  validateMovement,
  type MovementFormValues,
  type MovementKind,
  type MovementProblems,
} from '../transactions/form'
import { filledBy, movementOn } from './today'

interface FastEntryProps {
  accounts: Account[]
  categories: Category[]
  /** What the history remembers, as chips. */
  suggestions: Suggestion[]
  /** What has already been recorded, so "same as yesterday" can copy it. */
  movements: Transaction[]
  today: string
  yesterday: string
  onSubmit: (payload: MovementCreate) => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * Recording today's money in as few taps as possible.
 *
 * The amount comes first, because it is the one thing the user always knows and
 * nothing else can guess. The chips then bring a name's account and category with
 * them, and "same as yesterday" brings everything: the rules for what a movement
 * is and how it is sent are the ones the recording form already uses, so this
 * screen is only a faster way to fill them in.
 */
export default function FastEntry({
  accounts,
  categories,
  suggestions,
  movements,
  today,
  yesterday,
  onSubmit,
  isSaving,
  errorMessage = null,
}: FastEntryProps) {
  const [values, setValues] = useState<MovementFormValues>(() => blankMovement(today))
  const [problems, setProblems] = useState<MovementProblems>({})

  function change<K extends keyof MovementFormValues>(
    field: K,
    value: MovementFormValues[K],
  ): void {
    setValues((current) => ({ ...current, [field]: value }))
  }

  /** One tap on a chip: the name, its account and its category, and its amount if none was typed. */
  function fillFrom(suggestion: Suggestion): void {
    setValues((current) => ({
      ...current,
      ...filledBy(suggestion),
      amount: current.amount === '' ? (filledBy(suggestion).amount ?? '') : current.amount,
    }))
  }

  /** "Same as yesterday": everything, from the last movement on that day. */
  function copyDay(day: string): void {
    const source = movementOn(movements, day)
    if (source === null) {
      return
    }
    const [only] = source.postings
    if (only === undefined) {
      return
    }
    setValues((current) => ({
      ...current,
      amount: String(Math.abs(only.amount_paise) / 100),
      merchant: source.merchant ?? '',
      account_id: String(only.account_id),
      category_id: only.category_id === null ? '' : String(only.category_id),
      kind: only.kind === 'income' ? 'income' : 'expense',
    }))
    setProblems({})
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = validateMovement(values)
    setProblems(found)
    if (Object.keys(found).length === 0) {
      onSubmit(toPayload(values))
      setValues(blankMovement(today))
    }
  }

  const accountOptions = ['', ...accounts.map((account) => String(account.id))]
  const accountLabels: Record<string, string> = {
    '': 'Choose an account',
    ...Object.fromEntries(accounts.map((account) => [String(account.id), account.name])),
  }
  const hasYesterday = movementOn(movements, yesterday) !== null

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-4 grid gap-4">
      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <TextField
          label="Amount"
          id="today-amount"
          value={values.amount}
          inputMode="decimal"
          autoFocus
          error={problems.amount}
          onChange={(value) => change('amount', value)}
        />
        <SelectField<MovementKind>
          label="Direction"
          id="today-kind"
          value={values.kind}
          options={KINDS}
          labels={KIND_LABELS}
          onChange={(value) => change('kind', value)}
        />
      </div>

      {suggestions.length > 0 && (
        <fieldset className="border-0 p-0">
          <legend className="text-sm font-medium text-slate-700">Used often</legend>
          <ul className="mt-2 flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <li key={suggestion.merchant}>
                <button
                  type="button"
                  onClick={() => fillFrom(suggestion)}
                  className="min-h-11 rounded-full border border-slate-300 bg-white px-4 text-slate-900"
                >
                  {suggestion.merchant}
                </button>
              </li>
            ))}
          </ul>
        </fieldset>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => copyDay(yesterday)}
          disabled={!hasYesterday}
          className="min-h-11 rounded border border-slate-300 px-4 text-slate-900 disabled:opacity-60"
        >
          Same as yesterday
        </button>
        <button
          type="button"
          onClick={() => copyDay(today)}
          disabled={movementOn(movements, today) === null}
          className="min-h-11 rounded border border-slate-300 px-4 text-slate-900 disabled:opacity-60"
        >
          Repeat last
        </button>
      </div>

      <SelectField
        label="Account"
        id="today-account"
        value={values.account_id}
        options={accountOptions}
        labels={accountLabels}
        error={problems.account_id}
        onChange={(value) => change('account_id', value)}
      />

      <CategoryPicker
        id="today-category"
        label="Category (optional)"
        categories={categories}
        kind={values.kind === 'income' ? 'income' : 'expense'}
        value={values.category_id}
        onChange={(value) => change('category_id', value)}
      />

      <TextField
        label="Merchant (optional)"
        id="today-merchant"
        value={values.merchant}
        error={problems.merchant}
        onChange={(value) => change('merchant', value)}
      />

      <button
        type="submit"
        disabled={isSaving}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        {isSaving ? 'Saving…' : 'Record it'}
      </button>
    </form>
  )
}
