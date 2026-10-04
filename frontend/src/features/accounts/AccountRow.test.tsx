import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { formatPaise } from '../../lib/money'
import type { Account } from './api'
import AccountRow from './AccountRow'

const SAVINGS: Account = {
  id: 1,
  name: 'SBI',
  type: 'savings',
  purpose: null,
  capture_mode: 'statement_import',
  parent_id: null,
  opening_balance_paise: 12_345_678,
  opening_date: '2026-04-01',
  statement_day: null,
  due_day: null,
  is_active: true,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

function renderRow(account: Account, parentName?: string) {
  render(
    <ul>
      <AccountRow account={account} parentName={parentName} />
    </ul>,
  )
}

describe('AccountRow', () => {
  it('shows the name, the formatted balance and the settings', () => {
    renderRow(SAVINGS)

    expect(screen.getByText('SBI')).toBeInTheDocument()
    expect(screen.getByText(formatPaise(12_345_678))).toBeInTheDocument()
    expect(screen.getByText(/Savings · Statement import · from 2026-04-01/)).toBeInTheDocument()
  })

  it('names the parent of a pot', () => {
    renderRow({ ...SAVINGS, id: 2, name: 'Goa trip', type: 'pot', parent_id: 1 }, 'SBI')

    expect(screen.getByText(/part of SBI/)).toBeInTheDocument()
  })

  it('shows the card days only for a credit card', () => {
    renderRow({ ...SAVINGS, type: 'credit_card', statement_day: 5, due_day: 20 })

    expect(screen.getByText(/Statement day 5, due day 20/)).toBeInTheDocument()
  })

  it('says when an account is not active', () => {
    renderRow({ ...SAVINGS, is_active: false })

    expect(screen.getByText('Not active')).toBeInTheDocument()
  })
})
