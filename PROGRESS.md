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
| M9a Balance check backend | done | `BalanceCheck` model, migration 0007, pure reconciliation maths, the service that posts the write-off as a visible `adjustment` posting, and three endpoints. Approved. |
| M9b The ten-second screen | done | *Check balance* on an account: enter the real balance, see the ledger's figure, the bank's and the difference, then write it off or put it away, with the nudge and the month's share. M9 is complete. Approved. |
| M10a The category tree | done | `Category` model, migration 0008 (the table and `postings.category_id`), the seeded Indian-household set, tree CRUD with its rules, and `seed-categories`. Approved. |
| M10b Categories in use | done | A movement carries a category; a write-off takes `Unaccounted for spending` or `Unrecorded income` by its sign; a movement can be split between categories; spend by category. Approved. |
| M10c The picker on the entry forms | done | The category tree offered as a flat `Branch · Child` picker on the recording form, splits between categories with the parts having to add up exactly, and the filing shown and changed on the edit screen. Approved. |
| M10d The categories page and the spend view | done | A third tab: the tree editable in place — add, rename, move, remove, with the server's own refusals — and the period's spending by branch, with the money in no category reported beside it. M10 is complete. Approved. |
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

**M10 is complete**: money is filed under names the user owns, and the app answers both sides of the
question — a movement says what it was filed under, and the categories screen shows what each branch cost
in a period and how much of the spending has no name on it at all. **The two-week Phase 0 gate is next**,
which needs the twelve figures only the user can give (`seed`), and real use from there.

Before the app holds real data:

- Running `seed` for real needs the 12 values only the user can give: for each of the six accounts, the
  balance that was true on a start date, and that date. Nothing else blocks it.
- The development database was rebuilt from empty in M7 and holds two accounts (SBI, Central Bank) and
  eleven movements recorded through the API and the screen during the M7–M9b walkthroughs, nine of them
  live and two removed from the screen, plus four balance checks and two write-offs (₹500 and ₹6,000 of
  unaccounted spending). SBI's balance is ₹1,45,000 because a walkthrough wrote it down to a stated
  figure. These are dummy entries with no real balances, kept for now so there is something to look at.
  `seed --demo` restores the six placeholders; `docker compose down -v` clears everything.
- The development database has a category tree: the seeded 51 names over 18 top-level groups, created by
  `seed-categories`, plus one extra top-level name (*Filter coffee*) left by the M10a walkthrough. The two
  write-off names are in the tree. `docker compose down -v` clears this with the rest.
- The M10b walkthrough added an account called *Walkthrough* (opening ₹1,00,000 on 2026-04-01) holding a
  few October 2026 movements: two filed under *Groceries* and *Eating out* directly, one ₹500 shop split
  between them, and two write-offs (₹220 found, ₹420 short) that filed themselves under *Unrecorded
  income* and *Unaccounted for spending*. Its balance stands at the stated figure of its last check
  (₹99,000). Nothing real, and useful for looking at M10c's screens.
- Take a backup before any risky change: `./scripts/backup.sh`.
- The M10d walkthrough edited the tree and put it back: *Groceries* was renamed to *Fruit & veg* (which the
  movements list immediately said it was filed under), moved under *Home*, then moved back and renamed
  again, so the tree stands as the default set plus *Filter coffee*. The month it showed was
  ₹4,050.00: ₹1,300.00 under *Food & groceries* (Eating out ₹700.00, Groceries ₹600.00) and ₹2,750.00
  filed under nothing.
- The M10c walkthrough added two movements to the *Walkthrough* account on 6 October 2026: ₹250 with no
  category (it was filed under *Groceries*, then refiled to *Eating out*, then cleared, which is the
  clearing path) and a ₹500 shop split between *Groceries* and *Eating out*. Useful for looking at
  M10d's screens alongside the category tree.

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
- The write-off nudge is a flat `BALANCE_CHECK_WARNING_PAISE` (₹1,000), and the month's share is shown
  beside it rather than altering it. Whether the threshold itself should become a share of spending
  (SPEC.md: under 5% is healthy, 25% means something is systematically missing) is still open; two
  figures that disagree would be worse than one honest figure, so this waits for real use.
- A write-off can still be edited or deleted in the Transactions screen, which would leave the check that
  produced it unreconciled with nothing warning about it. Proposed: refuse to change or remove an
  adjustment a check points at, or mark it as belonging to a check. Not built in M9b.
- The share is per account. The Phase 0 gate's "write-offs under 5% of spending" wants one figure across
  every account, which needs its own endpoint.
- A write-off is now filed under `Unaccounted for spending` or `Unrecorded income`, by the sign of its
  difference. Renaming or removing those two names leaves a write-off unfiled, silently: it is the user's
  tree, and the check is recorded either way, but nothing says the filing has gone. Proposed: a line in
  the balance-check panel when the name is missing. Not built in M10b.
- A movement may be split between categories, but every part must name one, and the parts must add up to
  the amount exactly. A part with no category is not offered, because the user can leave the whole
  movement unfiled instead. If real use asks for a half-filed split, that is a change to the request
  shape rather than to the ledger.
- Unknown fields are ignored rather than refused, so `parts` or `category_id` on a transfer payload is
  accepted and dropped. Same open question as `PATCH /accounts` above; the fix is one rule for every
  route rather than a second special case.
- The spend report has no row for uncategorised spending, so its rows do not add up to total spending for
  the period. **Decided**: a report-only *Uncategorised* row arrives with the M10d spend view, where the
  figure can be shown and explained rather than sitting in the API on its own.
- The Transactions list does not say which category a movement was filed under; the filing is only
  visible when a row is opened. **Decided**: M10d shows it in the row, so the work of filing is visible
  without opening anything.
- The picker is one flat list of `Branch · Child` names, which is fine on a desktop and long on a phone
  (43 names today). Kept as it is deliberately; M11's phone screen is where a two-step branch-then-name
  picker should be judged, with a thumb rather than a mouse.
- A write-off now carries no note, so its row is titled *No description* with *Filed under Unaccounted for
  spending* underneath; write-offs recorded before this change keep their note and say the wording twice.
  **Decided**: the wording belongs in the filing alone. If *No description* reads poorly in daily use, the
  one-line fix is to let the filing title the row and drop the line beneath it.
- The confirmation before a removal counts the names a category holds but cannot say how much money is
  filed under it: the tree a screen has carries no figures. The server's refusal names it either way.
- The spend view is one period at a time: no comparison with last month, and no drill-in from a branch to
  the movements behind it. **Decided**: that belongs with M11's daily screen rather than here.
- A group can be created as spending or earning only. An `adjustment` name can be made through the API but
  nothing would offer it, so the form does not offer it either.
- The spend report reads every matching posting and adds the figures up in Python, which is what keeps
  money out of the database's arithmetic. One household's month is a few hundred rows; a decade of import
  would want a grouped query, and that is a decision to make then, not now.
