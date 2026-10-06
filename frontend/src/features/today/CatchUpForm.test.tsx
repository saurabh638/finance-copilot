import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Account } from '../accounts/api'
import type { MovementCreate } from '../transactions/api'
import CatchUpForm from './CatchUpForm'

const SBI: Account = {
  id: 1,
  name: 'SBI',
  type: 'savings',
  purpose: null,
  capture_mode: 'statement_import',
  parent_id: null,
  opening_balance_paise: 0,
  opening_date: '2026-04-01',
  statement_day: null,
  due_day: null,
  is_active: true,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

function renderForm() {
  const onSubmit = vi.fn<(payload: MovementCreate) => void>()
  render(
    <CatchUpForm
      accounts={[SBI]}
      today="2026-10-06"
      defaultFrom="2026-10-05"
      onSubmit={onSubmit}
      isSaving={false}
    />,
  )
  return onSubmit
}

function type(field: string, value: string) {
  fireEvent.change(screen.getByLabelText(field), { target: { value } })
}

describe('CatchUpForm', () => {
  it('starts covering yesterday up to today', () => {
    renderForm()

    expect(screen.getByLabelText('Covered from')).toHaveValue('2026-10-05')
    expect(screen.getByRole('status')).toHaveTextContent('2 days covered, up to today')
  })

  it('counts the days as the dates change', () => {
    renderForm()

    type('Covered from', '2026-10-02')

    expect(screen.getByRole('status')).toHaveTextContent('5 days covered, up to today')
  })

  it('records the lump as spending with no category, dated today', () => {
    const onSubmit = renderForm()
    type('Total for those days', '2,500')
    type('Account', '1')
    type('Covered from', '2026-10-02')

    fireEvent.click(screen.getByRole('button', { name: 'Record the lump' }))

    expect(onSubmit).toHaveBeenCalledWith({
      kind: 'expense',
      account_id: 1,
      amount_paise: 250_000,
      transaction_date: '2026-10-06',
      merchant: null,
      note: 'Catch-up for 5 days to 6 Oct 2026',
    })
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty('category_id')
  })

  it('refuses an amount that is not money', () => {
    const onSubmit = renderForm()
    type('Total for those days', 'abc')

    fireEvent.click(screen.getByRole('button', { name: 'Record the lump' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Enter an amount like 1,23,456.78')).toBeInTheDocument()
  })

  it('refuses nothing at all as an amount', () => {
    const onSubmit = renderForm()
    type('Total for those days', '0')

    fireEvent.click(screen.getByRole('button', { name: 'Record the lump' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('The amount must be more than zero')).toBeInTheDocument()
  })

  it('asks for an account', () => {
    const onSubmit = renderForm()
    type('Total for those days', '500')

    fireEvent.click(screen.getByRole('button', { name: 'Record the lump' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Pick an account')).toBeInTheDocument()
  })

  it('refuses a day that has not happened yet', () => {
    const onSubmit = renderForm()
    type('Total for those days', '500')
    type('Account', '1')
    type('Covered from', '2026-10-09')

    fireEvent.click(screen.getByRole('button', { name: 'Record the lump' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Pick a day on or before today')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Pick the first day the lump covers')
  })
})
