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
| M8b Transactions screen | done | Transactions tab: the list newest first, account and date filters, and one form that records an expense, an income or a transfer. Balances still live on the API only. Approved. |
| M8c Edit, delete and balances in the UI | done | A movement opens pre-filled for correction, removal asks first and is soft, and each account shows the balance it was worked out from. M8 is complete. Approved. |
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

**M8 is complete**: a movement can be recorded, listed, filtered, corrected and removed by hand, and
each account shows the balance those movements produced. **M9 is next** — the balance check and
write-off — after which the two-week Phase 0 gate can begin.

Before the app holds real data:

- Running `seed` for real needs the 12 values only the user can give: for each of the six accounts, the
  balance that was true on a start date, and that date. Nothing else blocks it.
- The development database was rebuilt from empty in M7 and holds two accounts (SBI, Central Bank) and
  nine movements recorded through the API and the screen during the M7, M8a, M8b and M8c walkthroughs,
  seven of them live and two removed from the screen. They are dummy entries with no real balances, kept
  for now so there is something to look at. `seed --demo` restores the six placeholders;
  `docker compose down -v` clears everything.
- Take a backup before any risky change: `./scripts/backup.sh`.

## Open questions

- Error body shape: CODING_STANDARDS.md section 3.4 asks for a consistent error body with a
  `code` and a `message`, but the API still returns FastAPI's `{"detail": ...}` on the auth and
  account routes. Proposed as its own small change.
- `PATCH /api/v1/accounts/{id}` ignores unknown fields, so `{"type": "cash"}` returns 200 and
  changes nothing. Proposed: reject unknown fields with 422 instead of ignoring them.
- The account routes do not declare their 404/400 responses, so `/docs` lists only 401/422 for
  them; the rate routes declare theirs. Documentation-only follow-up.
- A removed movement cannot be reached from the screen: the row disappears and the balance moves, with
  no way to list or restore it. Proposed: a `?removed=true` filter plus an undelete, either inside M9's
  balance check or as its own small change.
- The Accounts screen asks for one balance per account. That is a handful of cached calls today; past
  roughly twenty accounts it should become a single `GET /accounts/balances`.
