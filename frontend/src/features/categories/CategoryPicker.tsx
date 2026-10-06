import SelectField from '../../components/SelectField'
import type { Category, CategoryKind } from './api'
import { categoryLabel, pickable } from './tree'

interface CategoryPickerProps {
  /** The field's own id, so several pickers can stand on one screen. */
  id: string
  /** What the field is called where it stands. */
  label: string
  /** The tree to offer names from, as the page already has it. */
  categories: Category[]
  /** Which kind of name may be chosen: spending names for money spent. */
  kind: CategoryKind
  /** The chosen name as text, or empty text for none, because a select holds text. */
  value: string
  error?: string
  onChange: (value: string) => void
}

/**
 * The names a movement may be filed under, or none at all.
 *
 * Filing is optional, so the first choice is "No category". A name under a branch
 * is offered as `Branch · Name`, and the write-off names are never offered: they
 * belong to a balance check, and the server refuses one chosen by hand.
 */
export default function CategoryPicker({
  id,
  label,
  categories,
  kind,
  value,
  error,
  onChange,
}: CategoryPickerProps) {
  const offered = pickable(categories, kind)

  return (
    <SelectField
      label={label}
      id={id}
      value={value}
      options={['', ...offered.map((row) => String(row.id))]}
      labels={{
        '': 'No category',
        ...Object.fromEntries(
          offered.map((row) => [String(row.id), categoryLabel(categories, row.id) ?? row.name]),
        ),
      }}
      error={error}
      onChange={onChange}
    />
  )
}
