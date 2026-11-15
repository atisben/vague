---
name: dev-implement
version: 2.0.0
description: |
  Build work that is already decided: a plan-eng plan, a spec, tickets, or the plan agreed in this
  conversation. Small work is built inline, test-first. Larger work becomes a task graph: each ready
  ticket goes to a fresh implementer subagent in its own git worktree, a merger lands it on one
  integration branch, and /dev-review checks the result. Never reopens the plan.
  Trigger: "implement this", "build this feature", "develop this", "orchestrate", "/dev-implement".
sdk_commands:
  - vague context
  - vague memory-log
  - vague memory-search
allowed-tools:
  - Bash
  - Read
  - Agent
  - Skill
  - AskUserQuestion
benefits-from:
  - plan-ideation
  - plan-eng
---

<!-- Adapted from mattpocock/skills implement@6d6a5b9 and implement-spec@a496f55 (MIT). See NOTICE.md. -->

## Preamble

```bash
eval "$(vague context --shell --skill dev-implement)"
```

**Proactive invocation:** When the user asks to build something that a plan, spec, ticket, or this conversation already decided.

---

## What this skill does

```
 ┌──────────────┐   ┌──────────────┐   small   ┌──────────────────────────────┐
 │ 1. Load the  │──▶│ 2. Size gate │──────────▶│ Inline path: TDD, commit     │──┐
 │ plan/tickets │   │              │           └──────────────────────────────┘  │
 └──────────────┘   └──────────────┘                                             │
                           │ large                                               │
                           ▼                                                     │
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
 │ 3. Task graph│──▶│ 4. Implement │──▶│ 5. Merge to  │──▶│ 6. Next      │       │
 │ + frontier   │   │ one worktree │   │ integration  │   │ frontier     │       │
 └──────────────┘   │ per ticket   │   │ branch       │   └──────┬───────┘       │
                    └──────────────┘   └──────────────┘          │ all done      │
                           ▲                                     │               │
                           └──────── more ready tickets ─────────┘               │
                                                                 ▼               ▼
                                                   ┌──────────────────────────────┐
                                                   │ 7. /dev-review, one fixer    │
                                                   │ 8. Clean up, hand off        │
                                                   └──────────────────────────────┘
```

Three terms carry the whole skill:

- **Task graph**: the tickets plus "blocked by" edges between them. It is not a list of steps.
- **Frontier**: every ticket whose blockers are all merged. The frontier is what runs in parallel.
- **Seam**: the public boundary a test observes, such as a function signature or an HTTP route. Tests live at seams, so they survive a rewrite underneath.

**Never reopen the plan.** Whatever was settled upstream is the input. Do not interview the user, propose another approach, or redesign while building. If no plan exists anywhere, stop and suggest `/plan-eng`.

---

## Step 1: Load the plan

Each bash call is a fresh process. Re-run the preamble `eval` in any block that needs `$SLUG` or `$BRANCH`.

```bash
eval "$(vague context --shell --skill dev-implement)"
echo "SLUG=$SLUG  BRANCH=$BRANCH"
vague memory-search --kind doc --skill plan-eng || echo "PLAN: NONE"
git status --short
```

Each search line prints as `scope/key  [skill]  text  (files: <path>)`, newest first. The plan for this branch has the key `eng-plan-<branch>`, with every `/` in the branch replaced by `-`. Its path is a vault note: read it.

Find the input in this order:

1. A ticket reference the user passed (`#42`, an issue URL, `owner/repo#42`). Fetch it with `gh issue view <ref>`, or `glab issue view <ref>` on GitLab. State its title before you start. If the reference could match another numbered list in context, ask.
2. A spec or plan path the user passed.
3. The `eng-plan-<branch>` vault note found above.
4. A plan agreed earlier in this conversation. Restate it in three lines before you start.

**Branch check.** Never build on `main`. If `$BRANCH` is the base branch, create the **integration branch** now: `git switch -c feat/<short-name>`. On a topic branch already, that branch is the integration branch. Every commit of this run lands on it. The examples below write it as `feat/<short-name>`.

---

## Step 2: Size gate

| The work is… | Path |
|---|---|
| One ticket, or a plan that fits one context window, with no independent parts | **Inline path** (this step) |
| Several tickets, or parts that can be built at the same time | **Graph path** (Steps 3 to 8) |

### Inline path

You build it yourself, in the current checkout:

1. Name the seams from the plan. If the plan names none, propose them in one message and wait for a yes. Never write a test at an unconfirmed seam.
2. For each seam: write one failing test, make it pass, then refactor. One red-green slice at a time.
3. Run the type checker and the single test file after each slice, for example `uv run pytest tests/test_x.py`.
4. Run the full suite once at the end: `task --list` names it, otherwise `uv run pytest`.
5. Commit to the integration branch. `/dev-review` only sees committed changes.
6. Go to Step 7.

---

## Step 3: Build the task graph

You are now the **orchestrator**. You do not write code, read large files, or run the suite yourself. Keep your own context under about 15%.

