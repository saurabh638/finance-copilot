import { useMemo, useState } from 'react'

import TextField from '../../components/TextField'
import type { Account } from '../accounts/api'
import type { Category } from '../categories/api'
import type { Suggestion } from '../transactions/api'
import type { MovementFormValues } from '../transactions/form'
import {
  quickSummary,
  readQuickLine,
  withAnswers,
  type QuickChoice,
  type QuickQuestion,
} from '../transactions/quick'

interface QuickEntryProps {
  accounts: Account[]
  categories: Category[]
  /** What the history remembers, which is what turns a word into a merchant. */
  suggestions: Suggestion[]
  today: string
  /** Hand the reading to the form. Nothing is recorded from here. */
  onFill: (values: MovementFormValues) => void
  /** Changes when a movement was recorded, so the line starts again. */
  resetToken: number
}

/**
 * One line of typing, read into the form above it.
 *
 * The reading is shown rather than acted on: whatever was understood is named,
 * whatever was not is said, and anything the line could not settle is a question
 * with a button per answer. Recording is still the form's job.
 */
export default function QuickEntry({
  accounts,
  categories,
  suggestions,
  today,
  onFill,
  resetToken,
}: QuickEntryProps) {
  const [line, setLine] = useState('')
  const [answers, setAnswers] = useState<Record<string, QuickChoice>>({})
  const [seenToken, setSeenToken] = useState(resetToken)

  // A recorded movement starts the line again: the form has been emptied, and
  // leaving the old line behind would read as if it were still about to happen.
  // Adjusting during render, rather than in an effect, is React's own pattern
  // for state that follows a prop — and it clears the line in the same paint.
  if (seenToken !== resetToken) {
    setSeenToken(resetToken)
    setLine('')
    setAnswers({})
  }

  const world = useMemo(
    () => ({ accounts, categories, merchants: suggestions, today }),
    [accounts, categories, suggestions, today],
  )

  const reading = useMemo(
    () => withAnswers(readQuickLine(line, world), answers),
    [line, world, answers],
  )
  const summary = line.trim() === '' ? [] : quickSummary(reading, world)

  function handOver(text: string, next: Record<string, QuickChoice>): void {
    if (text.trim() === '') {
      return
    }
    onFill(withAnswers(readQuickLine(text, world), next).values)
  }

  function change(text: string): void {
    setLine(text)
    handOver(text, answers)
  }

  function answer(question: QuickQuestion, choice: QuickChoice): void {
    const next = { ...answers, [question.field]: choice }
    setAnswers(next)
    handOver(line, next)
  }

  return (
    <div className="mt-4 grid gap-2">
      <TextField
        label="Say it in a line (optional)"
        id="today-quick"
        value={line}
        onChange={change}
      />
      <p className="text-sm text-slate-500">
        {`450 dinner swiggy hdfc — the amount, what it was, and the account. A transfer is 500 sbi to slice.`}
      </p>

      {reading.problem !== null && (
        <p role="alert" className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {reading.problem}
        </p>
      )}

      {summary.length > 0 && (
        <ul
          aria-label="What was understood"
          className="flex flex-wrap gap-x-3 text-sm text-slate-700"
        >
          {summary.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}

      {reading.notices.length > 0 && (
        <ul aria-label="What was not used" className="grid gap-1 text-sm text-amber-800">
          {reading.notices.map((notice) => (
            <li key={notice}>{notice}</li>
          ))}
        </ul>
      )}

      {reading.questions.map((question) => (
        <fieldset key={question.field} className="border-0 p-0">
          <legend className="text-sm font-medium text-slate-700">{question.prompt}</legend>
          <ul className="mt-2 flex flex-wrap gap-2">
            {question.choices.map((choice) => (
              <li key={choice.label}>
                <button
                  type="button"
                  onClick={() => answer(question, choice)}
                  className="min-h-11 rounded-full border border-slate-300 bg-white px-4 text-slate-900"
                >
                  {choice.label}
                </button>
              </li>
            ))}
          </ul>
        </fieldset>
      ))}
    </div>
  )
}
