import type { Transaction } from './api'
import {
  displayDate,
  movementAmountText,
  movementLabel,
  movementParties,
  movementTitle,
} from './describe'

interface TransactionListProps {
  transactions: Transaction[]
  names: Map<number, string>
}

/** The movements, in the order the server sent them: newest first. */
export default function TransactionList({ transactions, names }: TransactionListProps) {
  return (
    <ul className="mt-4 divide-y divide-slate-200 overflow-hidden rounded border border-slate-200 bg-white">
      {transactions.map((transaction) => (
        <li
          key={transaction.id}
          className="flex flex-wrap items-baseline justify-between gap-2 px-3 py-3"
        >
          <div>
            <p className="font-medium text-slate-900">{movementTitle(transaction)}</p>
            <p className="text-sm text-slate-600">
              {displayDate(transaction.transaction_date)} · {movementLabel(transaction)} ·{' '}
              {movementParties(transaction, names)}
            </p>
          </div>
          <p className="font-medium text-slate-900">{movementAmountText(transaction)}</p>
        </li>
      ))}
    </ul>
  )
}
