import { type FormEvent, useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { Account } from '../accounts/api'
import { InvalidMoneyError, parsePaise } from '../../lib/money'
import type { MovementCreate } from '../transactions/api'
import { catchUpDays, catchUpNote } from './today'

interface CatchUpFormProps {
  accounts: Account[]
  /** Today, so the days covered can be counted from the date chosen. */
  today: string
  /** The day the lump would start from, which the screen offers as yesterday. */
  defaultFrom: string
  onSubmit: (payload: MovementCreate) => void
  isSaving: boolean
  errorMessage?: string | null
}

/**
 * One figure for days that were not recorded.
 *
 * The lump is spending with no category rather than an adjustment: the money did
 * leave the account, so it belongs in the month's spending, and leaving it
 * unfiled is what puts it in the spend view's "not filed under a category" line
 * instead of pretending to be a categorised expense. The note says which days it
 * covers, so the figure explains itself in the list later.
 */
export default function CatchUpForm({
  accounts,
  today,
  defaultFrom,
  onSubmit,
  isSaving,
  errorMessage = null,
}: CatchUpFormProps) {
  const [amount, setAmount] = useState('')
  const [accountId, setAccountId] = useState('')
  const [from, setFrom] = useState(defaultFrom)
  const [problem, setProblem] = useState<string | null>(null)

  const days = catchUpDays(from, today)

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()

    let amountPaise: number
    try {
      amountPaise = parsePaise(amount)
    } catch (error) {
      if (!(error instanceof InvalidMoneyError)) {
        throw error
      }
      setProblem('Enter an amount like 1,23,456.78')
      return
    }
    if (amountPaise <= 0) {
      setProblem('The amount must be more than zero')
      return
    }
    if (accountId === '') {
      setProblem('Pick an account')
      return
    }
    if (days === 0) {
      setProblem('Pick a day on or before today')
      return
    }

    setProblem(null)
    onSubmit({
      kind: 'expense',
      account_id: Number(accountId),
      amount_paise: amountPaise,
      transaction_date: today,
      merchant: null,
      note: catchUpNote(from, today),
    })
    setAmount('')
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-4 grid gap-4 sm:max-w-md">
      <h2 className="text-lg font-semibold text-slate-900">Catch up on days I missed</h2>
      <p className="text-sm text-slate-600">
        One figure for everything unrecorded: it is spending with no category, so the month’s report
        counts it as spending that has no name on it.
      </p>

      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <TextField
        label="Total for those days"
        id="catch-up-amount"
        value={amount}
        inputMode="decimal"
        error={problem ?? undefined}
        onChange={setAmount}
      />

      <SelectField
        label="Account"
        id="catch-up-account"
        value={accountId}
        options={['', ...accounts.map((account) => String(account.id))]}
        labels={{
          '': 'Choose an account',
          ...Object.fromEntries(accounts.map((account) => [String(account.id), account.name])),
        }}
        onChange={setAccountId}
      />

      <TextField
        label="Covered from"
        id="catch-up-from"
        type="date"
        value={from}
        onChange={(value) => setFrom(value)}
      />

      <p role="status" className="text-sm text-slate-600">
        {days === 0
          ? 'Pick the first day the lump covers'
          : `${String(days)} ${days === 1 ? 'day' : 'days'} covered, up to today`}
      </p>

      <button
        type="submit"
        disabled={isSaving}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        {isSaving ? 'Recording…' : 'Record the lump'}
      </button>
    </form>
  )
}
