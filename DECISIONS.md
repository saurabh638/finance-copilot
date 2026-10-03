# DECISIONS

One line per non-obvious decision and why. The assistant adds to this after each approved milestone. Newest at the bottom.

| Date | Decision | Why |
| --- | --- | --- |
| 2026-10-04 | Money is integer paise everywhere; no floats | Rounding drift in a finance app is unrecoverable trust damage |
| 2026-10-04 | Balances are derived from postings, never stored as truth | Stored running totals drift |
| 2026-10-04 | Category lives on the posting, not the transaction | Splits come free: one payment, several postings |
| 2026-10-04 | Pots are child accounts (`parent_id`), one table | Slice goals, FDs and sub-balances need no special cases; net worth sums the tree once |
| 2026-10-04 | Python and FastAPI backend, React and TypeScript frontend | PDF and statement parsing is far stronger in Python; frontend ports to React Native later |
| 2026-10-04 | Sync SQLAlchemy 2.0 with psycopg 3, not async | Simpler and less error-prone for a single-user app built with a coding model |
| 2026-10-04 | Server-side sessions in Postgres with an HttpOnly cookie | Revocable and simple; mobile can use tokens later |
| 2026-10-04 | Everything runs in Docker; host needs only Git and Docker | Zero local toolchain setup, and local mirrors production |
| 2026-10-04 | No Redis, Celery, microservices or Kubernetes | Added only when something actually hurts |
| 2026-10-04 | Real balances and statements stay out of git (seed_local.json, data/samples, backups ignored) | Privacy; the repository may become shared |
| 2026-10-04 | Deploy to a budget VPS behind Caddy, backups kept off the server | Free tiers sleep or expire; the data is financial history and needs a stable home |
| 2026-10-04 | Work proceeds one milestone at a time with plan approval and a completion approval | Prevents large unreviewed changes from a coding model |
| 2026-10-04 | A dedicated `finance_test` database is created by the Postgres init script; tests run against real Postgres | Integration tests need a real database, and development data must stay untouched |
| 2026-10-04 | The backend container entrypoint runs `alembic upgrade head` before starting | A fresh database is always migrated, with no manual step |
| 2026-10-04 | The frontend health check reads only the HTTP status, not the JSON body | Avoids hand-writing a duplicate of the server schema; generated OpenAPI types come later |
| 2026-10-04 | Money parsing rejects more than two decimal places instead of rounding | A silently rounded amount is a wrong number the user would never see |
| 2026-10-04 | A split gives the remainder paise to the first parts | Deterministic, and the parts always sum back to the total with no paise lost or created |
| 2026-10-04 | Parsing accepts Indian and Western digit grouping but rejects malformed grouping | Real inputs vary, yet broken grouping almost always means a typo worth failing on |
| 2026-10-04 | The frontend mirrors only the money formatter, not a parser | The UI formats what the API sends; it never parses or does money arithmetic |
| 2026-10-04 | Passwords are hashed with Argon2 (argon2-cffi) | Memory-hard and the algorithm named in ARCHITECTURE; never stored or logged in clear |
| 2026-10-04 | Session tokens are random and stored only as a SHA-256 hash | A stolen database dump must not be replayable as a login |
| 2026-10-04 | One app-level auth guard with an allowlist, not per-route dependencies | A router added later is protected by default and cannot be exposed by forgetting a dependency |
| 2026-10-04 | `create-user` reads credentials from the environment, never CLI arguments | Passwords passed as arguments appear in shell history and the process list |
| 2026-10-04 | Login rate limiting lives in Postgres (`login_failures`), not in memory | CODING_STANDARDS section 6 needs a limit and section 3.1 forbids global mutable state; Postgres also survives restarts and extra workers |
