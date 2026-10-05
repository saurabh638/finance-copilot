import { useState } from 'react'

import PageHeader from '../../components/PageHeader'
import { todayIso } from '../../lib/dates'
import AccountEditor from './AccountEditor'
import AccountForm from './AccountForm'
import AccountRow from './AccountRow'
import BalanceCheckPanel from './BalanceCheckPanel'
import { type NewAccount, useAccounts, useCreateAccount } from './useAccounts'

interface AccountsPageProps {
  /** Today, so that a test can hold the clock still. */
  today?: string
}

/**
 * The signed-in screen: the user's accounts, what each holds, and the form that adds one.
 *
 * Money comes from the API as integer paise and is only ever formatted here.
 */
export default function AccountsPage({ today = todayIso() }: AccountsPageProps = {}) {
  const accounts = useAccounts()
  const createAccount = useCreateAccount()
  const [isAdding, setIsAdding] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [checkingId, setCheckingId] = useState<number | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const list = accounts.data ?? []
  const byId = new Map(list.map((account) => [account.id, account.name]))
  // Only a non-pot can be a parent, so only those are offered.
  const parents = list.filter((account) => account.type !== 'pot')

  function handleSubmit(payload: NewAccount): void {
    createAccount.mutate(payload, {
      onSuccess: (created) => {
        setIsAdding(false)
        setNotice(
          created.rateError === null
            ? null
            : `The account was saved, but its interest rate was not: ${created.rateError}`,
        )
      },
    })
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <PageHeader title="Accounts" />

      {notice !== null && (
        <p role="status" className="mt-4 rounded bg-amber-50 px-3 py-2 text-amber-900">
          {notice}
        </p>
      )}

      {accounts.isPending && <p className="mt-6 text-slate-600">Loading your accounts…</p>}

      {accounts.isError && (
        <p role="alert" className="mt-6 rounded bg-red-50 px-3 py-2 text-red-800">
          Could not load your accounts: {accounts.error.message}
        </p>
      )}

      {accounts.isSuccess && list.length === 0 && (
        <p className="mt-6 text-slate-600">
          No accounts yet. Add the banks, cards and wallets your money sits in.
        </p>
      )}

      {list.length > 0 && (
        <ul className="mt-6 grid gap-3">
          {list.map((account) => (
            <AccountRow
              key={account.id}
              account={account}
              parentName={account.parent_id === null ? undefined : byId.get(account.parent_id)}
              isEditing={editingId === account.id}
              onEdit={() => setEditingId(editingId === account.id ? null : account.id)}
              isChecking={checkingId === account.id}
              onCheck={() => setCheckingId(checkingId === account.id ? null : account.id)}
            >
              {editingId === account.id && (
                <AccountEditor
                  account={account}
                  parents={parents.filter((candidate) => candidate.id !== account.id)}
                  onClose={(message) => {
                    setEditingId(null)
                    setNotice(message ?? null)
                  }}
                />
              )}
              {checkingId === account.id && (
                <BalanceCheckPanel accountId={account.id} today={today} />
              )}
            </AccountRow>
          ))}
        </ul>
      )}

      {isAdding ? (
        <AccountForm
          parents={parents}
          onSubmit={handleSubmit}
          isSaving={createAccount.isPending}
          errorMessage={createAccount.isError ? createAccount.error.message : null}
        />
      ) : (
        <button
          type="button"
          onClick={() => setIsAdding(true)}
          className="mt-6 min-h-11 rounded border border-slate-300 bg-white px-4 text-slate-900"
        >
          Add account
        </button>
      )}
    </main>
  )
}
