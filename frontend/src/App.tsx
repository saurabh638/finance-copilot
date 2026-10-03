import HomePage from './features/auth/HomePage'
import LoginPage from './features/auth/LoginPage'
import { useSession } from './features/auth/useSession'

/** Show the login screen until there is a session, then the protected screen. */
export default function App() {
  const session = useSession()

  if (session.isPending) {
    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <p className="text-slate-600">Loading…</p>
      </main>
    )
  }

  return session.data ? <HomePage /> : <LoginPage />
}
