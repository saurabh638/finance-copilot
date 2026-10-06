import TextField from '../../components/TextField'
import { formatPaise } from '../../lib/money'
import CategoryPicker from '../categories/CategoryPicker'
import type { Category, CategoryKind } from '../categories/api'
import { PARTS_MIN, addPart, blankPart, removePart, type MovementPart } from './parts'

interface SplitEditorProps {
  /** What the parts hold so far, in the order they are shown. */
  parts: MovementPart[]
  /** The tree every part is filed in. */
  categories: Category[]
  /** Which kind of name may be chosen in each part. */
  kind: CategoryKind
  /** What is left of the amount after the parts, or null until the amount is money. */
  remainingPaise: number | null
  /** What is wrong with the parts, when something is. */
  error?: string
  onChange: (parts: MovementPart[]) => void
}

/**
 * One amount, filed under several names.
 *
 * The amount above stays the source of truth: the parts are a reading of it, and
 * the line at the bottom says how much of it is still to be allocated. Removing a
 * part stops at two, because one part is simply the whole amount.
 */
export default function SplitEditor({
  parts,
  categories,
  kind,
  remainingPaise,
  error,
  onChange,
}: SplitEditorProps) {
  function changePart(index: number, changed: Partial<MovementPart>): void {
    onChange(parts.map((part, at) => (at === index ? { ...part, ...changed } : part)))
  }

  /** A part holding whatever is left, so the parts can be made to add up. */
  function addRemainder(): void {
    onChange([...parts, { ...blankPart(), amount: formatPaise(remainingPaise ?? 0) }])
  }

  return (
    <fieldset className="grid gap-3 border-0 p-0">
      <legend className="text-sm font-medium text-slate-700">Parts of this amount</legend>

      {parts.map((part, index) => (
        <div key={index} className="grid gap-2 rounded border border-slate-200 p-3">
          <TextField
            label={`Part ${index + 1} amount`}
            id={`split-amount-${index}`}
            value={part.amount}
            inputMode="decimal"
            onChange={(value) => changePart(index, { amount: value })}
          />
          <CategoryPicker
            id={`split-category-${index}`}
            label={`Part ${index + 1} category`}
            categories={categories}
            kind={kind}
            value={part.category_id}
            onChange={(value) => changePart(index, { category_id: value })}
          />
          {parts.length > PARTS_MIN && (
            <button
              type="button"
              aria-label={`Remove part ${index + 1}`}
              onClick={() => onChange(removePart(parts, index))}
              className="min-h-11 justify-self-start rounded border border-slate-300 px-3 text-sm text-slate-700"
            >
              Remove
            </button>
          )}
        </div>
      ))}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onChange(addPart(parts))}
          className="min-h-11 rounded border border-slate-300 px-3 text-sm text-slate-700"
        >
          Add a part
        </button>
        {remainingPaise !== null && remainingPaise > 0 && (
          <button
            type="button"
            onClick={addRemainder}
            className="min-h-11 rounded border border-slate-300 px-3 text-sm text-slate-700"
          >
            Add {formatPaise(remainingPaise)}
          </button>
        )}
      </div>

      <p role="status" className="text-sm text-slate-600">
        {remainingMessage(remainingPaise)}
      </p>

      {error !== undefined && (
        <p role="alert" className="text-sm text-red-800">
          {error}
        </p>
      )}
    </fieldset>
  )
}

/** What is left to allocate, said plainly, so the parts can be made to add up. */
function remainingMessage(remainingPaise: number | null): string {
  if (remainingPaise === null) {
    return 'Enter the amount above first'
  }
  if (remainingPaise > 0) {
    return `${formatPaise(remainingPaise)} still to allocate`
  }
  if (remainingPaise < 0) {
    return `${formatPaise(-remainingPaise)} too much`
  }
  return 'The parts add up'
}
