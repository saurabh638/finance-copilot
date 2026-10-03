# SPEC: AI Personal Finance Co-pilot

A finance co-pilot for Indian households. It reads your money wherever it lives, keeps one trustworthy ledger, and acts as an always-on expert that plans, audits and nudges. Built for one user first (the owner), architected so a mobile app and more users can follow without a rewrite.

This is the condensed product spec. Scope is intentionally a little flexible: when a detail here conflicts with reality, raise it and decide, do not silently work around it.

## 1. Product thesis

Indians already know where their money went; almost nobody knows what to do next. Existing apps stop at the pie chart. This product starts there. Three jobs:

1. **Know my position.** One honest picture across bank accounts, cards, loans, investments and cash, built from statements and quick manual entry.
2. **Tell me what it means.** Not "you spent 42,000 on food" but "food is 18% above your own six-month median, driven by eleven delivery orders in ten days, and it will push your Goa fund two months late."
3. **Tell me what to do, and do the boring part.** Ranked actions sized to real cash flow. The app drafts the change; the user approves it.

The moat is an AI that understands Indian transaction text (UPI narrations, four banks, cash, family transfers, informal loans) and learns each household's own vocabulary from corrections.

## 2. Design principles (constraints on every feature)

1. **The ledger is deterministic; the AI sits on top.** Every balance, total, projection and interest figure is computed by tested code. The model receives computed facts and explains, ranks or drafts. It never does arithmetic on money.
2. **AI proposes, the user disposes.** Nothing is written to the ledger by the AI without explicit approval. Every AI-originated change is labelled and reversible.
3. **Every insight is traceable.** Each claim links to the transactions or rules behind it.
4. **Manual entry is a first-class path, not a fallback.** Some banks never produce a usable statement. Every manual flow gets the same care as automated ones.
5. **Daily effort is capped at two minutes.** If keeping the ledger current takes longer on an ordinary day, the product has failed.
6. **Approximately right and current beats exactly right and abandoned.** Let the user close a gap, round a figure or write off a difference and move on.
7. **Correctness over coverage.** Parse three banks perfectly rather than twelve badly. A wrong transaction is worse than a missing one.
8. **Honest about what it is not.** Planning guidance, not regulated investment advice. It says "I don't know" and flags when a human professional is needed.
9. **The user's data stays the user's.** Full export, deletion on request, minimum data sent to any model, no selling of data, ever.
10. **India is the base case.** UPI narration, lakh and crore formatting, the financial year ending 31 March, EMIs, SIPs, EPF, PPF, NPS are first-class.

## 3. The first user's accounts (sets build order)

| Account | Type | Capture mode | Notes |
| --- | --- | --- | --- |
| SBI | Savings | Statement import | Parser priority 1. CSV and PDF available |
| Central Bank | Savings | Statement import | Parser priority 2 |
| SBI Credit Card | Credit card | Statement import | PDF, usually password-protected. Has statement cycle and due date |
| slice | Savings | Statement import | Statement via Accounts, Passbook, Download Statement. Interest tracks the RBI repo rate and is credited **daily** |
| Indian Bank | Savings | Manual only | No usable export. Depends on the daily check-in and balance check |
| Cash | Cash wallet | Manual, periodic reconcile | Topped up by ATM withdrawals. Difference written off |

The product must be complete for a user whose primary account never exports. Phase 0 stands on its own.

## 4. Features by domain

### 4.1 Accounts and balances
- Types: savings, current, credit card, wallet, cash, FD, RD, loan, and **pot** (a named sub-balance inside a parent account). The type drives behaviour (a card has a statement cycle and due date).
- **Opening balance and start date are configurable per account.** An account joins the ledger with a balance the user types as of a date they choose. Everything before it is out of scope. The same mechanism handles an account the user stopped tracking for two months.
- **Capture mode per account:** `statement_import`, `manual_only` or `hybrid`. A manual-only account is never flagged for a missing import; a statement account not updated in six weeks is.
- **Interest rates are configurable wherever they apply** and used by the engine: savings (daily, monthly or quarterly credit), FD and RD (maturity value), loans (amortisation), card APR on revolved balance, informal loans (rate may be zero). Rates are **dated**: a change is recorded, never overwritten. Unknown rate: use a stated default and label the figure an estimate.
- Account purposes (emergency fund, spending, travel) form a routing plan, and a payday sweep checklist says how much to move where.

