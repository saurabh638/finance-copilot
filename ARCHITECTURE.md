# ARCHITECTURE

Build and run everything locally with Docker Compose first. Deployment to a budget VPS later is a configuration change, not a rewrite. Product behaviour is in SPEC.md; working rules are in RULES.md; code style is in CODING_STANDARDS.md.

## 1. Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | Python 3.12, FastAPI | Parsing, financial math and AI SDKs are strongest in Python. Typed models and an auto-generated OpenAPI schema keep a coding model honest |
| Database | PostgreSQL 16 | Exact arithmetic, strong dates, JSONB for raw statement rows, identical in Docker and on any host |
| ORM and migrations | SQLAlchemy 2.0 (**sync**) and Alembic | Migrations from the first commit. Sync keeps code simple and easier for a model to get right; this is a single-user app |
| DB driver | psycopg 3 | Current, well supported |
| Validation | Pydantic v2, pydantic-settings | One definition of each shape; config from environment |
| Backend tooling | ruff (lint and format), mypy, pytest, pytest-cov | See CODING_STANDARDS.md |
| Frontend | React 18, Vite, TypeScript (strict) | Fast reload, huge training corpus, ports to React Native later |
| Frontend libraries | Tailwind CSS, TanStack Query, React Router, Recharts | Utility styling; server-state caching; routing; charts |
| Frontend tooling | ESLint, Prettier, Vitest, Testing Library | See CODING_STANDARDS.md |
| API types | `openapi-typescript` generating from the FastAPI schema | Removes a class of drift bugs |
| Background jobs | APScheduler in the backend process | Interest accrual, reminders, digests. No queue at this size |
| Auth | Server-side sessions in Postgres, HttpOnly cookie, Argon2 | Revocable and simple. Mobile can use token auth against the same endpoints later |
| PDF and tables | pdfplumber, pikepdf (encrypted PDFs), pandas | The SBI card PDF will be password-protected |
| AI runtime | Provider-agnostic client behind one interface | Runtime model is a config value, separate from the model used to write the code |
| Containers | Docker Compose | Local stack mirrors production |

**Deliberately left out for now:** Redis, Celery, microservices, Kubernetes, GraphQL, server-side rendering frameworks, async SQLAlchemy. Add only when something actually hurts.

**Host machine needs only Git and Docker.** Python and Node live inside the containers. Never install project packages on the host.

## 2. Repository layout

```text
finance-copilot/
  docker-compose.yml
  docker-compose.prod.yml        # added at deployment
  .env.example                   # every variable, no real values
  README.md  SPEC.md  ARCHITECTURE.md  RULES.md
  CODING_STANDARDS.md  MILESTONES.md  PROGRESS.md  DECISIONS.md  PROMPTS.md
  scripts/                       # backup, restore, helpers (cross-platform)
  backups/                       # gitignored
  data/samples/                  # gitignored; redacted statements for parser tests
  backend/
    Dockerfile
    pyproject.toml               # ruff, mypy, pytest config
    requirements.txt  requirements-dev.txt
    alembic.ini
    alembic/versions/
    app/
      main.py                    # app factory, router registration
      config.py                  # settings from environment
      db.py                      # engine, session
      models/                    # SQLAlchemy models, one file per domain
      schemas/                   # Pydantic request and response shapes
      api/v1/                    # routers, one file per domain, thin
      services/                  # business logic and DB access
      core/                      # pure functions: money, ledger, interest, forecast
      importers/                 # base.py plus one parser per bank
      categorise/                # rules, resolver, detection
      ai/                        # client, facts, prompts/
    tests/                       # mirrors app/ structure
  frontend/
    Dockerfile
    package.json
    src/
      api/                       # generated client types and fetch wrapper
      components/                # reusable UI
      features/                  # one folder per domain: accounts, transactions, checkin...
      lib/                       # money formatting, dates, utilities
      pages/  hooks/
```

## 3. Layering rules

