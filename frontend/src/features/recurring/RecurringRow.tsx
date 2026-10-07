import { useState } from 'react'

import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import { formatPaise } from '../../lib/money'
import type { Account } from '../accounts/api'
import CategoryPicker from '../categories/CategoryPicker'
import type { Category } from '../categories/api'
import { categoryLabel } from '../categories/tree'
import type { RecurringItem, RecurringItemUpdate } from './api'
import {
  FREQUENCIES,
  FREQUENCY_LABELS,
  KIND_LABELS,
  WEEKDAY_NAMES,
  draftFrom,
  rhythmWords,
  updatePayload,
  validateItem,
  type ItemDraft,
  type ItemProblems,
} from './recurring'

interface RecurringRowProps {
  item: RecurringItem
  accounts: Account[]
  categories: Category[]
  /** Whether a change to this row is on its way to the server. */
  isSaving: boolean
  errorMessage?: string | null
  onSave: (update: RecurringItemUpdate) => void
  onSetActive: (isActive: boolean) => void
  onRemove: () => void
}

/**
 * One repeating item: what it is, and the three things that can happen to it.
 *
 * Changing it opens the same fields as planning it did, on the row itself, so the
 * plan the user is editing is the thing they are looking at. Only what changed is
 * sent, and nothing here ever touches money already recorded: removing an item
 * leaves everything it has already written exactly where it is.
 */
export default function RecurringRow({
  item,
  accounts,
  categories,
  isSaving,
  errorMessage = null,
  onSave,
  onSetActive,
  onRemove,
}: RecurringRowProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isRemoving, setIsRemoving] = useState(false)
  const [draft, setDraft] = useState<ItemDraft>(() => draftFrom(item))
  const [problems, setProblems] = useState<ItemProblems>({})

  const account = accounts.find((row) => row.id === item.account_id)
  const filing = item.category_id === null ? null : categoryLabel(categories, item.category_id)

  function change<K extends keyof ItemDraft>(field: K, value: ItemDraft[K]): void {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  function openEditor(): void {
    setDraft(draftFrom(item))
    setProblems({})
    setIsEditing(true)
  }

  function handleSave(): void {
    const found = validateItem(draft)
    setProblems(found)
    if (Object.keys(found).length === 0) {
      onSave(updatePayload(draft, item))
      setIsEditing(false)
    }
  }

  return (
    <li className="grid gap-2 rounded border border-slate-200 bg-white px-3 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-slate-900">
          {item.name}
          {!item.is_active && <span className="ml-2 text-sm text-slate-600">Paused</span>}
        </span>
        <span className="text-slate-900">{formatPaise(item.amount_paise)}</span>
      </div>

      {/* Each fact is its own element, so a screen reader and a test can each
          find one of them rather than the whole sentence. */}
      <p className="text-sm text-slate-600">
        <span>{account?.name ?? 'An account that is gone'}</span>
        {' · '}
        <span>{KIND_LABELS[item.kind === 'income' ? 'income' : 'expense']}</span>
        {' · '}
        <span>{rhythmWords(item)}</span>
        {filing !== null && (
          <>
            {' · '}
            <span>Filed under {filing}</span>
          </>
        )}
        {item.ends_on !== null && (
          <>
            {' · '}
            <span>Ends {item.ends_on}</span>
          </>
        )}
      </p>

      {errorMessage !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      {isEditing && (
        <div
          role="group"
          aria-label={`Change ${item.name}`}
          className="grid gap-3 border-t border-slate-200 pt-3"
        >
          <TextField
            label="Name"
            id={`item-${String(item.id)}-name`}
            value={draft.name}
            error={problems.name}
            onChange={(value) => change('name', value)}
          />

          <TextField
            label="Amount"
            id={`item-${String(item.id)}-amount`}
            inputMode="decimal"
            value={draft.amount}
            error={problems.amount}
            onChange={(value) => change('amount', value)}
          />

          <SelectField
            label="Account"
            id={`item-${String(item.id)}-account`}
            value={draft.account_id}
            options={accounts.map((row) => String(row.id))}
            labels={Object.fromEntries(accounts.map((row) => [String(row.id), row.name]))}
            error={problems.account_id}
            onChange={(value) => change('account_id', value)}
          />

          <CategoryPicker
            id={`item-${String(item.id)}-category`}
            label="Filed under"
            categories={categories}
            kind={draft.kind === 'income' ? 'income' : 'expense'}
            value={draft.category_id}
            error={problems.category_id}
            onChange={(value) => change('category_id', value)}
          />

          <SelectField<ItemDraft['frequency']>
            label="How often"
            id={`item-${String(item.id)}-frequency`}
            value={draft.frequency}
            options={FREQUENCIES}
            labels={FREQUENCY_LABELS}
            onChange={(value) => change('frequency', value)}
          />

          {draft.frequency === 'monthly' ? (
            <TextField
              label="Day of the month"
              id={`item-${String(item.id)}-day`}
              inputMode="numeric"
              value={draft.day_of_month}
              error={problems.day_of_month}
              onChange={(value) => change('day_of_month', value)}
            />
          ) : (
            <SelectField
              label="Weekday"
              id={`item-${String(item.id)}-weekday`}
              value={draft.weekday}
              options={WEEKDAY_NAMES.map((_name, index) => String(index))}
              labels={Object.fromEntries(WEEKDAY_NAMES.map((name, index) => [String(index), name]))}
              error={problems.weekday}
              onChange={(value) => change('weekday', value)}
            />
          )}

          {/* The direction cannot be changed: the money it already recorded was
              spent or received, and a name's kind is what decides which. */}
          <p className="text-sm text-slate-600">
            {KIND_LABELS[item.kind === 'income' ? 'income' : 'expense']} · starting {item.starts_on}
          </p>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={isSaving}
              onClick={handleSave}
              className="min-h-11 rounded bg-slate-900 px-4 text-white disabled:opacity-60"
            >
              {isSaving ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="min-h-11 rounded border border-slate-300 px-4 text-slate-900"
            >
              Never mind
            </button>
          </div>
        </div>
      )}

      {isRemoving && (
        <div
          role="group"
          aria-label={`Remove ${item.name}`}
          className="grid gap-2 border-t border-slate-200 pt-3"
        >
          <p className="text-slate-900">
            Remove {item.name}? The movements it has already recorded stay in the ledger.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={isSaving}
              onClick={onRemove}
              className="min-h-11 rounded bg-red-700 px-4 text-white disabled:opacity-60"
            >
              Yes, remove it
            </button>
            <button
              type="button"
              onClick={() => setIsRemoving(false)}
              className="min-h-11 rounded border border-slate-300 px-4 text-slate-900"
            >
              Keep it
            </button>
          </div>
        </div>
      )}

      {!isEditing && !isRemoving && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={openEditor}
            className="min-h-11 rounded border border-slate-300 px-4 text-slate-900"
          >
            Change
          </button>
          <button
            type="button"
            disabled={isSaving}
            onClick={() => onSetActive(!item.is_active)}
            className="min-h-11 rounded border border-slate-300 px-4 text-slate-900 disabled:opacity-60"
          >
            {item.is_active ? 'Pause' : 'Start it again'}
          </button>
          <button
            type="button"
            onClick={() => setIsRemoving(true)}
            className="min-h-11 rounded border border-slate-300 px-4 text-slate-900"
          >
            Remove
          </button>
        </div>
      )}
    </li>
  )
}
