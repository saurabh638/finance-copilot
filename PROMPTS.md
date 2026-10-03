# Prompts to paste

Paste these into your coding assistant chat. Prompts 0 and 1 are used once to start. Prompts 2 and 3 repeat for every milestone, and Prompt 4 starts each one (a ready-made version for every milestone is at the end of this file). Prompt 5 is for when something is wrong. Prompt 6 is for the start of any later chat.

The loop for each milestone: **Prompt 4 (plan) -> you read the plan -> Prompt 2 (approve plan, build) -> you verify it yourself -> Prompt 3 (approve, commit).**

---

## Prompt 0: Environment check and setup (paste once, first)

```
You are helping me set up my computer for a project in this folder. Do not write any project code yet.

First, read RULES.md and CODING_STANDARDS.md in this folder. Then do the following, one step at a time, showing me the real output of each command:

1. Detect my operating system and shell.
2. Check whether these are installed and working, and show versions: Git, Docker (including `docker compose`), and for the editor, the `code` command is not required.
3. For anything missing, tell me exactly what you will install and how (for example winget on Windows, Homebrew on macOS, apt on Linux). Ask me to confirm before installing anything. Install only Git and Docker. Do NOT install Python or Node on my machine, because everything will run inside Docker.
4. If Docker Desktop needs a restart, WSL, virtualization enabled, or me to open it once and accept terms, tell me clearly what to do, then wait for me to say "done".
5. Verify Docker works by running `docker run --rm hello-world`, and verify `docker compose version`.
6. Run `git init` in this folder if it is not already a repository, set the default branch to `main`, and make an initial commit containing all files currently in the folder with the message "Initial project documents".
7. If git has no user name or email configured, ask me for them and set them locally for this repository only.

When finished, give me a short checklist of what is installed and working, and anything that still needs my attention. Then stop and wait. Do not start Milestone 1.
```

---

## Prompt 1: Session start and Milestone 1 plan (paste once, after Prompt 0 succeeds)

```
Read these files fully before doing anything: RULES.md, CODING_STANDARDS.md, SPEC.md, ARCHITECTURE.md, MILESTONES.md, PROGRESS.md, DECISIONS.md.

Then confirm in 6 lines or fewer: what the product is, the milestone protocol you will follow, the money rules you must never break, and the coding standards and checks that must pass before any step is called done.

Now we start Milestone 1 (Project skeleton). Follow RULES.md section 1 strictly:
- Give me only the PLAN for Milestone 1: the files you will create, the tests you will write, and any questions. Do not write any code yet.
- Keep it to one screen of text.
- Then stop and wait for me to reply "APPROVED PLAN".

Do not look ahead to any other milestone.
```

---

## Prompt 2: Approve the plan (paste after you are happy with a plan)

```
APPROVED PLAN. Build this milestone now, following RULES.md section 1.

- Build in small steps, no more than about 200 lines of new code at a time. Tell me when you are splitting.
- For anything involving money, dates, parsing or categorisation, show me the tests first, then implement.
- Run the tests and show me the real output.
- When the milestone is built, STOP and report using: Built / How to verify / Test results / Limitations / Questions.
- Do not commit, do not update PROGRESS.md, and do not start the next milestone until I say APPROVED.
```

---

## Prompt 3: Approve the milestone (paste after you have verified it yourself)

```
APPROVED. I have verified this milestone.

Now do only this:
1. Commit all changes on the milestone branch with the message format "M<number>: <what>".
2. Merge the branch into main.
3. Update PROGRESS.md: mark this milestone `done` and add one line of notes.
4. Add any non-obvious decision from this milestone to DECISIONS.md, one line each, with the reason.
5. Show me `git log --oneline -5` and the updated PROGRESS.md table.

Then STOP. Do not propose or start the next milestone until I ask.
```

---

## Prompt 4: Start the next milestone (paste to begin each new milestone)

