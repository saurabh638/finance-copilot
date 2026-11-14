# DECISIONS

The rules still in force, one line each: what a new change must not break. Order follows the original log.

The full dated log — every entry's original reasoning, and the decisions that no longer constrain anything
(the platform and process choices, how a milestone was implemented, bugs the walkthroughs found, and the
ones later milestones superseded) — is `DECISIONS_ARCHIVE.md`. Read that one when changing something these
rules touch, not every session. Nothing has been deleted: every entry that was ever here is in one file or
the other.

## Money

- Money is integer paise everywhere; no floats. — Rounding drift is unrecoverable trust damage.
- More than two decimal places is rejected, never rounded. — A silently rounded amount is a wrong number the user would never see.
- Parsing accepts Indian and Western digit grouping and rejects malformed grouping. — Real inputs vary; broken grouping almost always means a typo worth failing on.
- A split gives the remainder paise to the first parts. — Deterministic, and the parts always sum back to the total with no paise lost or created.
- The browser parses and formats money with `lib/money.ts`, mirroring `core/money.parse_paise` case for case, and never does money arithmetic of its own. — One reading of money, not two; every sum happens on the server, where it is tested.
- `parsePaise` refuses an amount above `Number.MAX_SAFE_INTEGER`. — JavaScript cannot hold such a number exactly, and a silently wrong balance is worse than a refusal.

## Ledger

