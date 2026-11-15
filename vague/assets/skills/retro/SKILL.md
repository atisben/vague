---
name: retro
version: 2.0.0
description: |
  Retrospective on how the agent worked. Reads the session log and the skill observations in the
  memory ledger, finds where the agent struggled, and proposes environment fixes: a check, a coding
  standard for /dev-review, a skill edit, a navigation pointer, or a deletion. Applies only what the
  user picks, then curates the memory ledger. Changes the environment, never the product code.
  Trigger: "retro", "retrospective", "what went wrong this session", "improve skills", "review observations".
sdk_commands:
  - vague context
  - vague skill-check
  - vague skill-list
  - vague memory-log
  - vague memory-search
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

<!-- Adapted from mattpocock/skills retro@a7d038f (MIT), merged with vague's former /meta skill. See NOTICE.md. -->

## Preamble

```bash
eval "$(vague context --shell --skill retro)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
```

**Proactive invocation:** Suggest it at the end of a session that was harder than it should have been, or when the user mentions friction with a skill.

---

## What this skill does

```
 ┌──────────────────┐
 │ 1a. Session log  │──┐
 │ *.jsonl          │  │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 └──────────────────┘  ├──▶│ 2. Candidates│──▶│ 3. Route each│──▶│ 4. User picks│──▶│ 5. Apply,    │
 ┌──────────────────┐  │   │ each cites a │   │ to where its │   │ by severity  │   │ skill-check  │
 │ 1b. Observations │──┘   │ real moment  │   │ fix belongs  │   └──────────────┘   └──────┬───────┘
 │ memory ledger    │      └──────────────┘   └──────────────┘                              │
 └──────────────────┘                                                                       ▼
                                                                                 ┌──────────────────┐
                                                                                 │ 6. Curate memory │
                                                                                 │ 7. Verify, report│
                                                                                 └──────────────────┘
```

- **Changes the environment**: checks, standards, skills, pointers. It never fixes the product code itself.
- **Proposes before it acts.** Nothing changes until the user picks a candidate.
- **Not** the weekly commit statistics. That skill was retired.

---

## Step 1: Read the primary sources

### 1a. The session log

Default to the current session. The user can name another one. Claude Code keeps one JSONL file per session, where each line is one event:

```bash
LOGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/$(pwd | sed 's#[/.]#-#g')"
ls -t "$LOGS"/*.jsonl | head -5   # newest first: the first one is the current session
```

Read a large log through filters, not whole. These two show the tool calls in order, then the failed ones:

```bash
F="<the .jsonl path>"
jq -c 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | {name, input: (.input|tostring|.[0:120])}' "$F"
jq -c 'select(.type=="user") | .message.content | arrays | .[] | select(.type=="tool_result" and .is_error==true) | .content|tostring|.[0:200]' "$F"
```

On another runtime with no such log, use the current conversation as the session.

### 1b. The observations and memories

Every project shares one global store, so this reads the observations logged from every repo:

```bash
vague memory-search --kind observation   # all open skill feedback
vague memory-search --scope all          # every active memory, for Step 6
vague skill-list
```

Each observation prints as `global/<key>  [<skill>]  <issue → suggestion>`, where `<skill>` is the skill it is about. Keys starting with `new-skill-` are new-skill candidates. Actioned and declined observations no longer appear. When `--scope all` prints more than you can read in one pass, read one scope at a time with `--scope <project>` or `--scope global`.

---

## Step 2: Find the candidates

Every candidate must cite a specific moment: a tool call in the log, a user correction, or an observation key. Drop any candidate you cannot trace. Generic best practice is not a candidate.

Look for candidates in these categories:

| Category | The session shows… | Use when |
|---|---|---|
| **Navigation** | Many searches before the agent found a file or fact | A lookup took a long time |
| **Automated checks** | A mistake a linter, type, test, or hook could catch | The agent made that mistake, or the repo has no guardrail at all |
| **Coding standards** | A judgement-call mistake `/dev-review` missed | The reviewer let it through |
| **Skill defect** | A skill step that was wrong, missing, or ignored | The user had to correct a skill, or an observation names one |
| **Steering size** | `CLAUDE.md` or `guidelines.md` steering that belongs elsewhere | The file is large |
| **Tool economy** | An expensive tool call for what it returned | A call was slow or huge |
| **No-ops** | Steering lines that change no behaviour | A steering file is long |
| **Information access** | A fact the agent needed and could not reach | Logs or a service were out of reach |

A repo with no **guardrail** is itself a finding. A guardrail is a pre-commit hook or a CI job that runs lint, typecheck, and tests. Read the repo's own check commands first (`task --list`, `.pre-commit-config.yaml`, the CI workflow). A check that exists but is unwired or broken is the finding, not a reason to build a new one.