```
Start Milestone <NUMBER> from MILESTONES.md.

Re-read RULES.md and the milestone definition first. Create the branch m<NUMBER>-<short-name>.

Give me only the PLAN: files to create or change, tests to write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and tell me why.
```

---

## Prompt 5: Something is wrong or needs changing (paste as needed)

```
This milestone is not approved yet. Here is what I found:

<describe what you saw, what you expected, and the steps you took>

Do this:
1. Explain in two or three sentences what you think the cause is.
2. Propose the smallest fix. Do not change anything unrelated.
3. Wait for me to say "go" before changing code.
4. After the fix, re-run the tests, show the output, and stop and report again.
```

---

## Prompt 6: Starting a later session (paste at the start of any new chat)

```
New session. Read RULES.md, CODING_STANDARDS.md, SPEC.md, ARCHITECTURE.md, MILESTONES.md, PROGRESS.md and DECISIONS.md fully.

Then tell me in under 10 lines: which milestones are done, which one is in progress and its status, and what you think the next step is. Run `git status` and `git branch` and show me the output.

Do not write or change any code. Wait for my instruction.
```

---

## Handy one-liners (paste when needed)

**Check everything still runs**
```
Run the full test suite and show me the output, then run `docker compose up -d`, check the health endpoint and show me the result, then stop. Do not change any code.
```

**Review before I approve**
```
Before I approve this milestone, run the review checklist in CODING_STANDARDS.md section 8 against your own work, and compare it with the milestone definition in MILESTONES.md. List anything you did that was not in scope, any money handled outside core/, any place a float could appear, any lint or type suppression you added, and any untested path. Run all the checks in CODING_STANDARDS.md section 2 and show the real output. Do not change code, just report.
```

**Take a backup**
```
Run the backup script, show me where the file was written, and confirm the file size is not zero. (Available after Milestone 6.)
```

---

## Ready-made Prompt 4 for each milestone
Use one of these in place of the generic Prompt 4. Each one already names the milestone and adds the things that matter most for it. Only use the next one after the previous milestone is APPROVED and committed.

### Milestone 2: Money module

```
Start Milestone 2 (Money module) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 2 definition first. Create the branch m2-money-module.

Extra emphasis for this milestone: Write the test file first and show it to me before any implementation. I will check the expected Indian number formats myself.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 3: Single-user login

```
Start Milestone 3 (Single-user login) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 3 definition first. Create the branch m3-login.

Extra emphasis for this milestone: Never print, log or commit the password. The admin email and password come from .env, which must stay out of git.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 4: Accounts backend

```
Start Milestone 4 (Accounts backend) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 4 definition first. Create the branch m4-accounts-backend.

Extra emphasis for this milestone: Rates must be stored as exact values (basis points or decimal), never floats, and rate history must be kept, not overwritten. Include the Alembic migration and prove it runs on a fresh database.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 5: Accounts screen and real account setup

```
Start Milestone 5 (Accounts screen and real account setup) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 5 definition first. Create the branch m5-accounts-screen.

Extra emphasis for this milestone: The seed command must ask me for my real opening balances interactively and must not store them anywhere in git. Add a seed_example.json with fake numbers only. Generate the frontend API types from the OpenAPI schema here, as described in ARCHITECTURE.md.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 6: Backup and restore

```
Start Milestone 6 (Backup and restore) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 6 definition first. Create the branch m6-backup-restore.

Extra emphasis for this milestone: It must work on Windows PowerShell, macOS and Linux. Run pg_dump inside the db container and write into a mounted backups folder. Do not redirect binary output with the > operator. Restoring must go into a scratch database first, and the test must compare row counts.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 7: Postings and the ledger core (backend only)

```
Start Milestone 7 (Postings and the ledger core (backend only)) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 7 definition first. Create the branch m7-ledger-core.

Extra emphasis for this milestone: Tests first for every balance rule, including transfers, as-of-date balances and the opening-balance start date. All balance math goes in core/ledger.py as pure functions that take dates as parameters.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 8: Manual transaction entry

