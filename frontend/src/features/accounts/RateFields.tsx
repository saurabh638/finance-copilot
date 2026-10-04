import type { RateFrequency } from './api'
import SelectField from './SelectField'
import TextField from './TextField'
import { RATE_FREQUENCIES, RATE_FREQUENCY_LABELS } from './form'

interface RateFieldsProps {
  rate: string
  frequency: RateFrequency
  error?: string
  onRateChange: (rate: string) => void
  onFrequencyChange: (frequency: RateFrequency) => void
}

/**
 * The optional first rate: per cent a year, and how often it is credited.
 *
 * The frequency only means something once there is a rate, so it appears with
 * one rather than asking a question the user has no answer for yet.
 */
export default function RateFields({
  rate,
  frequency,
  error,
  onRateChange,
  onFrequencyChange,
}: RateFieldsProps) {
  return (
    <>
      <TextField
        label="Interest rate % a year"
        id="account-rate"
        value={rate}
        error={error}
        inputMode="decimal"
        onChange={onRateChange}
      />

      {rate.trim() !== '' && (
        <SelectField
          label="Interest credited"
          id="account-frequency"
          value={frequency}
          options={RATE_FREQUENCIES}
          labels={RATE_FREQUENCY_LABELS}
          onChange={onFrequencyChange}
        />
      )}
    </>
  )
}
