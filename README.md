# Finance Co-pilot

An AI-powered personal finance web app for Indian households: one trustworthy ledger built from quick manual entry and bank statements, with an AI co-pilot that explains, audits and plans on top of it. Built locally first with Docker, deployed later to a budget VPS.

## How to start (4 steps)

1. Create a new empty folder anywhere and copy everything from this package into it, **including the hidden `.vscode` folder and the dot files** (`.gitignore`, `.env.example`, and so on).
2. Open that folder in VS Code and open your coding assistant chat (DeepSeek).
3. Open `PROMPTS.md`. Paste **Prompt 0**. It checks your machine, tells you exactly what to install if anything is missing (only Git and Docker), and creates the git repository.
4. Paste **Prompt 1**. It reads the project files and proposes Milestone 1. Review the plan, reply with Prompt 2, and continue milestone by milestone.

You never install Python or Node. Everything runs inside Docker.

## The files

| File | Purpose | Read by |
| --- | --- | --- |
| `PROMPTS.md` | The prompts you paste, in order, plus a ready-made prompt per milestone | You |
| `RULES.md` | How the assistant must work: one milestone at a time, plan then approval, hard money rules | The assistant, every session |
| `CODING_STANDARDS.md` | Backend, frontend, testing, security and git standards, with the tools that enforce them | The assistant, every session |
| `MILESTONES.md` | The build split into small milestones, each with scope, tests and how you verify it | The assistant and you |
| `PROGRESS.md` | Live milestone status; the assistant updates it after each approval | Both |
| `SPEC.md` | What the product is and does | The assistant |
| `ARCHITECTURE.md` | Stack, data model, money rules, API, AI layer, VPS deployment | The assistant |
| `DECISIONS.md` | Short log of non-obvious decisions and why | Both |
| `.env.example` | Every environment variable, no real values | Both |
| `.gitignore`, `.gitattributes`, `.editorconfig`, `.vscode/` | Git hygiene and editor settings | Tools |
| `backups/`, `data/samples/`, `scripts/` | Database backups, redacted bank statements, helper scripts (the first two are git-ignored) | Later milestones |

## The working loop

For every milestone: the assistant proposes a short plan, you approve it, it builds in small steps running tests after each, it stops and shows you how to verify, you try it yourself, and only then you say `APPROVED`. It never starts the next milestone on its own.

## Daily commands (available after Milestone 1)

```text
docker compose up --build                       # start everything
docker compose down                             # stop everything
docker compose down -v                          # stop and wipe the database

docker compose exec backend pytest              # backend tests
docker compose exec backend ruff check .        # backend lint
docker compose exec backend ruff format --check .
docker compose exec backend mypy app            # backend types
docker compose exec backend alembic upgrade head

docker compose exec frontend npm run lint       # frontend lint
docker compose exec frontend npm run format:check
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test           # frontend tests
```

## Privacy ground rules

- Real balances, bank statements, backups and secrets never go into git. `.env`, `backups/`, `data/samples/` and `seed_local.json` are ignored.
- Take a database backup before any risky change, and again after the first week of real data (available after Milestone 6).
- Review `git diff --staged` before every commit.
