import { formatPaise } from '../../lib/money'
import { useBalance } from './useAccounts'

interface AccountBalanceProps {
  accountId: number
}

/**
 * The account's balance as it stands, with the figures it was worked out from.
 *
 * The balance is never stored: it is the opening balance plus every posting
 * since. Showing the parts means a surprising number can be checked instead of
 * merely mistrusted. Interest is one of those parts rather than another line of
 * the sum, so it is reported as "of which" - part of the movements, not beside
 * them, which is what stops it being counted twice.
 */
export default function AccountBalance({ accountId }: AccountBalanceProps) {
  const balance = useBalance(accountId)

  if (balance.isPending) {
    return <p className="text-sm text-slate-600">Working out the balance…</p>
  }

  if (balance.isError) {
    return (
      <p role="alert" className="text-sm text-red-800">
        Could not work out the balance: {balance.error.message}
      </p>
    )
  }

  return (
    <div className="text-right">
      <p className="font-medium text-slate-900">{formatPaise(balance.data.balance_paise)}</p>
      <p className="text-sm text-slate-600">
        Opening {formatPaise(balance.data.opening_balance_paise)} + movements{' '}
        {formatPaise(balance.data.postings_paise)}
      </p>
      {balance.data.interest_paise !== 0 && (
        <p className="text-sm text-slate-600">
          of which interest {formatPaise(balance.data.interest_paise)}
        </p>
      )}
    </div>
  )
}
