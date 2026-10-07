import { useState } from 'react'

import TextField from '../../components/TextField'
import { formatPaise, parsePaise } from '../../lib/money'
import type { Account } from '../accounts/api'
import { dueWords } from '../recurring/recurring'
import { useConfirmItem, useDueItems, useSkipItem } from '../recurring/useRecurring'

interface DueTodayProps {
  accounts: Account[]
  /** Today, given by the caller, so the screen never reads the clock itself. */
  today: string
}

/**
 * What is waiting to be recorded today.
 *
 * One tap confirms a repeating bill, because confirming is the ordinary case and
 * the amount is usually the plan's own. Everything else - a bill that was a
 * different amount this month, or one that is not happening at all - is one step
 * further in, so the common action stays a single large target.
 *
 * Nothing here is a reminder and nothing here scolds: an item that is not dealt
 * with simply stays on this list, and the ledger says what it says.
 */
export default function DueToday({ accounts, today }: DueTodayProps) {
  const due = useDueItems(today)
  const confirm = useConfirmItem()
  const skip = useSkipItem()

  // Which row has its "something else" open, and what was typed there.
  const [openId, setOpenId] = useState<number | null>(null)
  const [amount, setAmount] = useState('')
  const [failure, setFailure] = useState<{ id: number; message: string } | null>(null)

  const owed = due.data ?? []
  if (owed.length === 0) {
    return null
  }

  const names = new Map(accounts.map((account) => [account.id, account.name]))

  /** The amount typed, or null when it cannot be read, so it is never sent. */
  function typedPaise(): number | null {
    try {
      const paise = parsePaise(amount)
      return paise > 0 ? paise : null
    } catch {
      return null
    }
  }

  return (
    <section aria-label="Waiting to be recorded" className="grid gap-2">
      <h2 className="text-lg font-semibold text-slate-900">Waiting to be recorded</h2>

      <ul className="grid gap-2">
        {owed.map((row) => (
          <li
            key={row.item.id}
            className="grid gap-2 rounded border border-slate-300 bg-white px-3 py-3"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="text-slate-900">
                <span className="font-medium">{row.item.name}</span>
                <span className="ml-2 text-sm text-slate-600">
                  {names.get(row.item.account_id) ?? 'An account that is gone'}
                </span>
              </span>
              <span className="text-slate-900">{formatPaise(row.item.amount_paise)}</span>
            </div>

            <p className="text-sm text-slate-600">{dueWords(row)}</p>

            {failure !== null && failure.id === row.item.id && (
              <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
                {failure.message}
              </p>
            )}

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={confirm.isPending && confirm.variables?.id === row.item.id}
                onClick={() => {
                  setFailure(null)
                  confirm.mutate(
                    { id: row.item.id, on: today },
                    {
                      onError: (error) => setFailure({ id: row.item.id, message: error.message }),
                    },
                  )
                }}
                className="min-h-12 min-w-40 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
              >
                {confirm.isPending && confirm.variables?.id === row.item.id
                  ? 'Recording…'
                  : 'Confirm'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setOpenId(openId === row.item.id ? null : row.item.id)
                  setAmount('')
                }}
                className="min-h-12 rounded border border-slate-300 px-4 text-slate-900"
              >
                {openId === row.item.id ? 'Never mind' : 'Something else'}
              </button>
            </div>

            {openId === row.item.id && (
              <div
                role="group"
                aria-label={`Something else for ${row.item.name}`}
                className="grid gap-2 border-t border-slate-200 pt-2"
              >
                <TextField
                  label="A different amount this time"
                  id={`due-${String(row.item.id)}-amount`}
                  inputMode="decimal"
                  value={amount}
                  onChange={setAmount}
                />

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={typedPaise() === null}
                    onClick={() => {
                      const paise = typedPaise()
                      if (paise === null) {
                        return
                      }
                      setFailure(null)
                      confirm.mutate(
                        { id: row.item.id, on: today, amountPaise: paise },
                        {
                          onError: (error) =>
                            setFailure({ id: row.item.id, message: error.message }),
                        },
                      )
                    }}
                    className="min-h-11 rounded border border-slate-300 px-4 text-slate-900 disabled:opacity-60"
                  >
                    Record that amount
                  </button>

                  <button
                    type="button"
                    disabled={skip.isPending && skip.variables?.id === row.item.id}
                    onClick={() => {
                      setFailure(null)
                      skip.mutate(
                        { id: row.item.id, on: today },
                        {
                          onError: (error) =>
                            setFailure({ id: row.item.id, message: error.message }),
                        },
                      )
                    }}
                    className="min-h-11 rounded border border-slate-300 px-4 text-slate-900 disabled:opacity-60"
                  >
                    {skip.isPending && skip.variables?.id === row.item.id
                      ? 'Skipping…'
                      : 'Not this time'}
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
