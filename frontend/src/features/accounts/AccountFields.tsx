import type { Account } from './api'
import Field, { INPUT_CLASS } from '../../components/Field'
import SelectField from '../../components/SelectField'
import TextField from '../../components/TextField'
import {
  ACCOUNT_TYPES,
  ACCOUNT_TYPE_LABELS,
  CAPTURE_MODES,
  CAPTURE_MODE_LABELS,
  type AccountFormErrors,
  type AccountFormValues,
} from './form'

interface AccountFieldsProps {
  values: AccountFormValues
  errors: AccountFormErrors
  /** Accounts a pot may hang from. The caller passes only non-pots. */
  parents: Account[]
  /** False when editing: a type cannot change once the account exists. */
  isTypeEditable: boolean
  onChange: <K extends keyof AccountFormValues>(field: K, value: AccountFormValues[K]) => void
}

/** The fields the add and edit forms share, so the two cannot drift apart. */
export default function AccountFields({
  values,
  errors,
  parents,
  isTypeEditable,
  onChange,
}: AccountFieldsProps) {
  const isCard = values.type === 'credit_card'
  const isPot = values.type === 'pot'
  const parentOptions = ['', ...parents.map((account) => String(account.id))]
  const parentLabels = {
    '': 'Choose an account',
    ...Object.fromEntries(parents.map((account) => [String(account.id), account.name])),
  }

  return (
    <>
      <TextField
        label="Name"
        id="account-name"
        value={values.name}
        error={errors.name}
        onChange={(value) => onChange('name', value)}
      />

      <Field label="Alias (optional)" htmlFor="account-alias" error={errors.alias}>
        <input
          id="account-alias"
          value={values.alias}
          onChange={(event) => onChange('alias', event.target.value)}
          aria-invalid={errors.alias !== undefined}
          aria-describedby={errors.alias !== undefined ? 'account-alias-error' : undefined}
          className={INPUT_CLASS}
        />
        <p className="text-sm text-slate-500">
          A short word you can type instead of the name, like hdfc. One word means one account.
        </p>
      </Field>

      {isTypeEditable ? (
        <SelectField
          label="Type"
          id="account-type"
          value={values.type}
          options={ACCOUNT_TYPES}
          labels={ACCOUNT_TYPE_LABELS}
          onChange={(value) => onChange('type', value)}
        />
      ) : (
        <Field label="Type" htmlFor="account-type">
          <input
            id="account-type"
            value={ACCOUNT_TYPE_LABELS[values.type]}
            readOnly
            className={`${INPUT_CLASS} bg-slate-100 text-slate-600`}
          />
          <p className="text-sm text-slate-500">A type cannot change once the account exists.</p>
        </Field>
      )}

      <SelectField
        label="Capture mode"
        id="account-capture_mode"
        value={values.capture_mode}
        options={CAPTURE_MODES}
        labels={CAPTURE_MODE_LABELS}
        onChange={(value) => onChange('capture_mode', value)}
      />
      <TextField
        label="Purpose (optional)"
        id="account-purpose"
        value={values.purpose}
        error={errors.purpose}
        onChange={(value) => onChange('purpose', value)}
      />

      {isPot && (
        <SelectField
          label="Parent account"
          id="account-parent_id"
          value={values.parent_id}
          options={parentOptions}
          labels={parentLabels}
          error={errors.parent_id}
          onChange={(value) => onChange('parent_id', value)}
        />
      )}

      <TextField
        label="Opening balance"
        id="account-opening_balance"
        value={values.opening_balance}
        error={errors.opening_balance}
        inputMode="decimal"
        onChange={(value) => onChange('opening_balance', value)}
      />
      <TextField
        label="Opening date"
        id="account-opening_date"
        value={values.opening_date}
        error={errors.opening_date}
        type="date"
        onChange={(value) => onChange('opening_date', value)}
      />

      {isCard && (
        <>
          <TextField
            label="Statement day"
            id="account-statement_day"
            value={values.statement_day}
            error={errors.statement_day}
            inputMode="numeric"
            onChange={(value) => onChange('statement_day', value)}
          />
          <TextField
            label="Due day"
            id="account-due_day"
            value={values.due_day}
            error={errors.due_day}
            inputMode="numeric"
            onChange={(value) => onChange('due_day', value)}
          />
        </>
      )}
    </>
  )
}
