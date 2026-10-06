import { useState } from 'react'

import { formatPaise } from '../../lib/money'
import { todayIso } from '../../lib/dates'
import { monthRange, spendLines } from './spend'
import { useSpend } from './useCategories'

/**
 * What the period cost, by branch of the tree.
 *
 * The month a day falls in is the period it starts on, because "where did the
 * money go?" is asked about a month. The figures are the server's: this screen
 * adds nothing up, so a bar and the number beside it can never disagree.
 */
export default function SpendView() {
  const [range, setRange] = useState(() => monthRange(todayIso()))
  const report = useSpend(range.from, range.to)

  const rows = report.data?.rows ?? []
  const totalPaise = report.data?.total_paise ?? 0
  const uncategorisedPaise = report.data?.uncategorised_paise ?? 0
  const lines = spendLines(rows, totalPaise)

  return (
    <section aria-label="Spending by category" className="mt-10">
      <h2 className="text-lg font-semibold text-slate-900">What was spent</h2>
      <p className="mt-1 text-sm text-slate-600">
        Spending only: a transfer moves money without spending it, and a write-off has its own
        account of itself on the accounts screen.
      </p>

      <div className="mt-3 flex flex-wrap gap-4">
        <label className="grid gap-1 text-sm text-slate-700">
          From
          <input
            type="date"
            aria-label="Spending from"
            value={range.from}
            onChange={(event) => setRange((current) => ({ ...current, from: event.target.value }))}
            className="min-h-11 rounded border border-slate-300 px-3"
          />
        </label>
        <label className="grid gap-1 text-sm text-slate-700">
          To
          <input
            type="date"
            aria-label="Spending to"
            value={range.to}
            onChange={(event) => setRange((current) => ({ ...current, to: event.target.value }))}
            className="min-h-11 rounded border border-slate-300 px-3"
          />
        </label>
      </div>

      {report.isPending && <p className="mt-4 text-slate-600">Reading your spending…</p>}

      {report.isError && (
        <p role="alert" className="mt-4 rounded bg-red-50 px-3 py-2 text-red-800">
          Could not read your spending: {report.error.message}
        </p>
      )}

      {report.isSuccess && (
        <>
          <p className="mt-4 text-slate-900">
            The period cost <strong>{formatPaise(totalPaise)}</strong>.
          </p>

          {totalPaise === 0 ? (
            <p className="mt-2 text-slate-600">Nothing was spent in these dates.</p>
          ) : (
            <ul className="mt-4 grid gap-3">
              {lines.map(({ row, children, sharePercent }) => (
                <li key={row.id} className="rounded border border-slate-200 bg-white p-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h3 className="font-medium text-slate-900">{row.name}</h3>
                    <p className="text-slate-900">
                      {formatPaise(row.total_paise)}
                      <span className="ml-2 text-sm text-slate-600">{sharePercent}%</span>
                    </p>
                  </div>
                  <div
                    aria-hidden="true"
                    className="mt-2 h-2 rounded bg-slate-100"
                    title={`${sharePercent}% of the period`}
                  >
                    <div
                      className="h-2 rounded bg-slate-900"
                      style={{ width: `${Math.min(100, sharePercent)}%` }}
                    />
                  </div>
                  {children.length > 0 && (
                    <ul className="mt-2 grid gap-1 text-sm text-slate-700">
                      {children.map((child) => (
                        <li key={child.id} className="flex flex-wrap justify-between gap-2">
                          <span>{child.name}</span>
                          <span>{formatPaise(child.total_paise)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}

              {uncategorisedPaise !== 0 && (
                <li className="rounded border border-amber-200 bg-amber-50 p-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h3 className="font-medium text-amber-900">Not filed under a category</h3>
                    <p className="text-amber-900">{formatPaise(uncategorisedPaise)}</p>
                  </div>
                  <p className="mt-1 text-sm text-amber-900">
                    This is spending with no name on it, so it has no line of its own in the tree.
                  </p>
                </li>
              )}
            </ul>
          )}
        </>
      )}
    </section>
  )
}
