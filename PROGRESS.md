# Progress

The assistant updates this file only after the user says `APPROVED` for a milestone.

Status values: `not started`, `plan approved`, `built, awaiting verification`, `done`.

| Milestone | Status | Notes |
| --- | --- | --- |
| Environment setup (Prompt 0) | done | Git + Docker only on host; repo initialised and pushed |
| M1 Project skeleton | done | Approved; backend + frontend skeleton, all tooling green |
| M2 Money module | done | Integer paise parse/format/split in core; formatter mirrored in lib/money.ts |
| M3 Single-user login | done | M3a backend auth + DB-backed login rate limit, M3b login UI. Approved. |
| M4a Accounts CRUD backend | done | Account model, migration 0004, CRUD under `/api/v1/accounts`, soft delete. Approved. |
| M4b Interest rates | done | Second half of MILESTONES.md M4: `InterestRate` model, migration 0005, dated history that is never overwritten, 3 endpoints. Approved. |
| M5a Accounts screen: list and add | done | Accounts page, add form, money text parsed to paise in the frontend, API types generated from the schema. Approved. |
| M5b Edit an account and its rate history | done | Inline editor per account: change the settings (type shown fixed), append dated rates, remove one only after a confirmation. Approved. |
| M5c Interactive seed command | done | `seed` asks for each account's balance and start date, skips what already exists, and offers `--demo` / `--remove-demo`. Approved. |
| M6 Backup and restore | done | Dated dumps in `backups/`, restore into a scratch database, a row-count round trip, and the last-resort promotion documented and tested. Approved. |
| M7 Postings and ledger core | done | `Transaction` and `Posting` models, migration 0006, pure `core/ledger.py`, expense/income/transfer services, and the balance endpoint. Approved. |
| M8a Transactions API | done | Recording, reading back, editing and soft-deleting a movement: `POST`/`GET /api/v1/transactions` and `GET`/`PATCH`/`DELETE /api/v1/transactions/{id}`. The create body is a discriminated union on `kind`. Approved. |
| M8b Transactions screen | not started | The list, its filters and the add form, on a two-item app shell. |
| M8c Edit, delete and balances in the UI | not started | Editing and deleting from the screen, with each account's balance shown. |
| M9 Balance check and write-off | not started | |
| M10 Categories | not started | |
| M11 Daily check-in screen | not started | |
| M12 Recurring and scheduled items | not started | |
| M13 Interest accrual engine | not started | |
| M14 Quick text entry | not started | |
| Phase 0 gate (two weeks of real use) | not started | |
| M15 Import framework and SBI CSV | not started | |
| M16 Rules, merchants, transfers, refunds | not started | |
| M17 AI categorisation and review queue | not started | |
| M18 Central Bank importer | not started | |
| M19 SBI Credit Card importer | not started | |
| M20 slice importer | not started | |

## Current focus

M7 and M8a are built and on `main`: a movement can be recorded, listed, corrected and deleted through the
API, and a balance can be watched moving. **M8b is next** — the Transactions screen — followed by M8c,
which brings editing, deleting and balances into that screen. M8 as a whole is the point from which the
two-week Phase 0 gate can realistically begin.

Before the app holds real data:

- Running `seed` for real needs the 12 values only the user can give: for each of the six accounts, the
  balance that was true on a start date, and that date. Nothing else blocks it.
- The development database was rebuilt from empty in M7 and holds two accounts (SBI, Central Bank) and
  six transactions recorded through the API during the M7 and M8a walkthroughs, one of them
  soft-deleted. They are dummy entries with no real balances, kept for now so M8b has something to
  show. `seed --demo` restores the six placeholders; `docker compose down -v` clears everything.
- Take a backup before any risky change: `./scripts/backup.sh`.

## Open questions

- Error body shape: CODING_STANDARDS.md section 3.4 asks for a consistent error body with a
  `code` and a `message`, but the API still returns FastAPI's `{"detail": ...}` on the auth and
  account routes. Proposed as its own small change.
- `PATCH /api/v1/accounts/{id}` ignores unknown fields, so `{"type": "cash"}` returns 200 and
  changes nothing. Proposed: reject unknown fields with 422 instead of ignoring them.
- The account routes do not declare their 404/400 responses, so `/docs` lists only 401/422 for
  them; the rate routes declare theirs. Documentation-only follow-up.
