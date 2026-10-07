import { type FormEvent, useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { Account } from '../accounts/api'
import CategoryPicker from '../categories/CategoryPicker'
import type { Category } from '../categories/api'
import type { RecurringItemCreate } from './api'
import {
  FREQUENCIES,
  FREQUENCY_LABELS,
  KINDS,
  KIND_LABELS,
  WEEKDAY_NAMES,
  blankItem,
  itemPayload,
  validateItem,
  type ItemDraft,
  type ItemProblems,
} from './recurring'

interface RecurringFormProps {
  accounts: Account[]
  categories: Category[]
  /** Today, so a new plan starts from a date the caller decides. */
  today: string
  onSubmit: (payload: RecurringItemCreate) => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * Planning something that repeats.
 *
 * The rhythm is one question in two halves: how often, and then the day it lands
 * on. Only the half the frequency asks for is shown, because a form offering both
 * a day of the month and a weekday would be asking the user a question the server
 * refuses to answer.
 */
export default function RecurringForm({
  accounts,
  categories,
  today,
  onSubmit,
  isSaving,
  errorMessage = null,
}: RecurringFormProps) {
  const [draft, setDraft] = useState<ItemDraft>(() => blankItem(today))
  const [problems, setProblems] = useState<ItemProblems>({})

  function change<K extends keyof ItemDraft>(field: K, value: ItemDraft[K]): void {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = validateItem(draft)
    setProblems(found)
    if (Object.keys(found).length === 0) {
      onSubmit(itemPayload(draft))
      setDraft(blankItem(today))
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-4 grid gap-4 sm:max-w-md">
      <h2 className="text-lg font-semibold text-slate-900">Plan something that repeats</h2>

      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <TextField
        label="Name"
        id="item-name"
        value={draft.name}
        error={problems.name}
        onChange={(value) => change('name', value)}
      />

      <SelectField<ItemDraft['kind']>
        label="What it is"
        id="item-kind"
        value={draft.kind}
        options={KINDS}
        labels={KIND_LABELS}
        onChange={(value) => change('kind', value)}
      />

      <TextField
        label="Amount"
        id="item-amount"
        inputMode="decimal"
        value={draft.amount}
        error={problems.amount}
        onChange={(value) => change('amount', value)}
      />

      <SelectField
        label="Account"
        id="item-account"
        value={draft.account_id}
        options={['', ...accounts.map((account) => String(account.id))]}
        labels={{
          '': 'Pick an account',
          ...Object.fromEntries(accounts.map((account) => [String(account.id), account.name])),
        }}
        error={problems.account_id}
        onChange={(value) => change('account_id', value)}
      />

      <CategoryPicker
        id="item-category"
        label="Filed under"
        categories={categories}
        kind={draft.kind === 'income' ? 'income' : 'expense'}
        value={draft.category_id}
        error={problems.category_id}
        onChange={(value) => change('category_id', value)}
      />

      <SelectField<ItemDraft['frequency']>
        label="How often"
        id="item-frequency"
        value={draft.frequency}
        options={FREQUENCIES}
        labels={FREQUENCY_LABELS}
        onChange={(value) => change('frequency', value)}
      />

      {draft.frequency === 'monthly' ? (
        <TextField
          label="Day of the month"
          id="item-day"
          inputMode="numeric"
          value={draft.day_of_month}
          error={problems.day_of_month}
          onChange={(value) => change('day_of_month', value)}
        />
      ) : (
        <SelectField
          label="Weekday"
          id="item-weekday"
          value={draft.weekday}
          options={WEEKDAY_NAMES.map((_name, index) => String(index))}
          labels={Object.fromEntries(WEEKDAY_NAMES.map((name, index) => [String(index), name]))}
          error={problems.weekday}
          onChange={(value) => change('weekday', value)}
        />
      )}

      <TextField
        label="Starts on"
        id="item-starts"
        type="date"
        value={draft.starts_on}
        error={problems.starts_on}
        onChange={(value) => change('starts_on', value)}
      />

      <TextField
        label="Ends on (optional)"
        id="item-ends"
        type="date"
        value={draft.ends_on}
        error={problems.ends_on}
        onChange={(value) => change('ends_on', value)}
      />

      <button
        type="submit"
        disabled={isSaving}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        {isSaving ? 'Planning…' : 'Plan it'}
      </button>
    </form>
  )
}
