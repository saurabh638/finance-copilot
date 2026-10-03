# Milestones

Each milestone is small, testable and ends with something the user can run and check. Follow RULES.md section 1 for every one: plan, approval, build with tests, stop, verify, `APPROVED`, then the next.

Format: **Goal / Build / Do not build / Tests / User verifies by.**

---

## PHASE 0: Ledger core and daily capture (usable on its own)

### M1: Project skeleton
- **Goal:** the empty stack runs end to end, with all quality tooling wired up and green, so every later milestone is checked automatically.
- **Build:**
  - `docker-compose.yml` with `db` (postgres:16, named volume, healthcheck), `backend` (FastAPI, source mounted, hot reload) and `frontend` (Vite + React + TypeScript strict + Tailwind). `.env` created from `.env.example` (generate a real `SECRET_KEY`; never commit `.env`).
  - Backend: `config.py` (pydantic-settings), `db.py` (sync SQLAlchemy 2.0 engine and session), `main.py` with `/api/v1/health` that also checks the database. Alembic initialised with an empty baseline migration that runs on a fresh database. `requirements.txt` and `requirements-dev.txt` with pinned versions. `pyproject.toml` configuring ruff, mypy and pytest (with coverage).
  - Frontend: plain page that calls the health endpoint through the Vite dev proxy and shows "Backend OK" or a clear error. ESLint, Prettier, Vitest and Testing Library configured, with npm scripts `lint`, `format:check`, `typecheck`, `test`.
  - A short README section confirming the daily commands work.
- **Do not build:** any feature, auth, models, or styling beyond a plain page. Do not add any library not listed in ARCHITECTURE.md.
- **Tests:** a pytest test for the health endpoint (including the database check) and a Vitest test for the frontend health component.
- **User verifies by:** `docker compose up --build`, open the frontend URL, see "Backend OK"; then run each command in CODING_STANDARDS.md section 2 and see all of them pass.

### M2: Money module
- **Goal:** one trusted place for all rupee handling.
- **Build:** `backend/app/core/money.py`: parse text like `1,23,456.78`, `₹500`, `500` into integer paise; reject floats and garbage; add, subtract, negate; format paise to Indian grouping (`₹1,23,456.78`, lakh and crore style); a helper to split an amount in paise evenly with no loss. Same formatting helper mirrored in `frontend/src/lib/money.ts`.
- **Do not build:** anything touching the database or API.
- **Tests (write first):** parsing cases, formatting cases including crore-level numbers and negatives, zero, rounding rules for splits, rejection of floats.
- **User verifies by:** reading the test file and checking the expected formats look right to them; running the tests.

### M3: Single-user login
- **Goal:** everything behind a login from the start.
- **Build:** `User` model and migration; Argon2 password hashing; session cookie login and logout endpoints; a CLI command to create the one user; auth dependency used by every route except health and login; a simple login page and a protected home page in the frontend.
- **Do not build:** sign-up, password reset, multiple users, roles.
- **Tests:** login success and failure, protected route rejects anonymous, password never stored in plain text.
- **User verifies by:** creating the user via the CLI, logging in on the web page, confirming a protected API call fails when logged out.

### M4: Accounts backend
- **Goal:** accounts exist with the settings this product needs.
- **Build:** `Account` model and migration: name, type (savings, current, credit_card, wallet, cash, fd, rd, pot), purpose, capture mode (statement_import, manual_only, hybrid), opening balance in paise, start date, `parent_id` for pots, soft delete. `InterestRate` model: account, rate, from_date, frequency (daily, monthly, quarterly, yearly), recorded history not overwrites. Credit card extras: statement day and due day. CRUD endpoints under `/api/v1/accounts`.
- **Do not build:** balances, transactions, UI.
- **Tests:** create, update, soft delete, rate history keeps old rates, pot requires a valid parent, validation errors.
- **User verifies by:** using the auto-generated API docs page to create and list an account.

