import { type FormEvent, useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { RateFrequency } from './api'
import { RATE_FREQUENCIES, RATE_FREQUENCY_LABELS, isValidRateText } from './form'
import { useAddRate, useDeleteRate, useRates } from './useAccounts'

interface RateHistoryProps {
  accountId: number
}

interface RateDraft {
  rate: string
  frequency: RateFrequency
  from_date: string
}

const EMPTY_DRAFT: RateDraft = { rate: '', frequency: 'quarterly', from_date: '' }

/**
 * An account's dated rates: the history, newest first, and a way to add to it.
 *
 * A rate is never edited in place. A mistake is removed (soft) and the same date
 * recorded again, which is why the history stays auditable.
 */
export default function RateHistory({ accountId }: RateHistoryProps) {
  const rates = useRates(accountId)
  const addRate = useAddRate(accountId)
  const removeRate = useDeleteRate(accountId)
  const [draft, setDraft] = useState<RateDraft>(EMPTY_DRAFT)
  const [error, setError] = useState<string | null>(null)
  /** The rate whose removal has been asked about but not yet confirmed. */
  const [confirmingId, setConfirmingId] = useState<number | null>(null)

  function handleAdd(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const problem = draftError(draft)
    setError(problem)
    if (problem !== null) {
      return
    }

    addRate.mutate(
      { rate: draft.rate.trim(), frequency: draft.frequency, from_date: draft.from_date },
      { onSuccess: () => setDraft(EMPTY_DRAFT), onError: (cause) => setError(messageOf(cause)) },
    )
  }

  function handleRemove(rateId: number): void {
    setError(null)
    removeRate.mutate(rateId, { onError: (cause) => setError(messageOf(cause)) })
  }

  return (
    <section className="mt-4 grid gap-3 border-t border-slate-200 pt-4">
      <h4 className="font-medium text-slate-900">Interest rates</h4>

      {rates.isPending && <p className="text-sm text-slate-600">Loading rates…</p>}

      {rates.isError && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          Could not load the rates: {rates.error.message}
        </p>
      )}

      {rates.isSuccess && rates.data.length === 0 && (
        <p className="text-sm text-slate-600">No rates recorded yet.</p>
      )}

      {rates.data !== undefined && rates.data.length > 0 && (
        <ul className="grid gap-2">
          {rates.data.map((rate) => (
            <li key={rate.id} className="flex flex-wrap items-center justify-between gap-2">
              {confirmingId === rate.id ? (
                <>
                  <span className="text-sm text-slate-900">
                    Remove the rate from {rate.from_date}?
                  </span>
                  <span className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setConfirmingId(null)
                        handleRemove(rate.id)
                      }}
                      disabled={removeRate.isPending}
                      className="min-h-11 rounded bg-red-700 px-3 text-sm text-white disabled:opacity-60"
                    >
                      Yes, remove
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmingId(null)}
                      className="min-h-11 rounded border border-slate-300 bg-white px-3 text-sm text-slate-900"
                    >
                      Keep it
                    </button>
                  </span>
                </>
              ) : (
                <>
                  <span className="text-sm text-slate-900">
                    {rate.rate}% · {RATE_FREQUENCY_LABELS[rate.frequency]} · from {rate.from_date}
                  </span>
                  <button
                    type="button"
                    onClick={() => setConfirmingId(rate.id)}
                    className="min-h-11 rounded border border-slate-300 bg-white px-3 text-sm text-slate-700"
                  >
                    Remove
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleAdd} noValidate className="grid gap-3 sm:max-w-md">
        <h5 className="text-sm font-medium text-slate-800">Record a rate change</h5>

        {error !== null && (
          <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        )}

        <TextField
          label="New rate % a year"
          id="rate-new"
          value={draft.rate}
          inputMode="decimal"
          onChange={(value) => setDraft((current) => ({ ...current, rate: value }))}
        />
        <SelectField
          label="Credited"
          id="rate-new-frequency"
          value={draft.frequency}
          options={RATE_FREQUENCIES}
          labels={RATE_FREQUENCY_LABELS}
          onChange={(value) => setDraft((current) => ({ ...current, frequency: value }))}
        />
        <TextField
          label="From date"
          id="rate-new-from"
          type="date"
          value={draft.from_date}
          onChange={(value) => setDraft((current) => ({ ...current, from_date: value }))}
        />

        <button
          type="submit"
          disabled={addRate.isPending}
          className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
        >
          {addRate.isPending ? 'Recording…' : 'Record rate'}
        </button>
      </form>
    </section>
  )
}

/** The first problem with the draft, or null when it is ready to send. */
function draftError(draft: RateDraft): string | null {
  if (draft.rate.trim() === '') {
    return 'A rate is required'
  }
  if (!isValidRateText(draft.rate)) {
    return 'Use up to four decimals, like 7.1000'
  }
  if (draft.from_date === '') {
    return 'A start date is required'
  }
  return null
}

/** A message from anything thrown, without assuming a shape. */
function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'something went wrong'
}