- Balances are derived from postings, never stored. — Stored running totals drift.
- A posting's amount is the signed change to its account's balance, and `kind` is what analytics reads. — A card's outstanding is then simply a negative balance, and one convention everything downstream can rely on.
- Only the transaction carries a date; a posting is dated by its transaction. — One date per movement, so a posting can never disagree with the transaction it belongs to.
- An expense or income is one posting; a transfer is two that sum to zero. — The other side of an external flow is the world outside the app, and an internal movement that does not sum to zero would create or destroy money.
- Amounts are given as positive numbers and the kind sets the direction, on create and on edit alike. — A hand-typed sign is a sign that can be typed wrongly; `-500` cannot turn an expense into an income one PATCH at a time.
- A movement has no `kind` of its own in the response; its postings and their kinds are the answer. — A top-level kind would be a second answer, free to disagree with the postings it summarises.
- A posting dated before the account opened is refused when written and ignored by the ledger. — Fail loudly on new data, yet stay correct for anything already stored, with one rule at create and at edit.
- Recording is one `POST /transactions` whose body is a discriminated union on `kind`. — One URL stays honest, and a malformed transfer is refused before any code runs.
- `transaction_date` is required and is never defaulted to today by the server. — The date of a movement is the one the user states; a server "today" is a bug that only appears near midnight.
- `PATCH` distinguishes an omitted field from an explicit `null`. — Absent means "leave it alone"; `null` is the only way to clear a note or a filing.
- An amount can only be changed when the movement has exactly one posting. — Two sides that must sum to zero cannot be rewritten from one amount without guessing which side moved.
- A malformed request is 400, a name that is not there is 404, and a clash with existing state is 409. — 400 would blame the request for something the data decided.
- Ownership is resolved through the account, and each route family hangs off it. — One rule, and no second path to another user's data.
- `?from=` and `?to=` are aliased parameters and both ends are inclusive. — `from` is a Python keyword, and a range typed as the 1st to the 31st should include both of those days.
- Account `type` and `capture_mode` are VARCHAR plus a CHECK, not Postgres enums, and a `type` cannot change after creation. — A new kind is an ordinary migration rather than an `ALTER TYPE` applied in lockstep, and postings, card rules and importers key off the type.
- A pot needs exactly one live, non-pot parent, enforced in the database and in the service. — The invariant is what makes pots and sub-balances work with no special cases.
- Service functions raise domain errors; only routers map them to HTTP statuses. — HTTP stays out of the logic layer, with one place per status code.
- A write-off is the signed difference, posted as an `adjustment`, so the computed balance plus the write-off lands on the stated balance exactly. — A reconciliation that leaves a paise behind is worse than none, and the request has to say it means to write off.
- A balance check is two deliberate steps, uses the figures it recorded, and is recorded whether or not it is written off. — One call cannot both inform and act, and the user decided on the numbers they were shown.
- The size warning is advice, never a refusal: a flat paise threshold with the month's share shown beside it. — SPEC.md says a large write-off is questioned, not blocked, and two figures disagreeing about one decision would be worse than one honest figure.
- "Adjustments as a share of spending" counts `expense` postings only, as a whole percent. — A transfer moves money without spending it, and an adjustment is the opposite of spending.
- A movement is filed under one category, carried by its posting, and a name whose kind does not match the movement is refused with 400 naming both kinds. — The posting's kind decided which categories were eligible, and it is the payload that is wrong, not the tree.
- A write-off files itself under `Unaccounted for spending` or `Unrecorded income` by its sign, and goes unfiled rather than failing if that name is gone. — The sign already says which it is, and losing a filing is recoverable where refusing a reconciliation is not.
- The tree is two levels and no deeper, and a child carries its parent's kind, which is never edited directly. — A name has to mean one thing everywhere.
- The default set is seeded once into an empty tree and never refilled, a name in use cannot be removed, and its unique index is partial with `NULLS NOT DISTINCT`. — Re-seeding would resurrect what was removed, and a removal would leave money with no name.
- The two write-off names live in the tree with kind `adjustment`. — A write-off needs a home that is neither spending nor income, which spend totals must exclude.
- A split states the total plus its parts, which must add up to it exactly, in two parts or more, all on one account. — The total is the statement's figure and the parts are a reading of it; splitting across accounts would count the money twice.
- `is_balanced` accepts a third shape: two or more postings of a single sign. — A split is one flow counted once, twice over, and the zero-sum rule is untouched, so a transfer cannot be mistaken for one.
- A category cannot be changed on a movement with more than one posting. — A split's parts are the filing, and a transfer's two sides are one movement.
- The spend report covers `expense` postings, filters in SQL and sums in Python. — Money stays out of the database's arithmetic, exactly as the balance does.
- It rolls a child into its branch, gives every expense category a row with zeros included, and returns the unfiled money and the period's whole with them. — Rows that could not add up to the whole would be the thing clients were written against.
- A catch-up lump is spending with no category, not an adjustment. — The money did leave the account, so it belongs in the month's spending, unfiled rather than excluded from every figure.
- A recurring item is a plan, and confirming one writes an ordinary transaction. — Storing a plan's figure as if it were spent would be the stored-balance mistake in another costume.
- Only spending and earning can repeat. — A transfer between the user's own accounts is not a bill, and a write-off is not something that happens every month.
- A period is dealt with only while the movement that recorded it is alive, and a skip stands for good. — A confirmation outliving its movement would let money vanish from the ledger while the item stayed settled.
- A confirmed period is dated the day it was owed, not the day it was confirmed. — That is when the money moved.
- A day beyond the month's length uses the month's last day, and one row per period is held by a unique index. — The 31st is what was agreed with the landlord, and "already dealt with" is an invariant, not something a screen remembers.
- The rhythm rule is stated twice: in the service, in words, and in the database with explicit `IS NOT NULL` halves. — A CHECK passes on null, so a rule written as "monthly implies a day" would have let a monthly item with no day through.
- Editing an item changes the plan and never the money it has already recorded, and a different amount confirms one period without rewriting the plan. — Rewriting last month because a form was open would be editing history, and one odd month is not a new agreement.

## Auth

