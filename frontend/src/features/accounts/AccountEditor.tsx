import RateHistory from './RateHistory'
import AccountEditForm from './AccountEditForm'
import type { Account } from './api'
import { useUpdateAccount } from './useAccounts'

interface AccountEditorProps {
  account: Account
  /** Accounts a pot may hang from. The caller passes only non-pots. */
  parents: Account[]
  /** Called on Cancel or after a save; the message is shown by the page. */
  onClose: (message?: string) => void
}

/** Everything that can be changed about one account: its fields and its rates. */
export default function AccountEditor({ account, parents, onClose }: AccountEditorProps) {
  const update = useUpdateAccount()

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <AccountEditForm
        account={account}
        parents={parents}
        onSubmit={(payload) => {
          update.mutate(
            { accountId: account.id, update: payload },
            { onSuccess: () => onClose(`${account.name} was saved.`) },
          )
        }}
        onCancel={() => onClose()}
        isSaving={update.isPending}
        errorMessage={update.isError ? update.error.message : null}
      />

      <RateHistory accountId={account.id} />
    </div>
  )
}
