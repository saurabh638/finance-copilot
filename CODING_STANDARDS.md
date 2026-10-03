# CODING STANDARDS

These apply to every line written in this project. They are enforced by tooling wherever possible, and by review where not. If a standard blocks you, stop and ask; do not work around it. RULES.md governs the workflow and money rules; this file governs how code is written.

## 1. Principles

1. **Correctness first, then clarity, then cleverness (never).** Boring, obvious code beats clever code.
2. **Small, single-purpose units.** A function does one thing. A module has one reason to change. Aim for functions under about 30 lines and files under about 300; if bigger, split with a reason.
3. **Make wrong states hard to represent.** Use types, enums and validation at the boundary so bad data cannot get in.
4. **Fail loudly on financial data.** A wrong number silently shown is worse than an error.
5. **Do not duplicate.** Search the repository before writing anything. Reuse or extend; never reimplement.
6. **Do not add what was not asked for.** No speculative features, abstractions, config options or dependencies.
7. **Leave the code more tested than you found it.** Every behaviour change has a test in the same change.

## 2. Tooling (set up in Milestone 1 and run before every commit)

| Area | Tool | Command (via Docker) |
| --- | --- | --- |
| Backend lint | ruff check | `docker compose exec backend ruff check .` |
| Backend format | ruff format | `docker compose exec backend ruff format --check .` |
| Backend types | mypy (strict on `app/core`, standard elsewhere) | `docker compose exec backend mypy app` |
| Backend tests | pytest with coverage | `docker compose exec backend pytest` |
| Frontend lint | ESLint | `docker compose exec frontend npm run lint` |
| Frontend format | Prettier | `docker compose exec frontend npm run format:check` |
| Frontend types | `tsc --noEmit` | `docker compose exec frontend npm run typecheck` |
| Frontend tests | Vitest and Testing Library | `docker compose exec frontend npm test` |

A change is not done until **all of these pass** and the output has been shown. Do not disable a lint rule, add `# type: ignore`, `eslint-disable` or `@ts-ignore` without a one-line comment explaining why and a mention in the report.

## 3. Backend standards (Python)

### 3.1 Style and structure
- Python 3.12. Format with ruff (line length 100). Imports sorted by ruff. No wildcard imports.
- **Type hints on every function signature and public attribute.** `Any` is forbidden outside narrow, commented boundaries.
- Naming: `snake_case` functions, variables and modules; `PascalCase` classes; `UPPER_SNAKE` constants. Names say what a thing is: `opening_balance_paise`, not `bal`.
- **Money variables carry the unit in the name** (`amount_paise`). Never a bare `amount` for money.
- Docstrings on public functions in `core/` and services: one line saying what, plus units, invariants and edge cases where non-obvious. Comments explain *why*, never *what*.
- Prefer pure functions and small dataclasses or Pydantic models over classes with hidden state. No global mutable state.
- Use `Decimal` or integer arithmetic only. `float` is banned for anything financial; ruff and review enforce it. Rates are stored as integer basis points or exact decimals, never floats.
- Dates and times: store UTC timestamps, dates as `date`. Never call `datetime.now()` or `date.today()` inside `core/`; pass the date in so the code is testable. Money dates are plain `date` values in `Asia/Kolkata` terms at the edges.

### 3.2 Layering (see ARCHITECTURE.md section 3)
- `api/` routers: thin, no logic, no database queries, no money arithmetic. Declare `response_model` on every route.
- `services/`: business logic and database access. Take a session as a parameter. One transaction per use case; commit at the service boundary, not scattered.
- `core/`: pure functions only. No imports from `models`, `db`, `services` or `api`. No I/O.
- `models/` (SQLAlchemy) never leak into API responses; return Pydantic schemas.