- **Routers** handle HTTP only and are about five lines each: parse, call a service, return.
- **Services** hold business logic and database access. Callable without a request object, so scheduled jobs reuse them.
- **`core/`** is pure functions over data: no database, no I/O, no clock access (pass dates in). Every money calculation lives here and has tests.
- Rule of thumb: arithmetic on money goes in `core/`; database access goes in a service; reading a request goes in a router.
- The frontend contains **no business logic**. A second client (mobile) must get identical behaviour from the API alone.

## 4. Money rules (invariants, each needs a test)

1. **Paise, always.** Integers in Python, `BIGINT` in the database. No floats, even in intermediate steps. Formatting to `₹1,23,456.78` (lakh and crore grouping) happens only at the presentation edge, via one helper per language.
2. **Balance is derived, never stored as truth.** Opening balance plus postings since the opening date. A cache is allowed only if recomputable and a test asserts they agree.
3. **Every movement is a posting.** An ordinary expense or income is one posting. A transfer between two accounts is exactly two postings in one transaction that sum to zero.
4. **Sign convention:** positive = money into an account, negative = out. Assets hold positive balances; liabilities (credit card, loan) hold negative balances.
5. **Posting kinds:** `expense`, `income`, `transfer`, `adjustment`, `interest`, `fee`, `investment`. Only `expense` and `income` count in spending analytics. Credit card bill payments are transfers; refunds net against the original.
6. **Adjustments are real and visible:** an `adjustment` posting with category, note, and the computed-versus-stated figures recorded. Never a silent balance overwrite.
7. **Opening balance** is dated at the account start date; nothing before that date needs to exist.
8. **Interest accrues on a schedule, by code.** Dated rate records; the engine takes a frequency (daily, monthly, quarterly) and a stated day-count convention. Accrued-but-uncredited interest is shown separately from credited. Each accrual posting records the rate and period that produced it.
9. **Two dates:** `transaction_date` (when money moved) and `posted_date` (when the bank recorded it). Analytics use `transaction_date`.
10. **Imports are batches** carrying `import_batch_id` and raw source text, reversible whole. A batch that does not reconcile to the statement closing balance is rejected, never partially applied.
11. **Idempotent imports:** a deterministic fingerprint per row (account, date, amount, normalised narration) with a tolerance window for the same payment via two channels.
12. **Nothing is hard-deleted.** Soft delete with a timestamp.

## 5. Data model (core entities)

- **User:** email, password_hash, created_at.
- **Account:** user_id, name, type (`savings`, `current`, `credit_card`, `wallet`, `cash`, `fd`, `rd`, `loan`, `pot`), purpose, capture_mode (`statement_import`, `manual_only`, `hybrid`), parent_id (self-reference for pots), opening_balance_paise, opening_date, statement_day and due_day (cards), is_active, timestamps, deleted_at. Pots are child accounts: one table, no special cases.
- **InterestRate:** account_id, rate (stored as basis points or exact decimal, never float), from_date, frequency, note. History is kept; never overwrite.
- **Category:** user_id, name, parent_id (two levels), kind. `Unaccounted` and `Unrecorded income` live here.
- **Transaction:** user_id, transaction_date, posted_date, merchant, note, raw_narration, source (`manual`, `import`, `recurring`, `ai_approved`), import_batch_id, fingerprint, timestamps, deleted_at. A container for postings.
- **Posting:** transaction_id, account_id, amount_paise (signed), category_id (nullable), kind. **Category lives on the posting**, so splits are multiple postings with no separate split table.
- **ImportBatch:** account_id, source file reference, statement closing balance, status, created_at, reversed_at.
- **BalanceCheck:** account_id, computed_paise, stated_paise, difference_paise, adjustment_posting_id, checked_at.
- **Later:** Rule, Merchant, RecurringItem, Bill, Budget, Goal (with backing type and backing_account_id), Loan, Holding, Policy, AIProposal (facts used, suggested change, approved_at).