### M5: Accounts screen and real account setup
- **Goal:** the user's real accounts are in the app.
- **Build:** Accounts page: list, add, edit, with fields for type, capture mode, opening balance, start date, interest rate and frequency. A seed command that asks the user (interactively) for the opening balance and start date of each of: SBI, Central Bank, SBI Credit Card, slice, Indian Bank, Cash, and creates them with the right types and capture modes (Indian Bank manual_only, Cash manual, the others statement_import).
- **Do not build:** balances display beyond the opening balance, transactions.
- **Tests:** seed command idempotent, form validation.
- **User verifies by:** seeing all six accounts in the UI with correct settings.

### M6: Backup and restore
- **Goal:** the data cannot be lost.
- **Build:** a script to dump the database to a dated file in `backups/` (gitignored), a script to restore from a dump into a scratch database, and a documented command for each. A test that dumps and restores and compares row counts.
- **Do not build:** scheduling, remote storage.
- **User verifies by:** running backup, then restore into a scratch database, and checking the accounts appear.

### M7: Postings and the ledger core (backend only)
- **Goal:** balances computed correctly from postings.
- **Build:** `Transaction` and `Posting` models and migration (see ARCHITECTURE.md): posting kinds expense, income, transfer, adjustment, interest, fee, investment; soft delete. `core/ledger.py` with pure functions to compute an account balance from opening balance plus postings, and balance as of a date. A service to create a simple expense, income, and a transfer (two postings summing to zero). Balance endpoint per account.
- **Do not build:** UI, categories, imports.
- **Tests (write first):** expense and income change balances correctly; transfer moves money without changing the total; balance as of a date; opening balance start date ignores earlier postings; deleting a posting reverses its effect; no float ever appears.
- **User verifies by:** creating a transfer and an expense through the API docs page and checking balances.

### M8: Manual transaction entry
- **Goal:** the user can record spending and income by hand.
- **Build:** Transactions page: list (newest first, filter by account and date), add form (amount, date defaulting to today, account, direction, merchant, note), and transfer form between two accounts. Edit and delete (soft). Account balances shown on the Accounts page.
- **Do not build:** categories, quick text entry, check-in screen.
- **Tests:** API validation, list filtering, pagination.
- **User verifies by:** adding an expense, an income and a transfer in the UI and watching balances change.

### M9: Balance check and write-off
- **Goal:** closing a mismatch takes ten seconds.
- **Build:** a Balance Check action per account: enter the real balance, see computed vs stated and the difference, and either post an `adjustment` (category Unaccounted or Unrecorded income, with note and timestamp) or cancel. A `BalanceCheck` record of each check. A warning when an adjustment exceeds a configurable threshold, offering to look first but never blocking. A figure showing adjustments as a share of monthly spending.
- **Do not build:** automatic matching or AI suggestions.
- **Tests (write first):** difference computed in both directions; adjustment brings computed balance exactly to stated; adjustment is a visible posting; threshold warning.
- **User verifies by:** deliberately entering a wrong balance, posting the write-off, and seeing the adjustment in the list.

### M10: Categories
- **Goal:** spending is categorised.
- **Build:** two-level `Category` tree with a seeded Indian-household default set (editable), `category_id` on postings, category picker on the entry forms, a categories management page, and a basic spend-by-category view for a date range. Splits supported by multiple postings in one transaction.
- **Do not build:** auto-categorisation, rules, AI.
- **Tests:** tree integrity, spend-by-category totals exclude transfers and adjustments, split totals equal the original amount.
- **User verifies by:** categorising several transactions and seeing correct totals.

### M11: Daily check-in screen
- **Goal:** the two-minute daily ritual.
- **Build:** a single mobile-friendly screen: today's entries, then fast entry (amount first, then merchant suggestions from history, then account, category shown as a tappable suggestion chip). "Repeat last" and "same as yesterday" shortcuts. A catch-up mode that accepts a lump figure for several skipped days as an adjustment-style entry. A visible streak with no negative messaging.
- **Do not build:** notifications, recurring items.
- **Tests:** suggestion ordering by recency and frequency, lump entry creates the right postings.
- **User verifies by:** timing a realistic day's entry. Target: under two minutes.

