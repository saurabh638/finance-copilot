import { useState } from 'react'

import AccountsPage from './features/accounts/AccountsPage'
import LoginPage from './features/auth/LoginPage'
import { useSession } from './features/auth/useSession'
import CategoriesPage from './features/categories/CategoriesPage'
import TransactionsPage from './features/transactions/TransactionsPage'

/** The screens the signed-in app can show. */
type Screen = 'transactions' | 'accounts' | 'categories'

const TABS: { id: Screen; label: string }[] = [
  { id: 'transactions', label: 'Transactions' },
  { id: 'accounts', label: 'Accounts' },
  { id: 'categories', label: 'Categories' },
]

/** Show the login screen until there is a session, then the chosen screen. */
export default function App() {
  const session = useSession()
  const [screen, setScreen] = useState<Screen>('transactions')

  if (session.isPending) {
    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <p className="text-slate-600">Loading…</p>
      </main>
    )
  }

  if (!session.data) {
    return <LoginPage />
  }

  return (
    <>
      <nav aria-label="Sections" className="bg-slate-100 px-6 pt-6">
        <ul className="flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <li key={tab.id}>
              <button
                type="button"
                aria-current={screen === tab.id ? 'page' : undefined}
                onClick={() => setScreen(tab.id)}
                className={`min-h-11 rounded px-4 ${
                  screen === tab.id
                    ? 'bg-slate-900 text-white'
                    : 'border border-slate-300 bg-white text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {screen === 'transactions' && <TransactionsPage />}
      {screen === 'accounts' && <AccountsPage />}
      {screen === 'categories' && <CategoriesPage />}
    </>
  )
}