Everything derived (balances, budget usage, goal progress, loan outstanding, net worth) is computed from postings, not stored and incremented.

## 6. API conventions

- REST under `/api/v1`, JSON only. Every route except `health` and `auth/login` requires a session.
- **Money is always integer paise in JSON**, never a pre-formatted string. Clients format.
- Dates ISO 8601. Every list endpoint paginates and accepts a `since` parameter (offline sync needs it later).
- Errors: consistent shape with a machine-readable `code` and a human `message`. 4xx for caller mistakes, never 200 with an error body.
- Coarse dashboard endpoint (one call, everything the home screen needs).
- Illustrative surface: `auth/login`, `accounts`, `accounts/{id}/balance`, `accounts/{id}/balance-check`, `transactions`, `transactions/quick`, `checkin/today`, `imports` (upload, preview, commit, reverse), `budgets`, `goals`, `loans`, `investments`, `dashboard`, `copilot/ask`, `copilot/audit/{month}`.

## 7. The AI layer

- **Facts contract:** before any AI call, `ai/facts.py` assembles a structured object of computed figures relevant to the request. The model receives it alongside the question. It never queries the database and never sees raw table dumps.
- **Number guard:** every numeric token in model output is checked against the facts object before reaching the user. An unsupplied, non-derivable number is a failed response: logged, regenerated or returned without the claim.
- **Redaction in `facts.py`**, not in templates: account numbers, card numbers and third-party names are stripped or tokenised before anything leaves the app.
- **Categorisation cascade, cheapest first:** exact match on confirmed merchants, user rules, fuzzy match, model, then the review queue. Log hit rates; a falling rule hit-rate signals statement format drift.
- **Prompts are versioned files** in `ai/prompts/`, each with a small evaluation set of real examples run like tests.
- **Provider independence:** one interface (`complete`, `complete_structured`); the runtime model is a config value.
- **The AI writes nothing directly.** Every AI-originated change is an `AIProposal` the user approves; ordinary service code then applies it.
- **Cost control:** cache categorisation by normalised narration, batch the monthly audit into one call, enforce a per-day spend ceiling with a visible counter.

## 8. Local development

- `docker compose up --build` starts `db` (postgres:16, named volume), `backend` (FastAPI, source mounted, hot reload) and `frontend` (Vite dev server). `docker compose down -v` resets to a clean database.
- The backend reads `DATABASE_URL` from the environment. That is the one thing that changes between laptop and server.
- **Seed data from a local, gitignored file** (`seed_local.json`, with a committed `seed_example.json`). Real balances never enter git.
- **Redacted sample statements** live in `data/samples/` (gitignored). Parser tests run against them.
- **Backups even locally:** `pg_dump` into `backups/` (gitignored) and a restore script that is actually tested. Losing two months of manual entry would end the project.

## 9. Deployment to a budget VPS (later)

Done once Phase 0 is stable and backups are tested. The same Docker images run unchanged.

- **Host:** a small Linux VPS (roughly 2 GB RAM is enough for one user). Docker and Docker Compose installed; non-root deploy user; SSH key login only; password login disabled; firewall allowing only 22, 80 and 443; automatic security updates.
- **`docker-compose.prod.yml`:** `db`, `backend` (no reload, production server), `frontend` as a static build, and **Caddy** as reverse proxy with automatic HTTPS. The database port is never exposed publicly.
- **Secrets:** a separate production `.env` on the server, with different values from local. Never in git.
- **Backups:** scheduled `pg_dump` to a location **off the server** (object storage or another machine) plus a periodically tested restore. A VPS where you own the volume is only safe if this exists.
- **Before going live, three things must exist:** automated backups with a tested restore, production-only secrets, and an authenticated health check.
- **Monitoring at this scale:** an uptime check on the health endpoint and disk-space alerting are enough.

## 10. Environment variables (see `.env.example`)

`APP_ENV`, `SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (initial user creation only), `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_DAILY_BUDGET`. New variables must be added to `.env.example` in the same change that introduces them.