- Passwords are hashed with Argon2 (argon2-cffi), never stored or logged in clear.
- Sessions live in Postgres, the token is stored only as a SHA-256 hash, and it travels in an HttpOnly cookie. — A stolen database dump must not be replayable as a login, and sessions have to be revocable.
- One app-level auth guard with an allowlist, not per-route dependencies. — A router added later is protected by default and cannot be exposed by forgetting a dependency.
- `create-user` reads credentials from the environment, never from CLI arguments. — Passwords passed as arguments appear in shell history and the process list.
- Login rate limiting lives in Postgres (`login_failures`), not in memory. — It survives restarts and extra workers, and global mutable state is forbidden.

## Screens

- Server state lives in TanStack Query; React keeps no copy of it. — One cache, no duplicated server state.
- There is still no router: the app swaps screens on state. — Two screens with no deep-link need do not justify a dependency; it should arrive with the first screen where a URL means something.
- Form rules live in pure modules (`form.ts`, `edit.ts`, `balanceCheck.ts`), and the component only renders and submits. — The rules are the part worth testing without a browser, and every figure shown comes from the API.
- `todayIso()` builds the day from local date parts, never from `toISOString()`. — A movement recorded early in the morning in India would otherwise be dated the previous day.
- A field the server will not change is shown read-only with the reason beside it, never hidden. — Hiding it reads as missing data; saying why teaches the rule the API enforces.
- Anything that rewrites money asks first, in place: a rate, a movement, a category, a proposal. — A soft delete is quiet, and a mis-tap must not rewrite what a balance says.
- A refusal is reported next to the values it refused, on the row it belongs to. — A page-level alert reads as a problem with the whole screen.
- A screen never offers what the server will refuse. — Offering a write-off name in the picker would be worse than not offering the filing at all.
- Today opens the app, the recording form starts closed, and today's list is read-only and says where a movement is corrected. — The daily action is the screen to land on, and one screen owns corrections.
- Every number comes with its parts: opening plus movements under the balance, and interest as "of which interest" rather than beside them. — A figure without its parts cannot be checked, and interest added beside them would count twice.
- Everything derived from movements is dropped when a movement changes, through one exported list of keys. — One path that refetches a little too much cannot be wrong about what it forgot.
- A transfer is shown as both accounts with the amount moved and no sign. — Spending must never be mistakable for income, and a transfer is neither.
- The run of days counts a run that ended yesterday as alive, and says nothing scolding. — The day is not over, and a product that tells someone their run broke at 9am is one they stop opening.
- Repeats is the fifth tab, and the last one that fits a tab bar. — A tab costs nothing to find; the next screen needs a different shape.
- A repeating bill is confirmed with one tap, and everything unusual sits one step in. — The common action is one large target on the screen that has to stay under two minutes.

## Interest

- Interest is actual days over a fixed 365, including 29 February, with the divisor never moving. — A day count is a policy, not a fact; one constant means a bank's different convention shows as the gap between the proposed and credited figures.
- Accrual is exact rational arithmetic, rounded once at the end, half away from zero. — Rounding each day would leak a paise a day and make the total depend on how the days were grouped.
- Crediting periods are calendar periods, and the first one is clipped to the day the rate started rather than skipped. — The bank's periods are the calendar's, a rate arriving on the 15th still earns for the rest of the month, and no day lands in two periods.
- One proposal per run of days under one rate: a rate change splits it, money moving does not. — A bank credits one figure for a month, and a rate change is a different agreement.
- Only a positive balance accrues. — An overdrawn account earning "negative interest" would be inventing a bank's behaviour.
- A proposal is a snapshot of a finished period, and a credit already posted compounds into the next one. — Proposals must stay stable enough to hold against a bank statement.
- Both figures are kept: what the ledger worked out and what the bank paid. — Overwriting one with the other would hide the only place the stated conventions can be seen to be wrong.
- A proposal can be thrown away after asking first; a credited period is undone only by removing its movement. — A proposal is arithmetic nobody has acted on, where a credit is money on the ledger, corrected where every other movement is.
- Rates are dated rows, never updated in place: a correction is a soft delete plus a re-add, with one live rate per `(account, from_date)`. — A rate change is recorded, never overwritten, and a soft-deleted mistake must not block the corrected one.
- `rate` is NUMERIC(7, 4), a Decimal end to end, serialised as a JSON string, and more than four decimals is rejected rather than rounded. — A rate must not drift through a float.
- A stored rate is trimmed as text for the words, never turned into a number. — Passing it through a number to tidy it would put a float on the path of a rate the ledger multiplies by.
- A yearly rate is refused with the reason rather than proposing nothing quietly. — Silence would look like "no interest due" and be wrong.
- The timer runs in the backend process, gated by `SCHEDULER_ENABLED`, and its body is the function the CLI calls. — The job that runs at one in the morning has to be the same thing that can be run by hand.
- Interest is a third panel on the account row, opened by its own toggle, one panel at a time. — The account's own money operations live on the account.
- The panel spells out the difference between the two figures, and says nothing when they agree. — Agreement needs no words; a difference is the only place the convention can be seen to be wrong.
- An empty bank figure means the ledger's own; a typed one must be readable and more than nothing. — Typing the figure is the exception, so the common case is one tap.

