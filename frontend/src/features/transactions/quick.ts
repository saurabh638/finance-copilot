/**
 * Reading a typed line into the movement form.
 *
 * `450 dinner swiggy hdfc` becomes the amount, the merchant, the note and the
 * account — as *values*, never as a recording: the screen still shows the form
 * and the user still presses Record it. Nothing here talks to the server.
 *
 * The rules are the approved ones, and they are deliberately plain: one pass
 * left to right, words matched as the longest run that names something, and a
 * question wherever a word could mean two things. A guess would be silently
 * wrong; a question is one tap.
 *
 * Money is read by `lib/money`, the same parser the form uses, so the amount in
 * the preview is exactly the amount that goes over the wire.
 */

import { formatPaise, parsePaise } from '../../lib/money'
import type { Account } from '../accounts/api'
import type { Category, CategoryKind } from '../categories/api'
import { categoryLabel } from '../categories/tree'
import type { Suggestion } from './api'
import { blankMovement, type MovementFormValues, type MovementKind } from './form'

/** Everything the parser is allowed to know: what the screen already has. */
export interface QuickWorld {
  accounts: Account[]
  categories: Category[]
  /** The names the history remembers, as the chips show them. */
  merchants: Suggestion[]
  /** Today, as `YYYY-MM-DD`. */
  today: string
}

/** One answer to a question: what it reads as, and what it would fill in. */
export interface QuickChoice {
  label: string
  values: Partial<MovementFormValues>
}

/** One thing the line did not settle, and the answers that would settle it. */
export interface QuickQuestion {
  field: keyof MovementFormValues
  prompt: string
  choices: QuickChoice[]
}

export interface QuickReading {
  /** The form's values, complete: the screen can hand these straight over. */
  values: MovementFormValues
  questions: QuickQuestion[]
  /** What the line did not do, and why, in the words of the person typing. */
  notices: string[]
  /** Set when the line cannot be recorded at all, as the screen must say. */
  problem: string | null
}

/** Take one of a question's answers, leaving everything else as it was. */
export function applyChoice(values: MovementFormValues, choice: QuickChoice): MovementFormValues {
  return { ...values, ...choice.values }
}

const SPENDING_WORDS = new Set(['spent', 'paid', 'bought'])
const EARNING_WORDS = new Set(['received', 'got'])
const TRANSFER_WORDS = new Set(['transfer', 'transferred', 'moved', 'move'])
/** The little words a transfer is built from, which are never a note. */
const JOINING_WORDS = new Set(['from', 'to', 'into'])

/** The server's own limits, so the preview never shows what the form refuses. */
const MERCHANT_MAX = 120
const NOTE_MAX = 500

const KIND_WORDS: Record<CategoryKind, string> = {
  expense: 'money spent',
  income: 'money received',
  adjustment: 'a balance check',
}

interface Candidate {
  kind: 'account' | 'category'
  id: number
  /** What the screen calls it: the account's name, or `Branch · Child`. */
  label: string
  /** A category's own kind, which can decide the direction on its own. */
  categoryKind: CategoryKind | null
}

interface Span {
  start: number
  length: number
  candidates: Candidate[]
}

/** A day before the one given, read in UTC so no time zone can move it. */
function dayBefore(day: string): string {
  const at = new Date(`${day}T00:00:00Z`)
  at.setUTCDate(at.getUTCDate() - 1)
  return at.toISOString().slice(0, 10)
}

/** The date a word carries, or null. `05/10` is deliberately not one. */
function dateIn(word: string, today: string): string | null {
  const lower = word.toLowerCase()
  if (lower === 'today') {
    return today
  }
  if (lower === 'yesterday') {
    return dayBefore(today)
  }
  return /^\d{4}-\d{2}-\d{2}$/.test(word) ? word : null
}

/** The amount a word carries, or null. `450/-` is the shorthand for ₹450. */
function amountIn(word: string): { text: string; paise: number } | null {
  const text = word.replace(/\/-$/, '')
  try {
    return { text, paise: parsePaise(text) }
  } catch {
    return null
  }
}

/**
 * Every word that names something, and what it names.
 *
 * A child answers to its own name and to the branch's words in front of it,
 * because `Home · Rent` is how the screen writes it and `home rent` is how it is
 * typed.
 */