### 4.2 Daily capture: the two-minute ritual
- **Daily check-in:** one screen. Shows the day's known items (imported, recurring, scheduled) pre-filled for one-tap confirmation, then asks: anything else today?
- Fast entry: amount first, then a merchant suggested from history, then account. Category is predicted and shown as a tappable chip.
- Shortcuts: "repeat last", "same as yesterday". Recent merchants and amounts first.
- Natural-language entry: `450 dinner swiggy hdfc` creates the transaction.
- Nothing mandatory except amount and account.
- A skipped day is not a failure. Ask for a lump figure ("roughly how much cash went out over the last three days?") rather than a day-by-day reconstruction.
- Streaks and prompts used carefully: gentle nudge, visible streak, weekly summary. No guilt, no red screens.
- **Cash:** model as a cash wallet topped up by ATM withdrawals. The user periodically enters actual cash in hand and the difference is written off. Counting every chai is not a goal.

### 4.3 Reconciliation and the write-off
- **Balance check:** the user enters the real balance from their banking app; the engine shows the computed balance and the difference. Ten seconds. The most valuable habit the product can build.
- **Write-off:** post the difference as an `adjustment` in one tap. It is a **real, visible transaction**, never a silent overwrite, with its own category (`Unaccounted for spending`, `Unrecorded income`), a note and a timestamp.
- Unaccounted spending is tracked as its own figure. About 3% of monthly spending is healthy; 25% means something is systematically missing.
- Guardrails: a large write-off prompts a quick check first (missed recurring charge? missed import? untracked account?). Write-offs are capped against a configurable threshold above which the user is nudged to investigate. Not blocked, just asked.
- Repeated small adjustments on one account are surfaced as a pattern worth fixing.

### 4.4 Transactions and categorisation
- Merchant resolution (turn `UPI/P2M/ZOMATO*8821/YESB` into Zomato, Food delivery). Two-level editable category tree, tags, splits, notes with receipts.
- Three detections matter more than the rest: **transfers between own accounts** are not income or expense; **credit card bill payments** are transfers; **refunds and reversals** net against the original.
- Recurring detection (subscriptions, EMIs, SIPs, rent), user-written rules, and a review queue holding only items the model was unsure about.

### 4.5 Budgets and cash flow
- Envelope budgets per category per month (carry-forward or reset). **Sinking funds** spread irregular costs (insurance, festivals, annual fees, school fees) across the months before they land.
- Rolling cash-flow forecast 3 to 12 months ahead from known income, scheduled bills, detected habits and projected interest (its own line).
- **Safe-to-spend:** what can I spend today without breaking a commitment.

### 4.6 Goals
- A goal is a target amount, a target date and a funding source. The app computes the required monthly contribution, tracks progress, recalculates the projected completion date, and shows tradeoffs between competing goals honestly.
- **Backing types:** *earmarked* (a label over ordinary money), *account-backed* (a whole account is the goal), *pot-backed* (a named sub-balance inside a provider, for example slice goals, RDs, FDs opened for a purpose).
- A pot is a child of its parent account with a user-entered balance the balance check can reconcile, and interest configured at pot level where the provider pays it separately.
- **A rupee is counted once:** money in a pot counts in the account balance for net worth but is excluded from safe-to-spend, because it is committed. Earmarked goals must not overcommit an account.
- Funding: a contribution schedule (fixed amount, percentage of income, round-ups), a source account, optionally a destination pot. On payday the contribution appears in the sweep checklist as a transfer. Withdrawals from a goal are deliberate and logged with a reason.

### 4.7 Debt and credit
- Loans with principal, rate, tenure, EMI and a generated amortisation schedule. **Prepayment simulator** (interest saved, tenure cut, prepay vs invest). Avalanche vs snowball with the real rupee difference.
- Credit cards: statement cycle, due date, minimum due, utilisation, interest if revolved, rewards.
- **Informal loans** (money lent to or borrowed from family) are first-class.

### 4.8 Investments and net worth
- Mutual funds, equity, FDs, PPF, EPF, NPS, gold, real estate; XIRR, allocation vs target, SIP tracking. Holdings follow the same backing model as goals: held in a named account or pot, so net worth never double-counts. Mutual funds importable from a CAS statement.
- Net worth over time is the headline dashboard number.

### 4.9 Insurance and tax
- Policy register with premiums as scheduled bills and renewal reminders; coverage adequacy check.
- Old vs new regime comparison, 80C and 80D headroom, capital gains (short and long term), advance tax reminders. Tax views follow the April to March financial year.

### 4.10 Analytics and dashboard
- Compare the user with their own past, never national averages. Default to rolling windows. Lead each chart with its finding in words. Every number clickable down to its transactions. Rank ruthlessly: three things that changed beats forty things that exist.
- Dashboard depths: **10 seconds** (net worth and change, safe-to-spend, one sentence on what needs attention), **30 seconds** (envelopes ordered by how off-track, bills in 14 days, goal progress, anomalies, card dues), **5 minutes** (drill-downs, trends, forecast, performance, audit).

### 4.11 The co-pilot
Natural-language capture and grounded Q&A over the user's own ledger, a monthly audit, proactive alerts (renewal at double price, card due with low balance, category 40% hot), health score with reasons, scenario simulation, and approved one-tap actions.

