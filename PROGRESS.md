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
| M5c Interactive seed command | not started | The six real accounts, from prompts for opening balance and start date. |
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

M4 (accounts CRUD, interest rates), M5a (accounts screen: list and add) and M5b (inline editor and
rate history) are built and on `main`. M5 was split into M5a, M5b and M5c during plan review because
the screen, its tests and the seed command together are well past one reviewable change.
**M5c (the interactive seed command) is next.** It can be built and verified with placeholder values;
the real balances and start dates are only needed when the user runs it.

## Open questions

- Error body shape: CODING_STANDARDS.md section 3.4 asks for a consistent error body with a
  `code` and a `message`, but the API still returns FastAPI's `{"detail": ...}` on the auth and
  account routes. Proposed as its own small change.
- `PATCH /api/v1/accounts/{id}` ignores unknown fields, so `{"type": "cash"}` returns 200 and
  changes nothing. Proposed: reject unknown fields with 422 instead of ignoring them.
- The account routes do not declare their 404/400 responses, so `/docs` lists only 401/422 for
  them; the rate routes declare theirs. Documentation-only follow-up.