## Quick entry

- An alias belongs to one account and may not collide with another account's alias or name. — A word that means two accounts turns every typed line into a question.
- The quick line fills the form rather than recording anything itself, and the parser lives in the frontend, outside `core/`. — One payload path and one place to correct a reading; parsing a sentence is not arithmetic.
- The reading is named part by part before anything is recorded. — A reading that cannot be seen cannot be trusted, and even a parser with no AI in it is wrong sometimes.
- `05/10` is refused rather than guessed, and a zero is not an amount. — Day-first and month-first both exist, so half those guesses would be wrong and silent; nothing is not an amount.
- An income name sets the direction only when the line names no merchant the history knows. — A merchant means a line of spending at that shop; with no merchant, the name is all there is to go on.
- The merchant is chosen from the names the history knows and the rest of the words become the note; two known names is a question. — `450 dinner big bazaar` must mean *Big Bazaar* with the note *dinner*, and both readings of two known names are right.
- A transfer is read as two accounts, and whatever is left over is its note. — Money that only moves is not spending, so it can be filed under nothing and has no merchant to name.
- The Today screen carries a note box. — A reading that cannot be corrected where it was read is a promise the screen does not keep.

## Imports

- A statement is read, checked and held before anything is written; committing is a second, deliberate act. — The rows are stored as they were read, so the preview somebody agreed to is the commit, and a file that does not reconcile never reaches the ledger.
- Reconciliation is two answers, not one: the file's own arithmetic, and whether the ledger plus the rows reaches the closing figure. — A perfect file can still mean the ledger is missing movements, and one vague "does not reconcile" would hide which of the two is wrong.
- Only the rows the ledger is missing count towards the closing figure when agreeing with the ledger. — A statement read twice has every row already recorded, and counting them again would refuse a perfectly good file.
- A row's identity is the account, the day the money moved, the amount and the normalised narration; the unique index on it is partial and live-only. — The same payment cannot be recorded twice, while a reversed batch or a removed movement releases exactly its row so the statement can be read again.
- Two rows in one file that cannot be told apart are refused, naming both, rather than merged. — Importing one and dropping the other would be a silent guess about somebody's money.
- A reader declares whether a statement counts money held or money owed, and the import path never knows the difference. — A card statement is the same arithmetic negated, so no per-bank rule leaks into the ledger.
- An imported movement is written through the ordinary recording path with `source = import`, and no merchant is invented from the narration. — It has to be correctable like any other movement, and naming a merchant from a bank's wording is M16's resolver, not a guess at import time.
- Committing writes row by row, and a preview that was never committed can be reversed like a committed one. — A database fault mid-commit must leave a remedy, and putting a preview away is the same action as undoing it.
- The plain reader takes ISO dates and a signed decimal amount, and says which row it failed on. — `01/09/2026` is a bank's convention and belongs to that bank's reader; a strict reader that names the line is more useful than a forgiving one that guesses.
