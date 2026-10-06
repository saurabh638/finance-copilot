import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchSession } from '../../lib/api'
import CategoriesPage from './CategoriesPage'
import type { Category } from './api'
import {
  createCategory,
  createDefaults,
  fetchCategories,
  fetchSpend,
  removeCategory,
  updateCategory,
} from './api'

vi.mock('../../lib/api')
vi.mock('./api')

const USER = { id: 1, email: 'owner@example.com' }

/** A group with two names under it, and a group of its own. */
const TREE: Category[] = [
  { id: 1, name: 'Food & groceries', kind: 'expense', parent_id: null },
  { id: 2, name: 'Groceries', kind: 'expense', parent_id: 1 },
  { id: 3, name: 'Eating out', kind: 'expense', parent_id: 1 },
  { id: 4, name: 'Salary', kind: 'income', parent_id: null },
]

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <CategoriesPage />
    </QueryClientProvider>,
  )
}

/** The page with a tree already loaded. */
async function openWithTree() {
  vi.mocked(fetchCategories).mockResolvedValue(TREE)
  renderPage()
  await screen.findByRole('heading', { name: 'The tree' })
}

beforeEach(() => {
  vi.mocked(fetchSession).mockResolvedValue(USER)
  vi.mocked(fetchSpend).mockResolvedValue({ rows: [], uncategorised_paise: 0, total_paise: 0 })
  vi.mocked(createCategory).mockResolvedValue(TREE[0])
  vi.mocked(updateCategory).mockResolvedValue(TREE[1])
  vi.mocked(removeCategory).mockResolvedValue()
  vi.mocked(createDefaults).mockResolvedValue({ created: TREE })
})

describe('CategoriesPage', () => {
  it('draws each group with the names under it', async () => {
    await openWithTree()

    expect(screen.getByRole('heading', { name: 'Food & groceries' })).toBeInTheDocument()
    expect(screen.getByText('Holds 2 names')).toBeInTheDocument()
    expect(screen.getByText('Groceries')).toBeInTheDocument()
    expect(screen.getByText('Eating out')).toBeInTheDocument()
    expect(screen.getAllByText('Nothing filed under it')).toHaveLength(3)
  })

  it('adds a name at the top level with the kind chosen', async () => {
    await openWithTree()

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Pets' } })
    fireEvent.change(screen.getByLabelText('What it is for'), { target: { value: 'income' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add name' }))

    await waitFor(() =>
      expect(createCategory).toHaveBeenCalledWith({ name: 'Pets', kind: 'income' }),
    )
  })

  it('adds a name under a group without a kind of its own', async () => {
    await openWithTree()

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Vet' } })
    fireEvent.change(screen.getByLabelText('Where it goes'), { target: { value: '1' } })

    expect(screen.queryByLabelText('What it is for')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Add name' }))

    await waitFor(() => expect(createCategory).toHaveBeenCalledWith({ name: 'Vet', parent_id: 1 }))
  })

  it('refuses a name already used among its neighbours, and says so', async () => {
    await openWithTree()

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Salary' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add name' }))

    expect(createCategory).not.toHaveBeenCalled()
    expect(screen.getByText('Salary is already used here')).toBeInTheDocument()
  })

  it('renames a name in place', async () => {
    await openWithTree()

    fireEvent.click(screen.getAllByRole('button', { name: 'Rename or move' })[1])
    fireEvent.change(screen.getByLabelText('Name of Groceries'), {
      target: { value: 'Fruit & veg' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))

    await waitFor(() => expect(updateCategory).toHaveBeenCalledWith(2, { name: 'Fruit & veg' }))
  })

  it('moves a name out to the top level', async () => {
    await openWithTree()

    fireEvent.click(screen.getAllByRole('button', { name: 'Rename or move' })[1])
    fireEvent.change(screen.getByLabelText('Move it to'), { target: { value: 'top' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))

    await waitFor(() => expect(updateCategory).toHaveBeenCalledWith(2, { parent_id: null }))
  })

  it('refuses to move a group that holds names, and does not offer it', async () => {
    await openWithTree()

    fireEvent.click(screen.getAllByRole('button', { name: 'Rename or move' })[0])

    expect(screen.queryByLabelText('Move it to')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Name of Food & groceries')).toHaveValue('Food & groceries')
  })

  it('asks before removing a name, and says what it would do', async () => {
    await openWithTree()

    fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[0])

    expect(screen.getByText(/It still holds 2/)).toBeInTheDocument()
    expect(removeCategory).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Yes, remove it' }))

    await waitFor(() => expect(removeCategory).toHaveBeenCalledWith(1))
  })

  it('keeps a name that the user changes their mind about', async () => {
    await openWithTree()

    fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[1])
    fireEvent.click(screen.getByRole('button', { name: 'Keep it' }))

    expect(removeCategory).not.toHaveBeenCalled()
  })

  it('shows what the server said when a removal is refused', async () => {
    vi.mocked(removeCategory).mockRejectedValue(new Error('Food & groceries holds names'))
    await openWithTree()

    fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Yes, remove it' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Food & groceries holds names')
  })

  it('offers the default set only when there is nothing in the tree', async () => {
    vi.mocked(fetchCategories).mockResolvedValue([])
    renderPage()

    expect(await screen.findByRole('button', { name: 'Add the default set' })).toBeInTheDocument()
  })

  it('hides the default set once the tree has anything in it', async () => {
    await openWithTree()

    expect(screen.queryByRole('button', { name: 'Add the default set' })).not.toBeInTheDocument()
  })
})
