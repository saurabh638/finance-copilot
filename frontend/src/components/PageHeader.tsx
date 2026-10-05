import { useLogout, useSession } from '../features/auth/useSession'

interface PageHeaderProps {
  title: string
}

/** The signed-in header: what this screen is, who is signed in, and the way out. */
export default function PageHeader({ title }: PageHeaderProps) {
  const session = useSession()
  const logout = useLogout()

  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-1 text-slate-700">Signed in as {session.data?.email}</p>
      </div>
      <button
        type="button"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
        className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
      >
        Log out
      </button>
    </header>
  )
}