function nameTable(world: QuickWorld): Map<string, Candidate[]> {
  const table = new Map<string, Candidate[]>()

  function add(phrase: string, candidate: Candidate): void {
    const key = phrase.trim().toLowerCase().replace(/\s+/g, ' ')
    if (key === '') {
      return
    }
    table.set(key, [...(table.get(key) ?? []), candidate])
  }

  for (const account of world.accounts) {
    const candidate: Candidate = {
      kind: 'account',
      id: account.id,
      label: account.name,
      categoryKind: null,
    }
    add(account.name, candidate)
    if (account.alias !== null) {
      add(account.alias, candidate)
    }
  }

  const byId = new Map(world.categories.map((category) => [category.id, category]))
  for (const category of world.categories) {
    const candidate: Candidate = {
      kind: 'category',
      id: category.id,
      label: categoryLabel(world.categories, category.id) ?? category.name,
      categoryKind: category.kind,
    }
    add(category.name, candidate)
    const parent = category.parent_id === null ? undefined : byId.get(category.parent_id)
    if (parent !== undefined) {
      add(`${parent.name} ${category.name}`, candidate)
    }
  }
  return table
}

/** The longest run at each position that names something, left to right. */
function spans(words: string[], table: Map<string, Candidate[]>): Span[] {
  const longest = Math.max(...[...table.keys()].map((phrase) => phrase.split(' ').length), 1)
  const found: Span[] = []
  let at = 0

  while (at < words.length) {
    let matched: Span | null = null
    const furthest = Math.min(longest, words.length - at)
    for (let length = furthest; length >= 1; length -= 1) {
      const phrase = words
        .slice(at, at + length)
        .map((word) => word.toLowerCase())
        .join(' ')
      const candidates = table.get(phrase)
      if (candidates !== undefined) {
        matched = { start: at, length, candidates }
        break
      }
    }
    if (matched === null) {
      at += 1
    } else {
      found.push(matched)
      at += matched.length
    }
  }
  return found
}

function withKind(found: Span[], kind: 'account' | 'category'): { span: Span; at: Candidate }[] {
  return found.flatMap((span) =>
    span.candidates
      .filter((candidate) => candidate.kind === kind)
      .map((candidate) => ({ span, at: candidate })),
  )
}

/** The runs where a name the history knows appears, overlaps and all. */
function knownMerchantSpans(
  words: string[],
  customers: Suggestion[],
): { start: number; length: number; name: string }[] {
  const lower = words.map((word) => word.toLowerCase())
  const found: { start: number; length: number; name: string }[] = []
  for (const suggestion of customers) {
    const phrase = suggestion.merchant.trim().toLowerCase().split(/\s+/)
    for (let at = 0; at + phrase.length <= lower.length; at += 1) {
      const run = lower.slice(at, at + phrase.length)
      if (run.every((word, offset) => word === phrase[offset])) {
        found.push({ start: at, length: phrase.length, name: suggestion.merchant })
      }
    }
  }
  return found.sort((left, right) => left.start - right.start || right.length - left.length)
}

/** Text cut to what the form accepts, with a notice when anything was lost. */
function cut(text: string, most: number, notices: string[]): string {
  if (text.length <= most) {
    return text
  }
  notices.push(
    `The ${most === MERCHANT_MAX ? 'merchant' : 'note'} was shortened to ${most} characters`,
  )
  return text.slice(0, most)
}

function wordsOutside(words: string[], start: number, length: number): string {
  return [...words.slice(0, start), ...words.slice(start + length)].join(' ')
}

function accountsExcept(
  world: QuickWorld,
  excluded: Candidate | null,
  field: string,
): QuickChoice[] {
  return world.accounts
    .filter((account) => account.id !== excluded?.id)
    .map((account) => ({ label: account.name, values: { [field]: String(account.id) } }))
}

/**
 * Read one line. Ambiguity becomes a question; nothing is ever decided twice.
 */
