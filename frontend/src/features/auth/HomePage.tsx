import { useLogout, useSession } from './useSession'

/** The protected screen. A placeholder until the real screens arrive. */
export default function HomePage() {
  const session = useSession()
  const logout = useLogout()

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <h1 className="text-2xl font-semibold text-slate-900">Finance Co-pilot</h1>
      <p className="mt-2 text-slate-700">Signed in as {session.data?.email}</p>
      <button
        type="button"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
        className="mt-4 min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        Log out
      </button>
    </main>
  )
}