### 3.3 Database
- SQLAlchemy 2.0 style (`select()`, typed `Mapped[...]` columns). No raw SQL strings unless unavoidable, and then always parameterised.
- **Every schema change has an Alembic migration** with a clear message; migrations are reviewed and must run forward on a fresh database. Never edit the database by hand and never edit an applied migration.
- Money columns `BIGINT` (paise). Add explicit `NOT NULL`, foreign keys, `CHECK` constraints and indexes for real query patterns. Timestamps `created_at`, `updated_at`; `deleted_at` for soft delete.
- Queries that return lists are paginated. Watch for N+1 queries; use explicit loading.
- Soft delete only for financial records; queries exclude deleted rows by default via one shared helper, not ad hoc filters.

### 3.4 API
- Versioned under `/api/v1`. Nouns for resources, plural (`/accounts`, `/transactions`). Standard verbs and status codes (201 on create, 204 on delete, 404, 409 conflict, 422 validation).
- Money in JSON is **integer paise**; never a formatted string. Dates ISO 8601.
- Request and response models are Pydantic v2 with strict types and explicit validators for business invariants (for example a transfer's two amounts sum to zero).
- Consistent error body with `code` and `message`. Never expose stack traces or internal ids of other users' data.
- Every route except `health` and `auth/login` depends on the auth dependency.

### 3.5 Errors and logging
- Define small domain exceptions (for example `ReconciliationError`, `InsufficientDataError`) and map them to HTTP responses in one place.
- **Never `except Exception:` and continue.** Catch the narrowest exception, handle it meaningfully or re-raise. No bare `except`. No `pass` in handlers.
- Structured logging via the standard `logging` module. **Never log financial values, balances, narrations, account numbers or personal data.** Log ids and event names.

### 3.6 Configuration and secrets
- All configuration through `pydantic-settings` reading environment variables, in one `config.py`. No `os.environ` calls scattered around. No hard-coded URLs, keys or paths.
- Secrets never in code, tests, fixtures, logs or git. `.env.example` is updated in the same change that adds a variable.

### 3.7 Dependencies
- Pin versions in `requirements.txt` and `requirements-dev.txt`. **Adding a dependency needs approval:** state what it does, why the standard library or an existing dependency is not enough, and its maintenance health.

## 4. Frontend standards (TypeScript and React)

### 4.1 Style and structure
- TypeScript **strict mode** on. No `any`; use `unknown` and narrow. No non-null assertions (`!`) without a comment. ESLint and Prettier clean.
- Functional components and hooks only. One component per file, named like the file (`AccountCard.tsx`). `PascalCase` components, `camelCase` functions and variables, `kebab-case` not used for source files except config.
- Folder by feature (`features/accounts`, `features/transactions`), shared pieces in `components/` and `lib/`. A feature folder holds its components, hooks, API calls and tests together.
- Props typed with explicit interfaces. Components small and focused (under about 150 lines); extract hooks for logic and keep components mostly presentational.
- No business logic in the frontend. If the UI needs a number, the API provides it. The UI formats and displays.

### 4.2 Data and state
- **Server state uses TanStack Query.** No copying server data into global state. Local UI state uses `useState`/`useReducer`. No global state library unless a milestone needs it and it is approved.
- API types come from the generated OpenAPI types; never hand-write a type that duplicates the server schema.
- Money is received as integer paise and shown through the single `lib/money.ts` formatter (Indian grouping). **Never do arithmetic on money with JavaScript floats in the UI**; if a sum is needed, the API returns it, or use integer paise arithmetic only.
- Forms: controlled inputs with validation that mirrors the server rules; show server errors clearly. Money inputs parse text to paise through the shared helper.
- Loading, empty and error states are designed for every screen. No unhandled promise rejections; no silent catches.

### 4.3 UI quality
- **Mobile-first.** Every screen works at 360px width. The daily check-in must be fast with one hand: large tap targets (at least 44px), amount field focused first, numeric keypad on mobile.
- Accessibility: semantic HTML, labels on every input, visible focus, sufficient contrast, keyboard operable, no information conveyed by colour alone.
- Tailwind utility classes; extract repeated patterns into components rather than long class strings repeated. A small set of design tokens (colours, spacing, radius) defined once.
- Tone: calm. No guilt, no red alarm screens for missed days. Numbers show Indian formatting and the ₹ symbol.
- No dependency for something a few lines of code or the platform already does.

## 5. Testing standards

- **Tests first for anything involving money, dates, parsing, balances, interest or categorisation.** Show the tests, confirm they express the intended behaviour, then implement.
- Test **intended behaviour**, not the implementation's current output. A test that merely snapshots what the code does proves nothing.
- Backend: pytest. Unit tests for `core/` (fast, no database); integration tests for services and API using a real Postgres test database (not mocks of the database). Each test independent and deterministic: no shared mutable state, no real clock, no network. Fixtures build realistic data.
- Cover the edges that bite in finance: zero, negative, very large amounts, exact lakh and crore boundaries, month-end and leap-year dates, financial-year boundary (31 March / 1 April), duplicate imports, rounding in splits (no paise lost or created).
- Parser tests run against redacted real samples. Every bug fixed gets a regression test.
- Frontend: Vitest and Testing Library test behaviour the user sees (what renders, what happens on click), not component internals. Test money formatting thoroughly, with the same cases as the backend helper.
- Name tests as sentences: `test_transfer_moves_money_without_changing_total`.
- Coverage is a signal, not a goal: aim for near-complete coverage of `core/`, and meaningful coverage elsewhere.
- Never claim tests pass without running them and showing the real output.

## 6. Security standards

- Every route authenticated except `health` and `auth/login`. Passwords hashed with Argon2; never logged or returned. Sessions in an HttpOnly, SameSite cookie, expiring. Rate-limit the login endpoint.
- Validate and bound all input (sizes, ranges, file types and sizes for uploads). Parameterised queries only. Escape output; never render raw HTML from data.
- Uploaded statements are stored outside any web-served path, with generated file names, size limits and type checks. Encrypted PDFs: the password is used in memory and never stored or logged.
- No secrets in git, ever. Check `git diff --staged` before committing.
- CORS locked to the known frontend origin. Security headers set in production (Caddy).
- AI calls: redact account and card numbers and third-party names first; send the minimum; log what category of data was sent, not the data.
- Dependencies kept current; an audit step (`pip-audit`, `npm audit`) is run before deployment.

## 7. Git standards

- `main` is always working. One branch per milestone: `m<number>-<short-name>`. Never commit directly to `main` except the initial commit.
- **Small, focused commits.** One logical change per commit, tests included. Message format: `M<number>: <imperative summary>`, for example `M7: add posting model and ledger balance`. A body explains *why* when not obvious.
- Commit only after the user approves the milestone (RULES.md). Never force-push, rewrite history or delete branches unasked.
- Before every commit: all tooling in section 2 is green, `git status` and `git diff --staged` reviewed, no secrets or real financial data staged.
- No generated files, build output, `node_modules`, `.env` or backups in git (see `.gitignore`).

## 8. Review checklist (the assistant runs this on its own work before reporting)

- [ ] Only what the milestone asked for was built; nothing extra.
- [ ] No float appears in any money path (search for `float(`, `/ 100`, `* 0.`, JS `parseFloat` on money).
- [ ] All money arithmetic lives in `core/` (backend) or the shared helper (frontend).
- [ ] Every schema change has a migration that runs on a fresh database.
- [ ] No business logic in routers or React components.
- [ ] No broad exception handling, no swallowed errors, no financial data in logs.
- [ ] Tests cover the happy path, the edges and the failure paths; all tooling is green with real output shown.
- [ ] `.env.example` and docs updated if configuration or commands changed.
- [ ] Anything surprising, any assumption made and any limitation is stated in the report.

## 9. Definition of done (for a milestone)

Built to the milestone definition and nothing beyond it. All tooling green with real output shown. New behaviour tested including edges. App runs from a clean `docker compose up --build` and the user-verification steps in MILESTONES.md work. Report delivered in the format in RULES.md. **Not done until the user says `APPROVED`.**
