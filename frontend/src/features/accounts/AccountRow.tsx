import type { ReactNode } from 'react'

import AccountBalance from './AccountBalance'
import type { Account } from './api'
import { ACCOUNT_TYPE_LABELS, CAPTURE_MODE_LABELS } from './form'

interface AccountRowProps {
  account: Account
  /** The pot's parent, so a sub-balance reads as part of something. */
  parentName?: string | undefined
  isEditing: boolean
  onEdit: () => void
  isChecking: boolean
  onCheck: () => void
  isShowingInterest: boolean
  onShowInterest: () => void
  /** The editor, the balance check or the interest, under the summary while open. */
  children?: ReactNode
}

/** One account as the user reads it: what it is, what it holds, what it is. */
export default function AccountRow({
  account,
  parentName,
  isEditing,
  onEdit,
  isChecking,
  onCheck,
  isShowingInterest,
  onShowInterest,
  children,
}: AccountRowProps) {
  return (
    <li className="rounded border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium text-slate-900">{account.name}</h3>
        <AccountBalance accountId={account.id} />
      </div>
      <p className="mt-1 text-sm text-slate-600">
        {ACCOUNT_TYPE_LABELS[account.type]} · {CAPTURE_MODE_LABELS[account.capture_mode]} · from{' '}
        {account.opening_date}
        {parentName !== undefined ? ` · part of ${parentName}` : ''}
      </p>
      {account.type === 'credit_card' && account.statement_day !== null && (
        <p className="mt-1 text-sm text-slate-600">
          Statement day {account.statement_day}
          {account.due_day !== null ? `, due day ${account.due_day}` : ''}
        </p>
      )}
      {!account.is_active && <p className="mt-1 text-sm text-slate-600">Not active</p>}

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onEdit}
          className="min-h-11 rounded border border-slate-300 bg-white px-4 text-slate-900"
        >
          {isEditing ? 'Close' : 'Edit'}
        </button>
        <button
          type="button"
          onClick={onCheck}
          className="min-h-11 rounded border border-slate-300 bg-white px-4 text-slate-900"
        >
          {isChecking ? 'Cancel check' : 'Check balance'}
        </button>
        <button
          type="button"
          onClick={onShowInterest}
          className="min-h-11 rounded border border-slate-300 bg-white px-4 text-slate-900"
        >
          {isShowingInterest ? 'Hide interest' : 'Interest'}
        </button>
      </div>

      {children}
    </li>
  )
}