export function readQuickLine(line: string, world: QuickWorld): QuickReading {
  const notices: string[] = []
  const words = line
    .trim()
    .split(/\s+/)
    .filter((word) => word !== '')

  // The first word that reads as money and is more than nothing is the amount.
  // A zero is dropped: it was never an amount, so it is not a merchant's word
  // either, while a later `500` stays in the text and is reported instead.
  const dropped = new Set<number>()
  let amount = ''
  let amountAt = -1
  for (let at = 0; at < words.length; at += 1) {
    const money = amountIn(words[at] as string)
    if (money === null) {
      continue
    }
    if (money.paise > 0) {
      amount = money.text
      amountAt = at
      break
    }
    notices.push(`${words[at]} is not an amount, so it was left out`)
    dropped.add(at)
  }

  // The date: today, yesterday, or an ISO date. Nothing else is guessed at.
  let date = world.today
  let dateAt = -1
  for (let at = 0; at < words.length; at += 1) {
    if (at === amountAt) {
      continue
    }
    const read = dateIn(words[at] as string, world.today)
    if (read !== null) {
      date = read
      dateAt = at
      break
    }
  }

  // The direction, when it is said outright.
  let saidOutLoud: 'expense' | 'income' | null = null
  let directionAt = -1
  for (let at = 0; at < words.length; at += 1) {
    if (at === amountAt || at === dateAt) {
      continue
    }
    const lower = (words[at] as string).toLowerCase()
    if (SPENDING_WORDS.has(lower) || EARNING_WORDS.has(lower)) {
      saidOutLoud = SPENDING_WORDS.has(lower) ? 'expense' : 'income'
      directionAt = at
      break
    }
  }

  const taken = new Set([amountAt, dateAt, directionAt])
  const rest = words
    .map((word, at) => ({ word, at }))
    .filter((entry) => !taken.has(entry.at) && !dropped.has(entry.at))
  const restWords = rest.map((entry) => entry.word)
  const lower = restWords.map((word) => word.toLowerCase())

  for (const word of restWords) {
    if (/^\d{1,2}[/-]\d{1,2}$/.test(word)) {
      notices.push(`${word} was not read as a date; use today, yesterday, or 2026-10-05`)
    }
    const money = amountIn(word)
    if (money !== null && money.paise > 0) {
      notices.push(`${word} was not taken as the amount; only the first one is`)
    }
  }

  const table = nameTable(world)
  const found = spans(restWords, table)
  const accountMatches = withKind(found, 'account')
  const categoryMatches = withKind(found, 'category')

  const toAt = lower.indexOf('to')
  const fromAt = lower.indexOf('from')
  const looksLikeATransfer =
    lower.some((word) => TRANSFER_WORDS.has(word)) ||
    (toAt !== -1 &&
      accountMatches.some((match) => match.span.start < toAt) &&
      accountMatches.some((match) => match.span.start > toAt))

  if (looksLikeATransfer) {
    return readTransfer({
      rest,
      lower,
      accountMatches,
      categoryMatches,
      world,
      notices,
      amount,
      date,
      toAt,
      fromAt,
    })
  }

  const settled = (...groups: { span: Span }[]): Set<number> => {
    const marks = new Set<number>()
    for (const group of groups) {
      for (let offset = 0; offset < group.span.length; offset += 1) {
        marks.add(group.span.start + offset)
      }
    }
    return marks
  }
  const leftoverOf = (marks: Set<number>): string[] => restWords.filter((_, at) => !marks.has(at))
  const phraseOf = (span: Span): string =>
    restWords.slice(span.start, span.start + span.length).join(' ')

  const matchedCategories = categoryMatches.map((match) => match.at)

  // A merchant the history knows means a line of spending at that shop, so an
  // income name in such a line is reported rather than obeyed. Where the line
  // names no merchant at all, an income name is the only thing saying what the
  // money was, and it decides: `salary 50,000 sbi` is money received.
  let direction = saidOutLoud
  if (direction === null) {
    const everyNameSettled = settled(...accountMatches, ...categoryMatches)
    const namedMerchant = knownMerchantSpans(leftoverOf(everyNameSettled), world.merchants)
    const impliesIncome = matchedCategories.find((candidate) => candidate.categoryKind === 'income')
    direction = impliesIncome !== undefined && namedMerchant.length === 0 ? 'income' : 'expense'
    if (direction === 'income') {
      notices.push(
        `Read as money received, because ${(impliesIncome as Candidate).label} is a money-received name`,
      )
    }
  }

  const usable = categoryMatches.filter((match) => match.at.categoryKind === direction)
  for (const match of categoryMatches.filter((each) => each.at.categoryKind !== direction)) {
    notices.push(
      `${match.at.label} is for ${KIND_WORDS[match.at.categoryKind as CategoryKind]}, so it was not used as a category`,
    )
  }

  const questions: QuickQuestion[] = []
  let category_id = ''
  if (usable.length > 1) {
    questions.push({
      field: 'category_id',
      prompt: 'Which one is this filed under?',
      choices: usable.map((match) => ({
        label: `File it under ${match.at.label}`,
        values: { category_id: String(match.at.id) },
      })),
    })
  } else if (usable.length === 1) {
    category_id = String((usable[0] as { at: Candidate }).at.id)
  }

  // The accounts: one is the account, two or more is a question. Either way
  // their words are settled and never become the merchant.
  const accountIds = [...new Set(accountMatches.map((match) => match.at.id))]
  let account_id = ''
  if (accountIds.length === 1) {
    account_id = String(accountIds[0])
  } else if (accountIds.length > 1) {
    questions.push({
      field: 'account_id',
      prompt: 'Which account was this out of?',
      choices: accountMatches.map((match) => ({
        label: match.at.label,
        values: { account_id: String(match.at.id) },
      })),
    })
  }

  // A name the tree does not hold is the user's own word again, so a name of the
  // wrong kind goes back into the text rather than disappearing from it.
  const leftover = leftoverOf(settled(...accountMatches, ...usable))

  const merchantSpans = knownMerchantSpans(leftover, world.merchants)
  let merchant = ''
  let note = ''
  if (merchantSpans.length === 1) {
    const only = merchantSpans[0] as { start: number; length: number; name: string }
    merchant = only.name
    note = wordsOutside(leftover, only.start, only.length)
  } else if (merchantSpans.length === 0) {
    merchant = leftover.join(' ')
  }

  // A word that is both a name in the tree and a name in the history is the one
  // thing the rules cannot settle: filing it and naming it are both right.
  const bothAtOnce =
    usable.length === 1 &&
    world.merchants.some(
      (suggestion) =>
        suggestion.merchant.trim().toLowerCase() ===
        phraseOf((usable[0] as { span: Span }).span).toLowerCase(),
    )

  if (merchantSpans.length > 1) {
    merchant = ''
    note = ''
    questions.push({
      field: 'merchant',
      prompt: 'Which one is the merchant?',
      choices: merchantSpans.map((span) => ({
        label: span.name,
        values: { merchant: span.name, note: wordsOutside(leftover, span.start, span.length) },
      })),
    })
  } else if (bothAtOnce && questions.length === 0) {
    const phrase = phraseOf((usable[0] as { span: Span }).span)
    const filing = category_id
    category_id = ''
    merchant = ''
    note = ''
    questions.push({
      field: 'category_id',
      prompt: `Is ${phrase} what this was, or where it is filed?`,
      choices: [
        {
          label: `File it under ${categoryLabel(world.categories, Number(filing))}`,
          values: { category_id: filing },
        },
        { label: `Use ${phrase} as the merchant`, values: { merchant: phrase } },
      ],
    })
  }

  return {
    values: {
      ...blankMovement(world.today),
      kind: direction,
      amount,
      transaction_date: date,
      account_id,
      category_id,
      merchant: cut(merchant.trim(), MERCHANT_MAX, notices),
      note: cut(note.trim(), NOTE_MAX, notices),
    },
    questions,
    notices,
    problem: null,
  }
}

