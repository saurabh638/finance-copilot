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
