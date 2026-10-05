import { type FormEvent, useState } from 'react'

import TextField from '../../components/TextField'
import { formatPaise, parsePaise } from '../../lib/money'
import {
  NUDGE,
  differenceSentence,
  monthStart,
  validateStated,
  writeOffLabel,
} from './balanceCheck'
import { useAdjustBalanceCheck, useAdjustmentShare, useCreateBalanceCheck } from './useBalanceCheck'

interface BalanceCheckPanelProps {
  accountId: number
  /** Today, given by the caller, so the panel never reads the clock itself. */
  today: string
}

/**
 * Check one account against the bank, and write the difference off if it is real.
 *
 * Two steps on purpose: comparing posts nothing, so the figures and the nudge are
 * on screen before anything moves. The write-off then uses the figures the check
 * recorded, never a fresh reading.
 */
export default function BalanceCheckPanel({ accountId, today }: BalanceCheckPanelProps) {
  const [stated, setStated] = useState('')
  const [problem, setProblem] = useState<string | undefined>()
  const compare = useCreateBalanceCheck(accountId)
  const writeOff = useAdjustBalanceCheck(accountId)
  const share = useAdjustmentShare(accountId, monthStart(today))

  const check = writeOff.data ?? compare.data ?? null
  const errorMessage = writeOff.error?.message ?? compare.error?.message ?? null
  const label = check === null ? null : writeOffLabel(check.difference_paise)

  function handleCompare(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const found = validateStated(stated)
    setProblem(found)
    if (found === undefined) {
      compare.mutate({ on: today, stated_balance_paise: parsePaise(stated), adjust: false })
    }
  }

  function handleDone(): void {
    setStated('')
    setProblem(undefined)
    compare.reset()
    writeOff.reset()
  }

  return (
    <section className="mt-3 grid gap-3 border-t border-slate-200 pt-3" aria-label="Balance check">
      {check === null ? (
        <form onSubmit={handleCompare} noValidate className="grid gap-3">
          <TextField
            label="Balance your bank shows"
            id={`check-stated-${accountId}`}
            value={stated}
            inputMode="decimal"
            autoFocus
            error={problem}
            onChange={setStated}
          />
          <button
            type="submit"
            disabled={compare.isPending}
            className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
          >
            {compare.isPending ? 'Checking…' : 'Compare'}
          </button>
        </form>
      ) : (
        <div className="grid gap-2">
          <p className="text-slate-900">
            The ledger says {formatPaise(check.computed_balance_paise)}
          </p>
          <p className="text-slate-900">Your bank says {formatPaise(check.stated_balance_paise)}</p>
          <p className="font-medium text-slate-900">{differenceSentence(check.difference_paise)}</p>

          {check.warning && (
            <p className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-900">{NUDGE}</p>
          )}

          {check.adjustment_transaction_id !== null ? (
            <p className="text-slate-700">Written off.</p>
          ) : (
            label !== null && (
              <button
                type="button"
                onClick={() => writeOff.mutate(check.id)}
                disabled={writeOff.isPending}
                className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
              >
                {writeOff.isPending ? 'Writing off…' : label}
              </button>
            )
          )}

          <button
            type="button"
            onClick={handleDone}
            className="min-h-11 rounded border border-slate-300 bg-white px-4 text-slate-900"
          >
            Done
          </button>
        </div>
      )}

      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      {share.isSuccess && (
        <p className="text-sm text-slate-600">
          {share.data.spend_paise === 0
            ? `Nothing spent this month${share.data.adjustments_paise > 0 ? `, and ${formatPaise(share.data.adjustments_paise)} written off` : ''}.`
            : `Written off this month: ${formatPaise(share.data.adjustments_paise)} of ${formatPaise(share.data.spend_paise)} spent (${share.data.share_percent}%).`}
        </p>
      )}
    </section>
  )
}