```
Start Milestone 8 (Manual transaction entry) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 8 definition first. Create the branch m8-manual-entry.

Extra emphasis for this milestone: Mobile-first layout at 360px width. The amount field is focused first and shows a numeric keypad on phones. Amounts are parsed to paise through the shared money helper; no float arithmetic in the UI.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 9: Balance check and write-off

```
Start Milestone 9 (Balance check and write-off) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 9 definition first. Create the branch m9-balance-check.

Extra emphasis for this milestone: Tests first. The adjustment must be a visible posting with a note, never a silent overwrite, and after posting it the computed balance must equal the stated balance exactly.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 10: Categories

```
Start Milestone 10 (Categories) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 10 definition first. Create the branch m10-categories.

Extra emphasis for this milestone: Spend-by-category must exclude transfers and adjustments. A split must always add up to the original amount with no paise lost or created.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 11: Daily check-in screen

```
Start Milestone 11 (Daily check-in screen) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 11 definition first. Create the branch m11-daily-checkin.

Extra emphasis for this milestone: This is the screen I will use every day, so keep it very light: few taps, large tap targets, amount first. Streak display must never use guilt or alarm styling. Tell me how you will measure the two-minute target.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 12: Recurring and scheduled items

```
Start Milestone 12 (Recurring and scheduled items) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 12 definition first. Create the branch m12-recurring.

Extra emphasis for this milestone: Tests first for due-date calculation, including month-end days like the 31st and February in leap years.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 13: Interest accrual engine

```
Start Milestone 13 (Interest accrual engine) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 13 definition first. Create the branch m13-interest-engine.

Extra emphasis for this milestone: Tests first. slice credits interest daily and SBI quarterly, so the engine must take a frequency and a stated day-count convention. All interest math lives in core/interest.py as pure functions.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### Milestone 14: Quick text entry

```
Start Milestone 14 (Quick text entry) from MILESTONES.md.

Re-read RULES.md, CODING_STANDARDS.md and the Milestone 14 definition first. Create the branch m14-quick-entry.

Extra emphasis for this milestone: Deterministic parser only, no AI calls. When the text is ambiguous it must ask me rather than guess. Show me the full list of test strings before implementing.

Give me only the PLAN: files to create or change, the steps you will build in (each under about 200 lines), the tests you will write, anything unclear, and any risk. Do not write code. Keep it to one screen. Then stop and wait for "APPROVED PLAN".

If the milestone is bigger than it should be, propose splitting it into two sub-milestones and explain why.
```

### After Milestone 14: the two-week gate

```
Milestone 14 is approved. Do not start any new milestone.

Help me prepare for the Phase 0 gate in MILESTONES.md: write a short checklist I can follow for two weeks of real use (what to enter daily, when to run a balance check, when to take a backup), and list what I should note down each week (median check-in time, how many write-offs and their share of spending, any friction). Keep it to one page. Then stop.
```

Do not start Milestone 15 until you have used the app for two weeks and tell the assistant the gate is met.

---

## If the assistant goes off the rails

Paste this the moment it starts building ahead, skips the plan, or changes things you did not ask for:

```
Stop. You have broken RULES.md section 1. List exactly which rule you broke and which files you changed or created that were outside the approved plan. Do not fix anything yet. Wait for my instruction.
```

If it seems to have forgotten the rules (long chats lose context), start a fresh chat and paste Prompt 6. Chats are disposable; the files in this folder are the memory.

## When the assistant asks you a question

- If it asks which option you prefer and you are unsure, answer: "Pick the simplest option that meets the milestone, explain your choice in two lines, and record it in DECISIONS.md after approval."
- If it asks to add a library, answer only after it states what it does, why the standard library or an existing dependency is not enough, and its maintenance status.
- If it asks to do something large ("shall I also build X?"), answer: "No. Note it in the report as a suggestion only."