---

## Step 3: Route each fix to where it belongs

Classify each candidate before proposing a fix:

| The problem is… | The fix goes in… |
|---|---|
| **Mechanical**: a banned API, an import shape, a file-location rule | A deterministic check. In the vague repo: a rule in `vague/sdk/core/skill_rules.py` with a test. Elsewhere: a linter rule, a pre-commit hook, or a CI job, whichever is cheapest. |
| An existing check that is unwired | Wiring it, not rebuilding it |
| A **judgement call** no check could catch | The standards file `/dev-review` reads (`CODING_STANDARDS.md` or `CONTRIBUTING.md`). Propose creating one if none exists. |
| A skill instruction | That skill's `SKILL.md` |
| A slow lookup | A one-line navigation pointer in a file the agent already reads |
| A line that changes nothing | Deleting it |

Keep `CLAUDE.md`, `AGENTS.md` and `vague/assets/claude/guidelines.md` small. They load into every session, whether relevant or not. Add to them only a navigation pointer, or a cross-cutting principle the user names. Prefer moving steering out of them.

**Why the reviewer owns standards.** The implementing agent has the most context pressure: it explores, writes code, and debugs. The reviewer gets a diff and nothing else. So a new rule goes where there is room to apply it, which is `/dev-review`.

---

## Step 4: Let the user pick

Present the candidates most severe first. Rank a quiet, expensive mistake above a loud, cheap one.

```
## Retro candidates

1. [Automated checks] Agent wrote `type: ignore` twice (tool calls 14, 31) → add a ruff rule to pre-commit
2. [Skill defect] dev-ship skipped the test step (observation ship-no-test-step) → add the step to dev-ship
3. [Navigation] 9 greps to find the hook config (calls 40-48) → pointer in CLAUDE.md to vague/hooks/
4. [New skill] new-skill-dependency-audit → scaffold a dependency-audit skill
```

Ask via AskUserQuestion: "Which candidates should I apply?" Offer: apply all, pick specific ones, or show details first.

---

## Step 5: Apply the picked fixes

**Skill edits.** Read the target from `vague/assets/skills/<name>/SKILL.md` in the vague repo, or `~/.claude/skills/<name>/SKILL.md` elsewhere. Integrate the change where it belongs, so it reads as if it was always there. Then validate:

```bash
vague skill-check vague/assets/skills/<name>/
```

**New skills.** Scaffold `vague/assets/skills/<name>/SKILL.md` from the template in `docs/skill-authoring.md`: all required frontmatter fields, the preamble `eval "$(vague context --shell --skill <name>)"`, the steps, the Observation Protocol line, and a Handoff. Validate it with `vague skill-check`.

**Checks and standards.** Write the check with a test that fails without it. Run it against the whole repo before it blocks anything: a new check is code like any other.

**Observations.** Mark each one you acted on, or that the user declined:

```bash
vague memory-log <key> --status actioned
vague memory-log <key> --status declined
```

---

## Step 6: Curate memories

Read the `vague memory-search --scope all` output from Step 1b. Each line prints as `scope/key  [skill]  text  (files: …)`, without the parts that are empty. Nothing is deleted: every change is a new line in the ledger.

| You find | Action |
|---|---|
| A duplicate: the same fact under two keys in one project | Rewrite one: `vague memory-log <keep-key> "<merged text>"`. Forget the other: `vague memory-log <drop-key> --status forgotten` |
| A cross-project fact: the same fact in two projects | Re-log it: `vague memory-log <key> "<text>" --global`. Forget each original with `--status forgotten` |
| A dead path: a memory whose `files` no longer exist in its repo | Re-log with corrected `--files`, or forget it |

Run each command from the repo of the memory's scope, or add `--global` for a `global/` memory. Ask the user before you forget anything.

---

## Step 7: Verify and report

Re-read every modified skill and confirm:

1. The frontmatter fields, the preamble, and the Handoff are intact.
2. The one-line Observation Protocol is present.
3. No existing rule or step was removed by accident.
4. `vague skill-check vague/assets/skills/<name>/` passes, and so does `uv run pytest` in the vague repo.

Then report:

```
## /retro complete

### Applied
- [Automated checks] ruff rule PGH003 added to pre-commit (calls 14, 31)
- [Skill defect] dev-ship: test step before commit (ship-no-test-step)

### Declined: ship-changelog-dates (user prefers the current format)
### Memories curated: merged tests-need-docker ← docker-pytest, promoted concat-empty-list
```

Log a learning only for a fact the retro itself revealed, such as a skill convention that keeps drifting.

> "Environment updated. Next: run `vague install` to deploy skill changes, review `git diff`, then `/dev-ship` to open a PR."

---

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about retro` (see the Memory guideline).