Turn the plan into tickets. Each ticket is a vertical slice that one fresh subagent can finish in one context window. Present the graph and ask via AskUserQuestion: "Here's the graph. Proceed, or adjust?"

```
T1  auth model + hashing        seams: hash_password(), User.password_hash     blocked by: none
T2  login/register endpoints    seams: POST /login, POST /register             blocked by: T1
T3  token refresh               seams: POST /refresh, create_token()           blocked by: T1
```

Here T2 and T3 form the frontier once T1 merges.

**Optional exploration.** When several tickets need the same research, spawn one exploration subagent first. It writes Markdown notes to a directory outside the repo, such as `$TMPDIR/dev-implement/$SLUG/`. Implementers then read the notes instead of re-exploring.

---

## Step 4: One fresh implementer per ticket

For each frontier ticket, create a worktree on its own branch, based on the integration branch:

```bash
git worktree add "../$(basename "$PWD")-wt-T2" -b "feat/<short-name>-T2" "feat/<short-name>"
```

Then spawn a **fresh** implementer subagent per ticket, never a reused one. Spawn every frontier ticket in one message, in the background, so they run at the same time.

**Brief with context pointers, not copies.** A pointer is a path to the plan, the ticket, the exploration notes, or a commit. Never paste what the subagent can read itself. Every brief holds these parts:

1. **Ticket**: its id, title, seams, and a pointer to the plan or issue.
2. **Worktree**: the absolute path. "Confirm `git -C <path> merge-base --is-ancestor feat/<short-name> HEAD` succeeds before you start. If not, reset onto the integration branch."
3. **How to build**: "Test-first at the named seams, one red-green slice at a time. Run the type checker and the single test file after each slice. Run the full suite once at the end. Commit to your branch."
4. **Before reporting done**: "Merge the integration branch tip into your branch and re-run the full suite."
5. **Boundaries**: "Do not invoke any skill. Do not touch files outside this ticket. Do not change the plan."
6. **Deviation rules**: paste the block from *Deviation Rules*.
7. **Memory**: a subagent never runs the preamble, so it sees no memory unless you pass it.
   - Paste the MEMORY lines from your preamble that touch this ticket's files.
   - Tell it to share a finding sibling agents need with `vague memory-log <key> "<note>" --scratch --skill dev-implement`. This writes a `note` into the memory ledger. Notes are hidden after 7 days and are not a lock.
8. **Report**: "Under 150 words: the branch, the commits, the tests added, and any deviation."

Coding standards stay out of the brief. `/dev-review` enforces them in Step 7, where there is room to apply them.

---

## Step 5: Merge each finished ticket

When an implementer reports done, spawn a **merger subagent**. Its brief:

- "Merge `feat/<short-name>-T2` into `feat/<short-name>` with `git merge --no-ff` from the main checkout."
- "Resolve conflicts by keeping both tickets' behaviour. Stop and report if that is impossible."
- "Run the full suite on the integration branch. Report pass or fail in under 100 words."

Merge one ticket at a time, so each merge sees the previous one.

Run `vague memory-search --scratch` after each merge to read the notes implementers left.

---

## Step 6: Advance the frontier

After each merge, recompute the frontier. Start a worktree and a fresh implementer for every ticket that just became ready (Step 4). Repeat until every ticket is merged.

An implementer that stops with an R4 deviation blocks only its own ticket. Ask the user via AskUserQuestion, then brief a fresh implementer with the answer.

---

## Step 7: Review and fix

Call the Skill tool with `dev-review`, using the base branch as the fixed point. It reviews `main...feat/<short-name>`.

Sort its findings before fixing:

- **Fix without asking**: Spec gaps, and hard violations of a documented standard.
- **Ask first**: baseline smells. They are judgement calls. List them and let the user pick.

Give every accepted finding to **one fresh fixer subagent**, briefed like an implementer in the main checkout, on the integration branch. It commits the fixes and runs the full suite.

---

## Step 8: Clean up and hand off

Remove every ticket worktree and branch:

```bash
git worktree list
git worktree remove "../$(basename "$PWD")-wt-T2"
git branch -d "feat/<short-name>-T2"
```

Log a non-obvious pitfall the run hit, or a scratch note that will still hold next week. The preamble printed the command. Give a promoted note a new key: a key cannot switch from `note` to another kind.

---

## Deviation Rules

Paste this block into every implementer and fixer brief:

```
## Deviation rules
- R1: a bug in existing code blocks you → fix it inline, note it in your report
- R2: missing critical correctness code (input validation on a public endpoint) → add it, note it
- R3: a build or test blocker (missing dependency, broken config) → fix it, note it
- R4: an architectural decision (new table, schema change, library switch) → STOP, change nothing, report back
R4 overrides R1 to R3.
```

---

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about dev-implement` (see the Memory guideline).

---

## Handoff

> "Built on `feat/<short-name>`, reviewed with `/dev-review`, fixes committed. Next: `/code-review` for a correctness bug hunt, then `/dev-ship` to open the PR."
