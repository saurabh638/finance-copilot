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
| M4b Interest rates | not started | Second half of MILESTONES.md M4: `InterestRate` model, migration 0005, rate history that never overwrites. |
| M5 Accounts screen and real account setup | not started | |
| M6 Backup and restore | not started | |
| M7 Postings and ledger core | not started | |
| M8 Manual transaction entry | not started | |
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

M4a (accounts CRUD backend) approved and on `main`. M4 was split into M4a (accounts) and M4b
(interest rates) when the plan was reviewed, because the model, migration, CRUD endpoints and
their tests already exceed one reviewable step and the rate history needs its own tests.
**M4b is next, and needs its plan approved before any code.**

## Open questions

- Error body shape: CODING_STANDARDS.md section 3.4 asks for a consistent error body with a
  `code` and a `message`, but the API still returns FastAPI's `{"detail": ...}` on the auth and
  account routes. Proposed as its own small change, not part of M4b.
- `PATCH /api/v1/accounts/{id}` ignores unknown fields, so `{"type": "cash"}` returns 200 and
  changes nothing. Proposed: reject unknown fields with 422 instead of ignoring them.
