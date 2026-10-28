---
name: feature
description: Run the full agentic workflow for one work item. The tester and developer agree on acceptance criteria up front, the developer implements, the reviewer reviews, and the tester validates, looping until the tester is satisfied. Use when the user asks to build a feature or a todo from DECISIONS.md's Open list.
argument-hint: <work item, e.g. "kyu grades" or "A4 paper">
---

# Feature workflow

Work item: $ARGUMENTS

You are the **orchestrator**. You don't write production code or tests
yourself. You delegate to the `tester`, `developer` and `reviewer`
subagents, pass their outputs between them, and keep the user informed.
Run the subagents in the foreground: each step depends on the one before.

**Commits.** Only you may commit, and exactly twice per run: a snapshot
before the run (Phase 0) and the validated result after the hand-off
(Phase 5). No subagent ever changes git state, and you never push, tag,
amend, stash, reset, rebase, check out or switch branches. The user pushes
and tags releases.

Pick a short kebab-case `<slug>` for the work item. All the paperwork lives
in `docs/work/<slug>/`.

## Phase 0: Snapshot

0. Run `git status --short`. If the tree is dirty, commit it first so the
   run's diff is clean: `git add -A`, then `git commit -m "WIP before
   <slug>: <one line>"`. Check `git status` before adding: never commit
   `dojo.toml`, `crest/`, `ref/`, `build/`, rendered certificates, `.env` or
   other unexpected files; if something looks wrong, stop and ask. If the
   tree is clean, make no commit. Tell the user in one line what the
   snapshot contains.

## Phase 1: Agree (before any code)

1. **tester (PLAN)**: draft `acceptance.md` and failing acceptance tests.
2. **developer (FEEDBACK)**: feasibility, gaps, cost.
3. **tester (PLAN)**: incorporate and record the `## Agreement`. Repeat 2–3
   at most twice; if they still disagree, take it to the user.
4. **Checkpoint: user approval.** Show the scope, the ACs and the open
   questions (short, with a link to acceptance.md). Ask questions one at a
   time, with a recommendation. Do not start Phase 2 without approval.

## Phase 2: Build

5. **developer (IMPLEMENT)**: build against acceptance.md.

## Phase 3: Review loop

6. **reviewer**: review all uncommitted changes. Save its report as
   `docs/work/<slug>/review.md` (append `## Round N`).
7. On `CHANGES REQUESTED`: **developer (FIX)** with all findings verbatim,
   then back to 6. Minor findings and nits may be disputed; a disputed
   blocker or major is decided by the reviewer next round. Stop after 3
   rounds and take what remains to the user.

## Phase 4: Validate loop

8. **tester (VALIDATE)**: append the round to `validation.md`. The regression
   suite in `tests/regression/` must stay green; a change to it needs the
   item's acceptance.md to say why.
9. On `VERDICT: FAIL`: **developer (FIX)** with the reproductions, then
   **reviewer** on the fix diff (one round), then back to 8. Stop after 3
   validation rounds and escalate.
10. Report anything flagged "new finding, not in contract" as a proposed
    follow-up. Don't build it in this item.

## Phase 5: Hand-off

11. Summarise for the user: what was built (ACs, all PASS), files changed,
    review and validation rounds, anything disputed or deferred, links to
    acceptance.md, review.md and validation.md, and the commit.
12. **Post-run commit**, only after `VERDICT: PASS` (or the user's explicit
    go-ahead): check `git status`, `git add -A`, `git commit` with an English
    summary line, a short body (ACs, rounds, deferred items) and the
    attribution trailer from the session's reminder. Show the hash. If the
    item touches DECISIONS.md's Open list, the developer has updated it.

Then stop. Don't start the next work item until the user asks.

## Passing context

Subagents start cold. Every prompt includes the mode, the slug and the paths
in `docs/work/<slug>/`; for FIX, the findings verbatim; for the reviewer,
which round and which earlier findings to re-check. Remind each one that
renders pin `-c src/menkyo/example.toml`.
