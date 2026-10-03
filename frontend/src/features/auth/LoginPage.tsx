import { useState, type FormEvent } from 'react'

import { useLogin } from './useSession'

/** The login screen: a single form, amount of chrome kept to a minimum. */
export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useLogin()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    login.mutate({ email, password })
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold text-slate-900">Finance Co-pilot</h1>

        <div className="space-y-1">
          <label htmlFor="email" className="block text-sm text-slate-700">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="min-h-11 w-full rounded border border-slate-300 px-3"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="block text-sm text-slate-700">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="min-h-11 w-full rounded border border-slate-300 px-3"
          />
        </div>

        <button
          type="submit"
          disabled={login.isPending}
          className="min-h-11 w-full rounded bg-slate-900 px-4 text-white disabled:opacity-60"
        >
          Log in
        </button>

        {login.isError && (
          <p role="alert" className="text-sm text-red-700">
            {login.error.message}
          </p>
        )}
      </form>
    </main>
  )
}
