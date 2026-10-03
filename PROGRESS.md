# Progress

The assistant updates this file only after the user says `APPROVED` for a milestone.

Status values: `not started`, `plan approved`, `built, awaiting verification`, `done`.

| Milestone | Status | Notes |
| --- | --- | --- |
| Environment setup (Prompt 0) | done | Git + Docker only on host; repo initialised and pushed |
| M1 Project skeleton | done | Approved; backend + frontend skeleton, all tooling green |
| M2 Money module | done | Integer paise parse/format/split in core; formatter mirrored in lib/money.ts |
| M3 Single-user login | built, awaiting verification | Split — M3a backend auth incl. DB-backed login rate limit: done, approved; M3b login UI: not started |
| M4 Accounts backend | not started | |
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

M3a (backend auth) done on `m3a-backend-auth` and merged to `main`. M3b (login UI) not started — awaiting the user.

## Open questions

None yet.
