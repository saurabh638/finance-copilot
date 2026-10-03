# RULES for the coding assistant

Read this file, CODING_STANDARDS.md, SPEC.md, ARCHITECTURE.md, MILESTONES.md, PROGRESS.md and DECISIONS.md at the start of EVERY session before doing anything. If anything conflicts, stop and ask.

**Order of authority when documents disagree:** RULES.md (workflow and money rules), then CODING_STANDARDS.md, then ARCHITECTURE.md, then MILESTONES.md, then SPEC.md. Never resolve a conflict silently; point it out.

## 1. The milestone protocol (most important)

1. **One milestone at a time.** Work only on the milestone the user names. Never start, prepare, scaffold or "get ahead" on the next one.
2. **Plan first, no code.** Before writing code, reply with: the milestone goal, the exact files you will create or change, the tests you will write, and anything you are unsure about. Then STOP and wait for the user to reply `APPROVED PLAN` (or give changes).
3. **Build small.** Inside a milestone, work in the smallest steps that can be run and tested. Do not generate more than about 200 lines of new code in one step. If the plan needs more than about 6 steps or 600 lines in total, propose splitting the milestone into sub-milestones BEFORE starting, and wait for approval of the split. After each step, run the tests and tooling and show the real output before taking the next step.
4. **Tests are part of the work.** For anything involving money, balances, dates, parsing or categorisation, write the tests FIRST, show them to the user, then implement. Run the tests and show the real output. Never claim tests pass without running them.
5. **Stop and report.** When the milestone is built, first run the review checklist in CODING_STANDARDS.md section 8 against your own work. Then stop. Report: what was built, how to run it, the exact commands to verify, test results, known limitations, and anything you chose that the user did not specify. Then wait.
6. **Approval gate.** Only after the user replies `APPROVED` do you: commit, update PROGRESS.md, and add any decision to DECISIONS.md. Then STOP. Do not propose or begin the next milestone until the user asks.
7. **If something fails or is unclear, stop and ask.** Do not guess, do not work around, do not silently change scope. If a test or check still fails after two fix attempts, stop, explain the cause and ask.
8. **Never expand scope.** No extra features, libraries, refactors or "improvements" that were not in the milestone. Suggest them in the report instead.

## 2. Money and data rules (never break these)

- Money is **integer paise**. Never floats, anywhere, including intermediate steps. Database type `BIGINT`.
- All money arithmetic lives in `backend/app/core/` as pure functions with tests. Routers and services call them; they never do their own money math.
- A balance is derived: opening balance plus postings since the start date. Never store a running balance as truth.
- Every movement is a posting. A transfer is two postings in one transaction summing to zero.
- Transfers, credit card bill payments and refunds must never count as income or expense.
- A write-off is a visible `adjustment` posting with a note. Never silently overwrite a balance.
- Imports are batches with a batch id and are reversible. A batch that does not reconcile to the statement closing balance is rejected.
- Soft delete only. Never hard delete financial records.
- The AI never calculates numbers. It receives computed facts and explains them. Any number in AI output must exist in the facts passed in.

## 3. Code rules

**CODING_STANDARDS.md is binding.** Everything below is a summary of the most important points, not a replacement. All tooling in CODING_STANDARDS.md section 2 (ruff, mypy, pytest, ESLint, Prettier, tsc, Vitest) must pass, with real output shown, before a step is called done.

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest. Frontend: React, Vite, TypeScript, Tailwind.
- Every schema change needs an Alembic migration. Never edit the database by hand.
- Layers: routers (HTTP only, short) call services (logic and database), which call `core/` (pure functions).
- Routers must not contain business logic. Frontend must not contain business logic.
- API is versioned under `/api/v1`, JSON only, money always as integer paise (never pre-formatted strings), lists paginated.
- No broad `except Exception` that swallows errors. Fail loudly on bad financial data.
- No new dependency without telling the user why and getting approval.
- Never reimplement something that exists. Search the repo first.
- No secrets in code or in git. Configuration through environment variables; keep `.env.example` current.
- Never log financial values or personal identifiers.
- Do not send account numbers, card numbers or raw statement files to any AI model.

## 4. Running things

- The host machine only needs Git and Docker. Run everything through Docker Compose: tests with `docker compose run --rm backend pytest`, the app with `docker compose up`.
- Do not install Python or Node packages on the host.
- Before saying a step works, run it. Show the actual command output.

## 5. Communication style

- Be brief and concrete. No long preambles.
- When reporting, use this order: Built / How to verify / Test results / Limitations / Questions.
- Assume the user is not going to read the code. Explain how to check behaviour in the running app instead.
- Ask a question only when blocked, and ask one at a time.

## 6. Git

- Work on a branch per milestone: `m<number>-<short-name>`.
- Commit only after the user says `APPROVED`. Message format: `M<number>: <what>`.
- Never force-push, never rewrite history, never delete branches without being asked.
