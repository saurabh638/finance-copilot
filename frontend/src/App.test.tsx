import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { checkHealth } from './lib/api'
import App from './App'

vi.mock('./lib/api')

describe('App', () => {
  it('renders the application heading', () => {
    vi.mocked(checkHealth).mockResolvedValue(undefined)

    render(<App />)

    expect(screen.getByRole('heading', { name: 'Finance Co-pilot' })).toBeInTheDocument()
  })
})
