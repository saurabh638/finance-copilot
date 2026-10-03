import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { checkHealth } from '../../lib/api'
import HealthStatus from './HealthStatus'

vi.mock('../../lib/api')

describe('HealthStatus', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows "Backend OK" when the health check succeeds', async () => {
    vi.mocked(checkHealth).mockResolvedValue(undefined)

    render(<HealthStatus />)

    expect(await screen.findByText('Backend OK')).toBeInTheDocument()
  })

  it('shows a clear error when the health check fails', async () => {
    const failure = new Error('Backend health check failed with HTTP 503')
    vi.mocked(checkHealth).mockRejectedValue(failure)

    render(<HealthStatus />)

    expect(await screen.findByRole('alert')).toHaveTextContent(failure.message)
  })
})
