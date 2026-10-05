import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { fetchAccounts } from './features/accounts/api'
import { fetchTransactions } from './features/transactions/api'
import { fetchSession, login, logout } from './lib/api'

vi.mock('./lib/api')
vi.mock('./features/accounts/api')
vi.mock('./features/transactions/api')

const USER = { id: 1, email: 'owner@example.com' }

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  )
}

async function fillAndSubmit(email: string, password: string) {
  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))
}

describe('App', () => {
  beforeEach(() => {
    vi.mocked(fetchAccounts).mockResolvedValue([])
    vi.mocked(fetchTransactions).mockResolvedValue([])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the login form when there is no session', async () => {
    vi.mocked(fetchSession).mockResolvedValue(null)

    renderApp()

    expect(await screen.findByRole('button', { name: 'Log in' })).toBeInTheDocument()
  })

  it('opens on the transactions screen when a session already exists', async () => {
    vi.mocked(fetchSession).mockResolvedValue(USER)

    renderApp()

    expect(await screen.findByText(`Signed in as ${USER.email}`)).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Transactions' })).toBeInTheDocument()
  })

  it('moves between the two screens from the tabs', async () => {
    vi.mocked(fetchSession).mockResolvedValue(USER)

    renderApp()
    fireEvent.click(await screen.findByRole('button', { name: 'Accounts' }))

    expect(await screen.findByRole('heading', { name: 'Accounts' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Transactions' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Transactions' }))

    expect(await screen.findByRole('heading', { name: 'Transactions' })).toBeInTheDocument()
  })

  it('signs in and reveals the accounts screen', async () => {
    vi.mocked(fetchSession).mockResolvedValue(null)
    vi.mocked(login).mockResolvedValue(USER)

    renderApp()
    await fillAndSubmit(USER.email, 's3cret-passphrase')

    expect(await screen.findByText(`Signed in as ${USER.email}`)).toBeInTheDocument()
  })

  it('shows a clear error when the credentials are wrong', async () => {
    vi.mocked(fetchSession).mockResolvedValue(null)
    vi.mocked(login).mockRejectedValue(new Error('Invalid email or password'))

    renderApp()
    await fillAndSubmit(USER.email, 'wrong')

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password')
  })

  it('logs out and returns to the login form', async () => {
    vi.mocked(fetchSession).mockResolvedValue(USER)
    vi.mocked(logout).mockResolvedValue(undefined)

    renderApp()
    fireEvent.click(await screen.findByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('button', { name: 'Log in' })).toBeInTheDocument()
  })
})
