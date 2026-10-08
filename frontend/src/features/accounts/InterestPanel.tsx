import { useState } from 'react'

import TextField from '../../components/TextField'
import { formatPaise, parsePaise } from '../../lib/money'
import { bankFigureProblem, differenceWords, periodWords, rateWords } from './interest'
import { useConfirmInterest, useDropInterest, useInterest, useProposeInterest } from './useInterest'

interface InterestPanelProps {
  accountId: number
  /** Today, given by the caller, so the surface never reads the clock itself. */
  today: string
}

/**
 * What a rate has earned: waiting to be confirmed, and already credited.
 *
 * The ledger works the interest out and the user says what the bank actually paid.
 * Both figures are shown side by side, because their difference is the one place
 * the day-count convention can be seen to be wrong — and it is a difference worth
 * looking at rather than smoothing over.
 */
export default function InterestPanel({ accountId, today }: InterestPanelProps) {
  const interest = useInterest(accountId)
  const propose = useProposeInterest(accountId)
  const confirm = useConfirmInterest(accountId)
  const drop = useDropInterest(accountId)

  /** What was typed for each period's bank figure, by period id. */
  const [figures, setFigures] = useState<Record<number, string>>({})
  /** Which period's figure is unusable, and why. */
  const [problem, setProblem] = useState<{ id: number; message: string } | null>(null)
  /** A refusal from the server about the list itself, such as working it out. */
  const [listFailure, setListFailure] = useState<string | null>(null)
  /** A refusal from the server about one period, shown on it. */
  const [rowFailure, setRowFailure] = useState<{ id: number; message: string } | null>(null)
  /** The proposal whose removal has been asked about but not yet confirmed. */
  const [discardingId, setDiscardingId] = useState<number | null>(null)

  if (interest.isPending) {
    return <p className="text-sm text-slate-600">Reading the interest…</p>
  }

  if (interest.isError) {
    return (
      <p role="alert" className="text-sm text-red-800">
        Could not read the interest: {interest.error.message}
      </p>
    )
  }

  const { credited_paise: credited, uncredited_paise: waiting, proposals, history } = interest.data

  function figureOf(creditId: number): string {
    return figures[creditId] ?? ''
  }

  /** The figure to credit: the bank's if one was typed, otherwise none. */
  function paidFigure(creditId: number): number | undefined {
    const text = figureOf(creditId)
    return text.trim() === '' ? undefined : parsePaise(text)
  }

  function handleConfirm(creditId: number): void {
    setRowFailure(null)
    const trouble = bankFigureProblem(figureOf(creditId))
    setProblem(trouble === null ? null : { id: creditId, message: trouble })
    if (trouble !== null) {
      return
    }

    confirm.mutate(
      { creditId, on: today, creditedPaise: paidFigure(creditId) },
      { onError: (cause) => setRowFailure({ id: creditId, message: cause.message }) },
    )
  }

  return (
    <section className="mt-4 grid gap-3 border-t border-slate-200 pt-4">
      <h4 className="font-medium text-slate-900">Interest</h4>

      <p className="text-sm text-slate-600">
        Credited so far <span className="text-slate-900">{formatPaise(credited)}</span>
        {waiting > 0 && (
          <>
            {' · waiting to be confirmed '}
            <span className="text-slate-900">{formatPaise(waiting)}</span>
          </>
        )}
      </p>

      <div>
        <button
          type="button"
          disabled={propose.isPending}
          onClick={() => {
            setListFailure(null)
            propose.mutate(today, {
              onError: (cause) => setListFailure(`Could not work it out: ${cause.message}`),
            })
          }}
          className="min-h-11 rounded border border-slate-300 bg-white px-4 text-slate-900 disabled:opacity-60"
        >
          {propose.isPending ? 'Working it out…' : 'Work out what has finished'}
        </button>
      </div>

      {listFailure !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {listFailure}
        </p>
      )}

      {proposals.length === 0 && (
        <p className="text-sm text-slate-600">
          Nothing is waiting. Every period that has finished since the rate started has been
          credited.
        </p>
      )}

      {proposals.length > 0 && (
        <ul aria-label="Waiting to be confirmed" className="grid gap-2">
          {proposals.map((credit) => (
            <li
              key={credit.id}
              className="grid gap-2 rounded border border-slate-300 bg-white px-3 py-3"
            >
              <p className="text-slate-900">
                {periodWords(credit)} · {rateWords(credit.rate_percent)}
              </p>
              <p className="text-sm text-slate-600">
                The ledger worked out{' '}
                <span className="text-slate-900">{formatPaise(credit.computed_paise)}</span>
              </p>

              <TextField
                label="What the bank paid (optional)"
                id={`interest-${String(credit.id)}-figure`}
                inputMode="decimal"
                value={figureOf(credit.id)}
                error={problem !== null && problem.id === credit.id ? problem.message : undefined}
                onChange={(value) => setFigures((current) => ({ ...current, [credit.id]: value }))}
              />

              {rowFailure !== null && rowFailure.id === credit.id && (
                <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
                  {rowFailure.message}
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={confirm.isPending && confirm.variables?.creditId === credit.id}
                  onClick={() => handleConfirm(credit.id)}
                  className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
                >
                  {confirm.isPending && confirm.variables?.creditId === credit.id
                    ? 'Crediting…'
                    : 'Confirm'}
                </button>

                {discardingId === credit.id ? (
                  <>
                    <button
                      type="button"
                      disabled={drop.isPending}
                      onClick={() => {
                        setRowFailure(null)
                        drop.mutate(credit.id, {
                          onError: (cause) =>
                            setRowFailure({ id: credit.id, message: cause.message }),
                          onSuccess: () => setDiscardingId(null),
                        })
                      }}
                      className="min-h-11 rounded border border-slate-300 px-4 text-slate-900 disabled:opacity-60"
                    >
                      Yes, throw it away
                    </button>
                    <button
                      type="button"
                      onClick={() => setDiscardingId(null)}
                      className="min-h-11 rounded border border-slate-300 px-4 text-slate-900"
                    >
                      Keep it
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => setDiscardingId(credit.id)}
                    className="min-h-11 rounded border border-slate-300 px-4 text-slate-900"
                  >
                    Throw it away
                  </button>
                )}
              </div>

              {discardingId === credit.id && (
                <p className="text-sm text-slate-600">
                  Something the ledger worked out wrongly can be worked out again afterwards.
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {history.length > 0 && (
        <>
          <h5 className="font-medium text-slate-900">Credited</h5>
          <ul aria-label="Credited periods" className="grid gap-1">
            {history.map((credit) => {
              const difference = differenceWords(credit)
              return (
                <li key={credit.id} className="text-sm text-slate-600">
                  <span className="text-slate-900">{periodWords(credit)}</span> ·{' '}
                  {rateWords(credit.rate_percent)} ·{' '}
                  <span className="text-slate-900">{formatPaise(credit.credited_paise ?? 0)}</span>
                  {difference !== null && <p>{difference}</p>}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}
