import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { fetchSession, login, logout } from './lib/api'

vi.mock('./lib/api')

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
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the login form when there is no session', async () => {
    vi.mocked(fetchSession).mockResolvedValue(null)

    renderApp()

    expect(await screen.findByRole('button', { name: 'Log in' })).toBeInTheDocument()
  })

  it('shows the home page when a session already exists', async () => {
    vi.mocked(fetchSession).mockResolvedValue(USER)

    renderApp()

    expect(await screen.findByText(`Signed in as ${USER.email}`)).toBeInTheDocument()
  })

  it('signs in and reveals the home page', async () => {
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