## 5. Where the AI adds value (five layers over a deterministic ledger)

1. **Understand the mess:** parse unseen statement layouts, resolve merchants from narration, classify. The real product; everything depends on it.
2. **Learn this household:** remember corrections, counterparties, what is normal. The retention moat.
3. **Explain and answer:** grounded Q&A, the monthly audit, why a number moved.
4. **Advise and plan:** rank tradeoffs, size goals to real cash flow, prepay vs invest. Simulation is deterministic; choosing what to surface is judgement.
5. **Act, with approval:** draft the budget change, flag the anomaly, propose the sweep.

**The line that must not be crossed:** totals, balances, EMI schedules, XIRR, interest and projections are computed by code and unit tested. The model receives them as given facts.

## 6. Getting data in

| Channel | Coverage | Phase |
| --- | --- | --- |
| Manual entry and daily check-in | Everything, including cash and banks with no export | 0 |
| CSV / XLS statement upload | One account, one period; parser per bank | 1 |
| PDF statement upload | Banks with no CSV; password-protected files | 1 to 2 |
| Credit card statements | Itemised card spending, PDF | 2 |
| Email parsing (alerts) | Most card and bank alerts; needs inbox access | 3 |
| CAS statement | Mutual funds and demat | 4 |
| SMS parsing (Android) | Very high; needs Play Store approval; not possible on iOS | 5, mobile only |
| Notification listener (Android) | UPI apps and card alerts | 5, mobile only |
| Account Aggregator | Banks, insurers, funds, consent-based; needs FIU onboarding via a licensed AA or TSP, effectively a company, counsel and budget | 6 |

Never let early value depend on a regulatory gate. Build on statements and manual entry; prototype Account Aggregator in the sandbox only when the core is stable.

**Parsing pipeline (every channel feeds it):** ingest raw artefact immutably with an import batch id, extract rows (bank parser, model fallback), normalise (date, amount in paise, direction, account, raw narration), deduplicate, resolve merchant and classify, detect transfers/refunds/recurring, queue low-confidence items, learn from corrections. Ingest, normalise and deduplicate stay deterministic.

## 7. Trust, security, privacy

- Encryption in transit and at rest, secrets in environment variables only, every route authenticated, rate limiting on auth, expiring sessions, statement files stored encrypted, financial values never logged, audit log of writes, automated and **restore-tested** backups.
- AI privacy: send the minimum, redact account and card numbers and third-party names before sending, prefer aggregates, provider swappable, log what was sent.
- India's DPDP Rules 2025: full compliance due 13 May 2027. A single-user personal tool triggers almost nothing; obligations arrive with the second user (consent and notice, withdrawal, access/correction/erasure, breach process, processor agreements, retention periods). Set a minimum signup age (under-18 needs verifiable parental consent).

## 8. Non-goals

Payments and money movement. Stock or fund recommendations (SEBI-regulated). Lending or credit brokerage. Social or comparison features. Crypto (until the core is solid). Full double-entry accounting. Selling anonymised data, ever.

## 9. Key risks

Categorisation accuracy below the trust threshold. AI hallucinating a number. Statement format drift (reconcile against closing balance and refuse imports that do not). Abandonment after a month. Advice wrong for the user's situation. Security incident. Scope collapse (phase gates).

## 10. Phases and gates

| Phase | Scope | Gate |
| --- | --- | --- |
| 0 | Ledger core and daily capture | Ledger current for two weeks on manual entry alone, under two minutes a day |
| 1 | Ingestion and categorisation | A month of real statements imports with 90% categorised without intervention; 100% reconcile |
| 2 | Plan and act: budgets, goals, forecast, dashboard | Used weekly without a reminder |
| 3 | Debt and net worth | The net worth figure is one you would quote without checking |
| 4 | Proactive co-pilot | You act on its advice at least once a month |
| 5 | Mobile with Android SMS capture | Play Store approval for SMS permission |
| 6 | Multi-user and commercial | Second user onboarded without hand-holding |

## 11. Success metrics

Phase 0: median check-in seconds under 60; ledger current 14+ days; write-offs under 5% of spending. Phase 1: 90% (rising to 95%) correctly categorised; under 5 minutes per month of statements; 100% of imports reconcile. Phase 4: zero AI answers containing a number not in the computed facts. Personal headline: has the spreadsheet been abandoned, and is the check-in still happening in week six.

## 12. Open questions

- Sample exports of each bank statement are needed before Phase 1 parsers.
- Are the amounts owed to individuals in the existing plan loans with interest, informal family transfers, or recurring support?
- Where does the idle surplus go? The goals model needs a stated purpose.
- Which AI provider serves the in-app model at runtime, and under what data-retention terms?
- Is this a personal tool that might become a product, or a product that starts personal?