interface TransferParts {
  rest: { word: string; at: number }[]
  lower: string[]
  accountMatches: { span: Span; at: Candidate }[]
  categoryMatches: { span: Span; at: Candidate }[]
  world: QuickWorld
  notices: string[]
  amount: string
  date: string
  toAt: number
  fromAt: number
}

/**
 * A transfer: two accounts and the little words between them.
 *
 * The wording is the same shape as a line of money — amount, then who from, then
 * who to — and whatever is left over is the note, because a transfer has no
 * merchant. Money that only moves is never filed under a category.
 */
function readTransfer(parts: TransferParts): QuickReading {
  const { rest, accountMatches, categoryMatches, world, notices, amount, date } = parts

  if (categoryMatches.length > 0) {
    notices.push('A transfer is not filed under a category, so that word was left as the note')
  }

  const before = (at: number): Candidate | null => {
    const ending = accountMatches.filter((match) => match.span.start + match.span.length <= at)
    return ending.length === 0 ? null : (ending[ending.length - 1] as { at: Candidate }).at
  }
  const after = (at: number): Candidate | null => {
    const starting = accountMatches.filter((match) => match.span.start > at)
    return starting.length === 0 ? null : (starting[0] as { at: Candidate }).at
  }

  let source: Candidate | null = null
  let destination: Candidate | null = null
  if (parts.toAt !== -1) {
    source = before(parts.toAt)
    destination = after(parts.toAt)
  }
  if (parts.fromAt !== -1 && source === null) {
    source = after(parts.fromAt)
  }
  if (parts.toAt === -1 && parts.fromAt === -1) {
    // No word to say which is which, so they are read in the order they appear.
    source = accountMatches[0]?.at ?? null
    destination = accountMatches[1]?.at ?? null
  }

  const settled = new Set<number>()
  for (const match of accountMatches) {
    for (let offset = 0; offset < match.span.length; offset += 1) {
      settled.add(match.span.start + offset)
    }
  }
  const leftover = rest
    .filter((_, at) => !settled.has(at))
    .map((entry) => entry.word)
    .filter((word) => {
      const lower = word.toLowerCase()
      return !TRANSFER_WORDS.has(lower) && !JOINING_WORDS.has(lower)
    })

  if (source !== null && destination !== null && source.id === destination.id) {
    return {
      values: {
        ...blankMovement(world.today),
        kind: 'transfer',
        amount,
        transaction_date: date,
        from_account_id: String(source.id),
        to_account_id: String(destination.id),
      },
      questions: [],
      notices,
      problem: 'A transfer needs two different accounts',
    }
  }

  const questions: QuickQuestion[] = []
  if (source === null) {
    questions.push({
      field: 'from_account_id',
      prompt: 'Which account did the money come from?',
      choices: accountsExcept(world, destination, 'from_account_id'),
    })
  }
  if (destination === null) {
    questions.push({
      field: 'to_account_id',
      prompt: 'Which account did the money go to?',
      choices: accountsExcept(world, source, 'to_account_id'),
    })
  }

  return {
    values: {
      ...blankMovement(world.today),
      kind: 'transfer',
      amount,
      transaction_date: date,
      from_account_id: source === null ? '' : String(source.id),
      to_account_id: destination === null ? '' : String(destination.id),
      note: cut(leftover.join(' ').trim(), NOTE_MAX, notices),
    },
    questions,
    notices,
    problem: null,
  }
}