### M12: Recurring and scheduled items
- **Goal:** repeating money is pre-filled.
- **Build:** `RecurringItem` (rent, EMI, SIP, subscription, salary): amount, account, category, day or frequency, active flag. The daily check-in pre-fills due items for one-tap confirmation. Items can be skipped or edited for that day. A recurring items management page.
- **Do not build:** automatic detection from history.
- **Tests:** due-date calculation for monthly, weekly and specific-day items, month-end edge cases, confirm creates correct postings, skip creates nothing.
- **User verifies by:** adding salary and rent as recurring items and confirming them from the check-in.

### M13: Interest accrual engine
- **Goal:** interest rates are actually used.
- **Build:** `core/interest.py`: pure accrual functions for daily, monthly and quarterly crediting using the dated rate records; separation of accrued-but-uncredited from credited interest; day-count convention stated in code. A scheduled job (APScheduler) that proposes interest postings, and a screen where the user confirms the credited amount from their bank. Interest shown as its own line on the account.
- **Do not build:** forecasts, loans.
- **Tests (write first):** daily accrual over a month with a changing rate, quarterly accrual, rate change mid-period uses the right rate, zero balance, large numbers stay exact.
- **User verifies by:** setting a rate on slice and checking the accrued interest looks right against their app.

### M14: Quick text entry
- **Goal:** type `450 dinner swiggy hdfc` and it works.
- **Build:** a deterministic parser (no AI): amount, optional words matched against merchant history and account names or aliases, optional category by keyword, optional `yesterday` or a date. Shown as a preview to confirm. Account aliases editable.
- **Do not build:** any AI call.
- **Tests:** many example strings, ambiguity handling (asks rather than guesses wrongly), Indian number formats.
- **User verifies by:** entering a dozen of their own typical expenses.

**PHASE 0 GATE:** the user uses the app for two weeks on manual entry. Ledger stays current, median check-in under 60 seconds, write-offs under 5% of spending. Do not start Phase 1 until the user says the gate is met.

---

## PHASE 1: Ingestion and categorisation

### M15: Import framework and SBI CSV
- **Goal:** the first statement imports safely.
- **Build:** the `importers/base.py` interface, `ImportBatch` model, upload endpoint, preview screen (rows to be added, duplicates found, closing balance check), commit, and reverse-whole-batch. SBI CSV parser built against a redacted sample in `data/samples/`. Fingerprint-based deduplication. Reject the batch if it does not reconcile to the statement closing balance.
- **Ask the user at this point** for a redacted SBI statement sample and how to redact it.
- **Tests:** parse the sample, duplicates skipped on re-import, reconciliation failure rejects, reverse removes exactly the batch.

### M16: Rules, merchant resolution, transfers and refunds
- **Build:** user-written rules, merchant resolver for UPI-style narrations, detection of own-account transfers, credit card bill payments, and refunds.
- **Tests:** a set of real redacted narrations with expected results.

### M17: AI categorisation and review queue
- **Build:** the provider-agnostic AI client, the categorisation cascade (confirmed merchants, rules, fuzzy match, model), a review queue for low-confidence items, learning from corrections, per-day spend ceiling, cache by normalised narration. Evaluation set of 200 real narrations.

### M18: Central Bank importer
### M19: SBI Credit Card importer (password-protected PDF)
### M20: slice importer

Detailed scopes for M16 to M20 are written when Phase 1 starts, using the real samples.

**PHASE 1 GATE:** a month of real statements imports with 90% correctly categorised and 100% reconciling imports.

---

## LATER PHASES (scoped in detail when reached)

- **Phase 2, plan and act:** budgets and envelopes, sinking funds, goals with backing types, bill calendar, cash-flow forecast, safe-to-spend, dashboard.
- **Phase 3, debt and net worth:** loans and prepayment simulator, credit cards, informal loans, investments with XIRR, CAS import, insurance register, net worth.
- **Phase 4, proactive co-pilot:** facts assembly and number guard, grounded Q&A, monthly audit, alerts, scenarios, health score, approved one-tap actions.
- **Phase 5, mobile.** **Phase 6, multi-user and commercial.**
- **Deployment to VPS** is a separate milestone group, done once Phase 0 is stable and backups are tested.
