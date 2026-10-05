import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import type { Account } from '../accounts/api'
import { NO_FILTER, type MovementFilter } from './api'

interface TransactionFiltersProps {
  accounts: Account[]
  filter: MovementFilter
  onChange: (filter: MovementFilter) => void
}

/** The account and date filters above the list. */
export default function TransactionFilters({
  accounts,
  filter,
  onChange,
}: TransactionFiltersProps) {
  const options = ['', ...accounts.map((account) => String(account.id))]
  const labels: Record<string, string> = {
    '': 'Every account',
    ...Object.fromEntries(accounts.map((account) => [String(account.id), account.name])),
  }

  const isFiltered = filter.accountId !== null || filter.from !== '' || filter.to !== ''

  return (
    <section className="mt-6 grid gap-4 sm:grid-cols-3" aria-label="Filters">
      <SelectField
        label="Filter account"
        id="filter-account"
        value={filter.accountId === null ? '' : String(filter.accountId)}
        options={options}
        labels={labels}
        onChange={(value) =>
          onChange({ ...filter, accountId: value === '' ? null : Number(value) })
        }
      />
      <TextField
        label="From"
        id="filter-from"
        type="date"
        value={filter.from}
        onChange={(value) => onChange({ ...filter, from: value })}
      />
      <TextField
        label="To"
        id="filter-to"
        type="date"
        value={filter.to}
        onChange={(value) => onChange({ ...filter, to: value })}
      />
      {isFiltered && (
        <button
          type="button"
          onClick={() => onChange(NO_FILTER)}
          className="min-h-11 rounded border border-slate-300 px-4 text-slate-900 sm:col-span-3"
        >
          Clear filters
        </button>
      )}
    </section>
  )
}
