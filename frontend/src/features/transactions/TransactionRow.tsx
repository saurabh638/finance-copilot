import { type ReactNode, useState } from 'react'

import type { Transaction } from './api'
import {
  displayDate,
  movementAmountText,
  movementLabel,
  movementParties,
  movementTitle,
} from './describe'

interface TransactionRowProps {
  transaction: Transaction
  names: Map<number, string>
  isEditing: boolean
  isDeleting: boolean
  onEdit: () => void
  onDelete: () => void
  /** The editor, rendered under the row while it is open. */
  children?: ReactNode
}

const SMALL_BUTTON =
  'min-h-11 rounded border border-slate-300 bg-white px-3 text-slate-900 disabled:opacity-60'

/** One movement: what it was, what it did, and the way to correct or remove it. */
export default function TransactionRow({
  transaction,
  names,
  isEditing,
  isDeleting,
  onEdit,
  onDelete,
  children,
}: TransactionRowProps) {
  const [isConfirming, setIsConfirming] = useState(false)

  return (
    <li className="px-3 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="font-medium text-slate-900">{movementTitle(transaction)}</p>
          <p className="text-sm text-slate-600">
            {displayDate(transaction.transaction_date)} · {movementLabel(transaction)} ·{' '}
            {movementParties(transaction, names)}
          </p>
        </div>
        <p className="font-medium text-slate-900">{movementAmountText(transaction)}</p>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button type="button" onClick={onEdit} disabled={isDeleting} className={SMALL_BUTTON}>
          {isEditing ? 'Close' : 'Edit'}
        </button>

        {isConfirming ? (
          <>
            <button
              type="button"
              onClick={() => {
                setIsConfirming(false)
                onDelete()
              }}
              disabled={isDeleting}
              className={SMALL_BUTTON}
            >
              {isDeleting ? 'Deleting…' : 'Confirm delete'}
            </button>
            <button
              type="button"
              onClick={() => setIsConfirming(false)}
              disabled={isDeleting}
              className={SMALL_BUTTON}
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setIsConfirming(true)}
            disabled={isDeleting}
            className={SMALL_BUTTON}
          >
            Delete
          </button>
        )}
      </div>

      {isConfirming && (
        <p className="mt-2 text-sm text-slate-700">
          Remove this movement? It leaves the list and the balance changes. The record is kept.
        </p>
      )}

      {children}
    </li>
  )
}