/**
 * Apply the answers already given, and drop the questions they settle.
 *
 * The screen keeps a choice by the field it fills, so a line that is typed again
 * after an answer keeps that answer rather than asking a second time.
 */
export function withAnswers(
  reading: QuickReading,
  answers: Record<string, QuickChoice>,
): QuickReading {
  let values = reading.values
  const open: QuickQuestion[] = []
  for (const question of reading.questions) {
    const answer = answers[question.field]
    if (answer === undefined) {
      open.push(question)
    } else {
      values = applyChoice(values, answer)
    }
  }
  return { ...reading, values, questions: open }
}

/**
 * What the line understood, in the words the form uses.
 *
 * The preview is the point of the whole screen: a reading that cannot be seen is
 * a reading that cannot be trusted, so every part the line decided is named.
 */
export function quickSummary(reading: QuickReading, world: QuickWorld): string[] {
  const { values } = reading
  const lines: string[] = []

  if (values.amount.trim() !== '') {
    lines.push(formatPaise(parsePaise(values.amount)))
  }

  const kindWords: Record<MovementKind, string> = {
    expense: 'Money spent',
    income: 'Money received',
    transfer: 'Transfer between accounts',
  }
  lines.push(kindWords[values.kind])

  const nameOf = (id: string): string =>
    world.accounts.find((account) => String(account.id) === id)?.name ?? ''
  if (values.kind === 'transfer') {
    const from = nameOf(values.from_account_id)
    const to = nameOf(values.to_account_id)
    if (from !== '' && to !== '') {
      lines.push(`From ${from} to ${to}`)
    } else if (from !== '') {
      lines.push(`From ${from}`)
    } else if (to !== '') {
      lines.push(`To ${to}`)
    }
  } else if (values.account_id !== '') {
    lines.push(`Out of ${nameOf(values.account_id)}`)
  }

  const filed = categoryLabel(
    world.categories,
    values.category_id === '' ? null : Number(values.category_id),
  )
  if (filed !== null) {
    lines.push(`Filed under ${filed}`)
  }

  if (values.merchant.trim() !== '') {
    lines.push(`Merchant ${values.merchant.trim()}`)
  }
  if (values.note.trim() !== '') {
    lines.push(`Note ${values.note.trim()}`)
  }
  if (values.transaction_date !== world.today) {
    lines.push(`Dated ${values.transaction_date}`)
  }
  return lines
}
